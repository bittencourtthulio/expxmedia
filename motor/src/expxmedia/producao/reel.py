"""Produção do reel narrado em Remotion, a partir de um template de reel (D-05, D-31, D-41, D-49).

A entrada é um objeto JSON (o `exemplo.json` do template embarcado é uma entrada completa):

    {
      "template": "reel-narrado-cartao-870a5c" | null,     padrão: o template embarcado narrado-cartao
      "titulo": "...",
      "roteiro": "texto narrado (130 a 180 palavras)",
      "cta": "PALAVRA",                                    a palavra do CTA, dita no roteiro
      "cenas": [{"kind": "abertura", "ancora": "primeiras palavras da cena", "etiqueta": ["L1", "L2"],
                 <slots do kind>, "id"?, "ev"?, "sons"?}, ...],
      "trilha": {...} | null,                              padrão: a do cenas.json do template
      "palavras_por_bloco": N | null,                      padrão: pela cadência medida na narração
      "legenda": "texto do post" | null,
      "porta_voz": "id" | null, "canal": "instagram" | null,
      "conteudo": {"gancho", "gancho_tipo", "cta_forma"} (opcional),
      "serie", "pack", "oferta", "slug"                    (opcionais)
    }

O caminho, na ordem (origem: Instragram-Videos/pipeline/render_remotion.py:154-164 e
Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md, no caminho do template em vez do sob medida):

1. confere a entrada: kinds e slots contra o `template.json`, âncoras casando com o roteiro em ordem (o
   mesmo casamento da montagem) — erro cita o campo e nada é criado;
2. cria a peça em `roteiro` e aplica o **gate do roteirista** (`revisar.roteiro`: 130 a 180 palavras, CTA no
   roteiro, sem travessão, markdown nem decimal): reprovado, nada é narrado;
3. **narra uma vez** (`narrar`, o provedor que o `.env` escolher);
4. **monta** com `scripts/montar.mjs` do kit: linha do tempo pelas âncoras, blocos de legenda (palavras por
   bloco pela cadência da narração, a mesma regra da legenda do reel) e trilha determinística que não repete
   a de outra peça da instalação;
5. **renderiza** o template (o código Remotion dele, sobre o kit) com a Alma por props, e tira da camada de
   legenda os cartões que a verificação confere (`caps/`, `caps.txt`, `legendas.json`) e o SRT;
6. **normaliza** a mistura (-14 LUFS, pico ≤ -1 dBFS);
7. **verifica** no perfil `reel` (as 11 checagens, 30 a 70 s); reprovado, `geracao_falhou` e a peça fica
   em `roteiro`;
8. registra arquivos, produção e `geracao_concluida`, e passa a peça para `produzida`.

O template é renderizado num projeto temporário: `src/composicoes/<id>/` com o código do template, e o
módulo `@expxmedia/template` (a Alma por props, a área segura, a mola, o selo) apontando para o kit do motor.
É o único módulo além de react e remotion que o código de template pode importar (CONTRATO-template).

Uso:

    from expxmedia.producao import reel
    r = reel.produzir(raiz, entrada)   # {"peca_id", "status", "pasta", "video", "duracao", "verificacao", ...}
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from expxmedia.alma import carregar as alma_carregar
from expxmedia.alma import fontes as alma_fontes
from expxmedia.ambiente.verificar import Verificador
from expxmedia.legendar import reel as legenda_reel
from expxmedia.legendar import srt
from expxmedia.motion import remotion
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.render_html import renderizar as render_html
from expxmedia.revisar import roteiro as gate_roteiro
from expxmedia.template import galeria_local
from expxmedia.video import ffmpeg, verificar

__all__ = [
    "ErroProducaoReel",
    "ErroEntradaReel",
    "ErroRoteiroReprovado",
    "ErroVerificacaoReprovada",
    "CAMPOS",
    "PERFIL",
    "TEMPLATE_PADRAO",
    "PAPEIS_COR",
    "ler_entrada",
    "achar_template",
    "conferir_ancoras",
    "montar_cenas",
    "props_alma",
    "preparar_projeto",
    "cartoes_da_legenda",
    "produzir",
]

TIPO, FORMATO, PERFIL = "reel", "9:16", "reel"
TEMPLATE_PADRAO = "reel-narrado-cartao-870a5c"
CAMPOS = ("template", "titulo", "roteiro", "cta", "cenas", "trilha", "palavras_por_bloco", "legenda", "porta_voz",
          "canal", "conteudo", "serie", "pack", "oferta", "slug")
PAPEIS_COR = ("fundo", "fundo_alt", "texto", "texto_inverso", "apoio", "destaque", "destaque_2", "positivo", "negativo")
CAMPOS_CENA = ("id", "kind", "ancora", "ev", "sons")  # o resto da cena são os slots do kind
PROVEDOR_LEGENDA, PROVEDOR_MOTION, PROVEDOR_VIDEO = "local", "remotion", "ffmpeg"
FPS = verificar.FPS  # o perfil reel pede 30/1; a linha do tempo da montagem diz o seu fps e é conferida
ENTRA_ANTES = 2  # o bloco da legenda entra 2 quadros antes da 1ª palavra; origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:137
MONTAR = remotion.KIT / "scripts" / "montar.mjs"
TEMPO_MONTAR_S = 600
FIM_DA_SAIDA = 1500  # origem: Instragram-Videos/pipeline/render_remotion.py:147-149 (últimos 1500 caracteres)
MODULOS_KIT = ("constantes", "anim", "alma", "fontes", "SeloPerfil")  # o que @expxmedia/template entrega
_RE_ID = re.compile(r"[^a-zA-Z0-9-]+")


class ErroProducaoReel(RuntimeError):
    """A produção do reel não terminou."""


class ErroEntradaReel(ValueError):
    """Entrada fora do formato; `campo` diz qual. Nada foi criado."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


class _ErroComPeca(ErroProducaoReel):
    def __init__(self, peca_id: str, mensagem: str, achados: list[dict[str, Any]]) -> None:
        super().__init__(f"{peca_id}: {mensagem}")
        self.peca_id = peca_id
        self.achados = achados


class ErroRoteiroReprovado(_ErroComPeca):
    """O gate do roteirista reprovou: nada foi narrado; a peça ficou em `roteiro`."""


class ErroVerificacaoReprovada(_ErroComPeca):
    """O MP4 saiu e reprovou na verificação de entrega; a peça ficou em `roteiro`."""


# ---------------------------------------------------------------- template


def achar_template(raiz: Path | str, template_id: str | None, embarcados: Path | str | None = None) -> tuple[Path, dict[str, Any]]:
    """(pasta, template.json) do template de reel em Remotion (galeria local antes da embarcada)."""
    template_id = template_id or TEMPLATE_PADRAO
    base_emb = Path(embarcados) if embarcados is not None else galeria_local.pasta_embarcados()
    itens = galeria_local.listar(raiz, embarcados=base_emb)
    item = next((i for i in itens if i["template_id"] == template_id), None)
    if item is None:
        de_reel = sorted(i["template_id"] for i in itens if isinstance(i["dados"], dict) and i["dados"].get("tipo") == TIPO)
        raise ErroEntradaReel("template", f"template '{template_id}' não encontrado (de reel: {', '.join(de_reel) or 'nenhum'})")
    if item["erro"] is not None:
        raise ErroEntradaReel("template", f"template '{template_id}' fora do contrato: {item['erro']}")
    dados = item["dados"]
    if dados.get("tipo") != TIPO or dados.get("motor") != "remotion":
        raise ErroEntradaReel("template", f"template '{template_id}' é {dados.get('tipo')}/{dados.get('motor')}, não reel/remotion")
    if dados.get("status") in galeria_local.STATUS_FORA_DA_BUSCA:
        raise ErroEntradaReel("template", f"template '{template_id}' está {dados['status']}")
    pasta = Path(raiz) / item["caminho"] if item["galeria"] == "local" else base_emb.parent / item["caminho"]
    for nome in ("cenas.json", "package.json", "src/Composicao.tsx"):
        if not (pasta / nome).is_file():
            raise ErroEntradaReel("template", f"template '{template_id}' sem {nome}")
    return pasta, dados


# ---------------------------------------------------------------- entrada


def _texto(e: dict[str, Any], campo: str, obrigatorio: bool = True) -> None:
    valor = e[campo]
    if valor is None and not obrigatorio:
        return
    if not isinstance(valor, str) or not valor.strip():
        raise ErroEntradaReel(campo, "texto obrigatório" if obrigatorio else "texto ou null")


def ler_entrada(dados: Any) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None."""
    if not isinstance(dados, dict):
        raise ErroEntradaReel("entrada", "a entrada é um objeto JSON")
    extras = sorted(set(dados) - set(CAMPOS))
    if extras:
        raise ErroEntradaReel(extras[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    e = {campo: dados.get(campo) for campo in CAMPOS}
    for campo in ("titulo", "roteiro", "cta"):
        _texto(e, campo)
    for campo in ("template", "legenda", "porta_voz", "canal", "serie", "pack", "oferta", "slug"):
        _texto(e, campo, obrigatorio=False)
    cenas = e["cenas"]
    if not isinstance(cenas, list) or not cenas or not all(isinstance(c, dict) for c in cenas):
        raise ErroEntradaReel("cenas", "lista de cenas ({\"kind\", \"ancora\", \"etiqueta\", <slots>})")
    for i, c in enumerate(cenas, 1):
        if not isinstance(c.get("kind"), str) or not c["kind"].strip():
            raise ErroEntradaReel("cenas", f"a cena {i} não tem kind")
        if not isinstance(c.get("ancora"), str) or not c["ancora"].strip():
            raise ErroEntradaReel("cenas", f"a cena {i} ({c['kind']}) não tem âncora: as primeiras palavras da narração em que ela entra")
    if e["trilha"] is not None and (not isinstance(e["trilha"], dict) or not e["trilha"].get("bpm") or not e["trilha"].get("acordes")):
        raise ErroEntradaReel("trilha", "objeto com bpm e acordes, ou null")
    ppb = e["palavras_por_bloco"]
    if ppb is not None and (isinstance(ppb, bool) or not isinstance(ppb, int) or ppb < 1):
        raise ErroEntradaReel("palavras_por_bloco", "inteiro positivo ou null")
    conteudo = e["conteudo"] or {}
    if not isinstance(conteudo, dict):
        raise ErroEntradaReel("conteudo", "objeto ou null")
    fora = sorted(set(conteudo) - {"gancho", "gancho_tipo", "cta_forma"})
    if fora:
        raise ErroEntradaReel("conteudo", f"chave '{fora[0]}' fora do contrato (gancho, gancho_tipo, cta_forma)")
    if conteudo.get("gancho_tipo") is not None and conteudo["gancho_tipo"] not in modelo.GANCHO_TIPOS:
        raise ErroEntradaReel("conteudo", f"gancho_tipo inválido: {conteudo['gancho_tipo']!r}")
    if conteudo.get("cta_forma") is not None and conteudo["cta_forma"] not in modelo.CTA_FORMAS:
        raise ErroEntradaReel("conteudo", f"cta_forma inválido: {conteudo['cta_forma']!r}")
    e["conteudo"] = conteudo
    e["roteiro"] = e["roteiro"].strip()
    e["cta"] = e["cta"].strip().upper()
    return e


def _conferir_cenas(manifesto: dict[str, Any], esqueleto: dict[str, Any], cenas: list[dict[str, Any]]) -> None:
    """Kinds e slots das cenas contra o template (a mesma conferência de slots da produção estática)."""
    kinds = manifesto.get("kinds") or {}
    padroes = esqueleto.get("kinds") or {}
    slides = [{k: v for k, v in c.items() if k == "kind" or k not in CAMPOS_CENA} for c in cenas]
    erros = render_html.validar_copy({"tipo": TIPO, "kinds": kinds}, {"slides": slides})
    erros = [e.replace("slide ", "cena ", 1) for e in erros]
    for i, c in enumerate(cenas, 1):
        if c["kind"] in kinds and c["kind"] not in padroes and ("ev" not in c or "sons" not in c):
            erros.append(f"cena {i} ({c['kind']}): o cenas.json do template não traz ev e sons deste kind; informe-os na cena")
    ids = [c.get("id") for c in cenas if c.get("id") is not None]
    if len(ids) != len(set(ids)):
        erros.append("ids de cena repetidos")
    if erros:
        raise ErroEntradaReel("cenas", "; ".join(erros))


def _normalizar(palavra: str) -> str:
    # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:79 (minúsculas, NFD sem diacríticos, só [a-z0-9])
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", palavra.lower()) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", sem_acento)


def conferir_ancoras(roteiro: str, cenas: list[dict[str, Any]]) -> None:
    """A âncora de cada cena casa com o roteiro, em ordem — antes de narrar, com o casamento da montagem.

    O alinhamento da narração está no espaço do roteiro, então o que casa aqui casa na montagem.
    origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:79-91
    """
    palavras = [_normalizar(p) for p in roteiro.split()]
    cursor = 0
    for n, c in enumerate(cenas, 1):
        alvo = [a for a in (_normalizar(p) for p in c["ancora"].split()) if a]
        if not alvo:
            raise ErroEntradaReel("cenas", f"cena {n} ({c['kind']}): âncora sem palavra")
        for i in range(cursor, len(palavras)):
            if palavras[i:i + len(alvo)] == alvo:
                cursor = i + 1
                break
        else:
            raise ErroEntradaReel("cenas", f"cena {n} ({c['kind']}): âncora \"{c['ancora']}\" não casou com o roteiro, em ordem")


# ---------------------------------------------------------------- cenas.json da peça


def _assinatura(trilha: dict[str, Any]) -> tuple:
    # só bpm, acordes e o conjunto de nomes dos instrumentos; origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:58
    return (trilha.get("bpm"), json.dumps(trilha.get("acordes")), tuple(sorted((trilha.get("instrumentos") or {}))))


def _transpor(trilha: dict[str, Any], semitons: int) -> dict[str, Any]:
    fator = 2 ** (semitons / 12)
    nova = json.loads(json.dumps(trilha))
    nova["acordes"] = [[round(r * fator, 2), [round(n * fator, 2) for n in notas]] for r, notas in trilha["acordes"]]
    return nova


def _trilhas_da_instalacao(raiz: Path, fora: Path) -> list[dict[str, Any]]:
    """As trilhas das outras peças de reel desta instalação (`midia/cenas.json`)."""
    lista = []
    for arq in sorted((raiz / "pecas").glob("*/*/midia/cenas.json")):
        if arq.parent.parent == fora:
            continue
        try:
            trilha = arquivos.ler_json(arq).get("trilha")
        except (arquivos.ErroArquivo, AttributeError):
            continue
        if isinstance(trilha, dict):
            lista.append({"reel": arq.parent.parent.name, "trilha": trilha})
    return lista


def _escolher_trilha(trilha: dict[str, Any], outras: list[dict[str, Any]], explicita: bool) -> dict[str, Any]:
    """A trilha do template, transposta de semitom em semitom até não repetir a de outra peça.

    A trilha pedida pela entrada vai como veio: repetida, a montagem recusa com a mensagem da origem.
    """
    usadas = {_assinatura(o["trilha"]) for o in outras}
    if explicita or _assinatura(trilha) not in usadas:
        return trilha
    for k in range(1, 12):
        candidata = _transpor(trilha, k)
        if _assinatura(candidata) not in usadas:
            return candidata
    return trilha


def montar_cenas(esqueleto: dict[str, Any], cenas: list[dict[str, Any]], *, palavras_por_bloco: int,
                 trilha: dict[str, Any]) -> dict[str, Any]:
    """O `cenas.json` da peça: o esqueleto do template com as cenas da entrada e os eventos padrão de cada kind.

    Som de item de lista (`i<k>`) sem o item k na cena sai: não toca tique de item que não aparece.
    """
    padroes = esqueleto.get("kinds") or {}
    saida_cenas = []
    for n, c in enumerate(cenas, 1):
        base = padroes.get(c["kind"]) or {}
        cena = {"id": c.get("id") or f"c{n:02d}-{c['kind']}", "kind": c["kind"], "ancora": c["ancora"]}
        cena.update({k: v for k, v in c.items() if k not in CAMPOS_CENA})
        cena["ev"] = dict(c["ev"]) if isinstance(c.get("ev"), dict) else dict(base.get("ev") or {})
        sons = c["sons"] if isinstance(c.get("sons"), list) else list(base.get("sons") or [])
        itens = cena.get("itens")
        if isinstance(itens, list):
            def cabe(som: list[Any]) -> bool:
                m = re.fullmatch(r"i(\d+)", str(som[0]).split("+")[0])
                return m is None or int(m.group(1)) < len(itens)
            sons = [s for s in sons if cabe(s)]
        cena["sons"] = sons
        saida_cenas.append(cena)
    return {
        "trilha": trilha,
        "troca": esqueleto.get("troca"),
        "legenda": {"palavras_por_bloco": palavras_por_bloco},
        "cauda_s": esqueleto.get("cauda_s"),
        "cenas": saida_cenas,
    }


def _cadencia(alinhamento: dict[str, list]) -> float:
    """Palavras por segundo pela MEDIANA do intervalo início→início (as pausas não mascaram).

    origem: Instragram-Videos/pipeline/captions.py:84-92 (a mesma medida da legenda do reel)
    """
    inicios, dentro = [], False
    for ch, t0 in zip(alinhamento["characters"], alinhamento["character_start_times_seconds"]):
        if ch.isspace():
            dentro = False
        elif not dentro:
            inicios.append(t0)
            dentro = True
    gaps = sorted(b - a for a, b in zip(inicios, inicios[1:]))
    if not gaps or gaps[len(gaps) // 2] <= 0:
        raise ErroProducaoReel("alinhamento sem intervalo entre palavras: não dá para medir a cadência")
    return 1.0 / gaps[len(gaps) // 2]


def _montar(pasta_cenas: Path, narracao: Path, alinhamento: Path, saida: Path, assinaturas: Path) -> str:
    node = shutil.which("node")
    if node is None:
        raise ErroProducaoReel("node não encontrado no PATH (a montagem da linha do tempo roda em Node)")
    cmd = [node, str(MONTAR), "--reel", str(pasta_cenas), "--narracao", str(narracao), "--alinhamento", str(alinhamento),
           "--saida", str(saida), "--assinaturas", str(assinaturas)]
    try:
        r = subprocess.run(cmd, cwd=remotion.KIT, capture_output=True, text=True, timeout=TEMPO_MONTAR_S)
    except subprocess.TimeoutExpired as erro:
        raise ErroProducaoReel(f"a montagem passou do tempo limite de {TEMPO_MONTAR_S} s") from erro
    if r.returncode:
        raise ErroProducaoReel(f"a montagem falhou:\n{((r.stdout or '') + (r.stderr or ''))[-FIM_DA_SAIDA:]}")
    return (r.stdout or "") + (r.stderr or "")


# ---------------------------------------------------------------- Alma por props


def _faces(css: str) -> list[tuple[Path, int | None, str | None]]:
    faces = []
    for bloco in re.findall(r"@font-face\s*\{([^}]*)\}", css):
        url = re.search(r"url\(\s*['\"]?([^'\")]+)", bloco)
        if not url:
            continue
        partes = urlsplit(url.group(1))
        if partes.scheme != "file":
            continue
        peso = re.search(r"font-weight:\s*(\d+)\s*(\d+)?\s*;", bloco)
        estilo = re.search(r"font-style:\s*([a-z]+)", bloco)
        faces.append((Path(unquote(partes.path)), int(peso.group(1)) if peso and not peso.group(2) else None,
                      estilo.group(1) if estilo else None))
    return faces


def props_alma(alma: Any, publico: Path | str, *, raiz: Path | str, cache_fontes: Path | str | None = None,
               porta_voz: dict[str, Any] | None = None, canal: str | None = None) -> tuple[dict[str, Any], list[str]]:
    """(props `alma` das composições do kit, avisos): cores por papel, fontes e retrato copiados para `publico`.

    Os caminhos das props são relativos a `publico`, que vira o public dir do render (M9). Fonte não
    resolvida cai na Inter embarcada com aviso, como no render HTML (D-21); nunca fonte de sistema.
    """
    dados = alma.dados if hasattr(alma, "dados") else alma
    raiz, publico = Path(raiz), Path(publico)
    cores = ((dados.get("visual") or {}).get("cores")) or {}
    faltam = [p for p in PAPEIS_COR if not isinstance(cores.get(p), str)]
    if faltam:
        raise ErroProducaoReel(f"a Alma não tem as cores {', '.join(faltam)} (visual.cores)")
    avisos: list[str] = []
    pasta_fontes = publico / "fontes"
    pasta_fontes.mkdir(parents=True, exist_ok=True)
    fontes: dict[str, Any] = {}
    for papel in ("titulo", "texto"):
        resolvida = alma_fontes.resolver_fonte(dados, papel, raiz=raiz, cache=cache_fontes)
        if resolvida.aviso:
            avisos.append(resolvida.aviso)
        faces = [f for f in _faces(resolvida.css) if f[0].is_file()] or [(p, None, None) for p in resolvida.arquivos]
        arquivos_fonte = []
        for n, (caminho, peso, estilo) in enumerate(faces):
            destino = pasta_fontes / f"{papel}-{n}{caminho.suffix.lower()}"
            shutil.copyfile(caminho, destino)
            arquivos_fonte.append({"caminho": relativo(publico, destino), "peso": peso, "estilo": estilo})
        fontes[papel] = {"familia": resolvida.familia, "arquivos": arquivos_fonte}
    pv = None
    if porta_voz is not None:
        retrato = None
        retratos = [r for r in porta_voz.get("retratos") or [] if isinstance(r, str)]
        if retratos and (raiz / retratos[0]).is_file():
            origem = raiz / retratos[0]
            destino = publico / "retratos" / f"porta-voz{origem.suffix.lower()}"
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origem, destino)
            retrato = relativo(publico, destino)
        elif retratos:
            avisos.append(f"retrato do porta-voz {porta_voz.get('id')} não encontrado: o selo sai sem foto")
        pv = {"id": str(porta_voz.get("id")), "nome": str(porta_voz.get("nome") or ""), "retrato": retrato}
    canais = [c for c in dados.get("canais") or [] if isinstance(c, dict) and c.get("identificador")]
    escolhido = next((c for c in canais if c.get("canal") == (canal or "instagram")), None)
    if escolhido is None and canal is None and canais:
        escolhido = canais[0]
    props = {
        "cores": {p: cores[p] for p in PAPEIS_COR},
        "fontes": fontes,
        "porta_voz": pv,
        "canal": {"canal": escolhido["canal"], "identificador": escolhido["identificador"]} if escolhido else None,
    }
    return props, avisos


def _porta_voz(alma: dict[str, Any], pedido: str | None) -> dict[str, Any]:
    vozes = [v for v in alma.get("porta_vozes") or [] if isinstance(v, dict)]
    if pedido:
        achado = next((v for v in vozes if v.get("id") == pedido), None)
        if achado is None:
            raise ErroEntradaReel("porta_voz", f"o porta-voz {pedido} não existe na Alma")
        return achado
    achado = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    if achado is None:
        raise ErroEntradaReel("porta_voz", "a Alma não tem porta-voz para narrar")
    return achado


# ---------------------------------------------------------------- projeto de render do template


def _id_composicao(template_id: str) -> str:
    return _RE_ID.sub("-", template_id).strip("-") or "Template"


def preparar_projeto(pasta_template: Path | str, destino: Path | str, composicao: str) -> Path:
    """Projeto Remotion temporário que renderiza o template como a composição `composicao`.

    - `node_modules/`: cada pacote do kit por link simbólico (nada é instalado nem copiado), mais
      `@expxmedia/template`, que reexporta os módulos do kit (Alma, área segura, mola, fontes, selo);
    - `src/composicoes/<composicao>/`: o `src/` do template e um `index.tsx` que dá o id à `composicao`
      que o template exporta (o runner registra só ela, por um entry point próprio).
    """
    pasta_template, destino = Path(pasta_template), Path(destino)
    destino.mkdir(parents=True)
    modulos = remotion.KIT / "node_modules"
    if not modulos.is_dir():
        raise ErroProducaoReel(f"o kit Remotion não está instalado em {remotion.KIT}: rode a preparação do ambiente")
    nm = destino / "node_modules"
    nm.mkdir()
    for entrada in sorted(modulos.iterdir()):
        if entrada.name in (".cache", "@expxmedia"):
            continue
        (nm / entrada.name).symlink_to(entrada, target_is_directory=entrada.is_dir())
    pacote = nm / "@expxmedia" / "template"
    pacote.mkdir(parents=True)
    arquivos.gravar_json(pacote / "package.json", {"name": "@expxmedia/template", "private": True,
                                                   "main": "index.ts", "types": "index.ts"})
    kit = remotion.KIT / "src" / "kit"
    (pacote / "index.ts").write_text(
        "// GERADO pelo motor (expxmedia.producao.reel) para um render: o módulo de apoio dos templates.\n"
        + "".join(f"export * from {json.dumps((kit / m).as_posix())};\n" for m in MODULOS_KIT),
        encoding="utf-8")
    comp = destino / "src" / "composicoes" / composicao
    shutil.copytree(pasta_template / "src", comp)
    if (comp / "index.tsx").exists():
        raise ErroProducaoReel("o src/ do template não pode ter index.tsx: o motor gera o registro da composição")
    (comp / "index.tsx").write_text(
        "// GERADO pelo motor: registra o template como uma composição do render.\n"
        'import { composicao as base } from "./Composicao";\n\n'
        f"export const composicao = {{ ...base, id: {json.dumps(composicao)} }};\n",
        encoding="utf-8")
    shutil.copyfile(pasta_template / "package.json", destino / "package.json")
    arquivos.gravar_json(destino / "tsconfig.json", {
        "compilerOptions": {"target": "ES2022", "module": "ESNext", "moduleResolution": "bundler", "jsx": "react-jsx",
                            "strict": True, "skipLibCheck": True, "esModuleInterop": True, "noEmit": True,
                            "resolveJsonModule": True},
        "include": ["src"],
    })
    return destino


# ---------------------------------------------------------------- cartões da legenda


def cartoes_da_legenda(timeline: dict[str, Any]) -> list[tuple[int, int]]:
    """(início, fim) em quadros de cada bloco na tela: entra 2 quadros antes da 1ª palavra e fica até o
    próximo entrar; o último fica até o fim do vídeo (é o quadro final que a checagem de cauda compara)."""
    total = int(timeline["totalFrames"])
    inicios = [max(0, int(b[0]["f0"]) - ENTRA_ANTES) for b in timeline["blocos"] if b]
    return [(ini, inicios[i + 1] if i + 1 < len(inicios) else total) for i, ini in enumerate(inicios)]


def _gravar_legenda(timeline: dict[str, Any], midia: Path, *, cta: str, ritmo: float, palavras_por_bloco: int,
                    stills) -> dict[str, Any]:
    """`caps/NNN.png` (a camada de legenda do próprio render, no último quadro de cada bloco), `caps.txt` e
    `legendas.json` — os artefatos que o perfil `reel` confere —, e os blocos para o SRT."""
    fps = int(timeline["fps"])
    janelas = cartoes_da_legenda(timeline)
    caps = midia / "caps"
    shutil.rmtree(caps, ignore_errors=True)
    caps.mkdir(parents=True)
    nomes = [f"{i:03d}.png" for i in range(len(janelas))]
    stills([fim - 1 for _, fim in janelas], caps, nomes)
    linhas, t = [], 0.0
    if janelas and janelas[0][0] > 0:
        from PIL import Image

        Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(caps / "blank.png")
        linhas.append(f"file 'caps/blank.png'\nduration {round(janelas[0][0] / fps, 3)}\n")
    for nome, (ini, fim) in zip(nomes, janelas):
        linhas.append(f"file 'caps/{nome}'\nduration {round((fim - ini) / fps, 3)}\n")
    if nomes:
        linhas.append(f"file 'caps/{nomes[-1]}'\n")  # o concat do ffmpeg só aplica a duração do último com ele repetido
    (midia / "caps.txt").write_text("".join(linhas), encoding="utf-8")
    legendas = {"blocos": len(janelas), "cta": cta, "duracao": round(int(timeline["totalFrames"]) / fps, 3),
                "offset_audio": 0.0, "ritmo_cadencia": round(ritmo, 3), "palavras_por_bloco": palavras_por_bloco}
    arquivos.gravar_json(midia / "legendas.json", legendas)
    blocos_srt = [{"start": ini / fps, "end": fim / fps, "lines": [" ".join(p["w"] for p in b)]}
                  for (ini, fim), b in zip(janelas, [b for b in timeline["blocos"] if b])]
    return {**legendas, "srt": blocos_srt}


# ---------------------------------------------------------------- produção


def produzir(
    raiz: Path | str,
    dados: Any,
    *,
    cache_fontes: Path | str | None = None,
    embarcados: Path | str | None = None,
    origem: str = "skill",
    agente: str | None = None,
    opcoes_narrar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produz um reel narrado a partir da entrada (ver o módulo)."""
    raiz = Path(raiz)
    e = ler_entrada(dados)
    pasta_template, manifesto = achar_template(raiz, e["template"], embarcados)
    esqueleto = arquivos.ler_json(pasta_template / "cenas.json")
    _conferir_cenas(manifesto, esqueleto, e["cenas"])
    conferir_ancoras(e["roteiro"], e["cenas"])
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducaoReel(str(erro)) from None
    voz_registro = _porta_voz(alma.dados, e["porta_voz"])

    conteudo = {"gancho": e["conteudo"].get("gancho"), "gancho_tipo": e["conteudo"].get("gancho_tipo"),
                "cta": e["cta"], "cta_forma": e["conteudo"].get("cta_forma")}
    peca = modelo.criar(raiz, tipo=TIPO, titulo=e["titulo"], formatos=[FORMATO], pack=e["pack"] or "nucleo",
                        slug=e["slug"], status="roteiro", serie=e["serie"], template=manifesto["template_id"],
                        porta_voz=voz_registro.get("id"), oferta=e["oferta"], conteudo=conteudo, origem=origem,
                        agente=agente)
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    midia, texto, saida = pasta / "midia", pasta / "texto", pasta / "saida"
    for p in (midia, texto, saida):
        p.mkdir(exist_ok=True)
    trabalho = Path(tempfile.mkdtemp(prefix=f"{peca_id}-render-"))
    inicio = time.monotonic()
    provedores: dict[str, str] = {}
    etapa = ["roteiro"]
    avisos: list[str] = []

    def falhou(detalhe: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=None, provedor=None, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3), template_id=manifesto["template_id"])

    try:
        # 1. gate do roteirista, antes de narrar
        arq_roteiro = texto / "roteiro.txt"
        arq_roteiro.write_text(e["roteiro"] + "\n", encoding="utf-8")
        gate = gate_roteiro.revisar_roteiro(e["roteiro"], e["cta"])
        if not gate["aprovado"]:
            raise ErroRoteiroReprovado(peca_id, "roteiro reprovado pelo gate: "
                                       + "; ".join(a["detalhe"] for a in gate["achados"]), gate["achados"])
        Verificador(raiz).escolher_provedor("renderizar_motion")  # sem render possível, não gasta narração

        # 2. narração, uma vez
        etapa[0] = "narrar"
        narr = narrar_base.narrar(raiz, e["roteiro"], voz_registro["id"], TIPO, relativo(raiz, midia),
                                  **(opcoes_narrar or {}))
        provedores["narrar"] = narr["provedor"]
        if narr.get("aviso_ritmo"):
            avisos.append(narr["aviso_ritmo"])

        # 3. montagem: linha do tempo, blocos de legenda e trilha
        etapa[0] = "montar"
        ritmo = _cadencia(narr["alinhamento"])
        por_bloco = e["palavras_por_bloco"] or legenda_reel.palavras_por_bloco(ritmo)
        outras = _trilhas_da_instalacao(raiz, pasta)
        trilha = _escolher_trilha(e["trilha"] or esqueleto["trilha"], outras, explicita=e["trilha"] is not None)
        cenas_peca = montar_cenas(esqueleto, e["cenas"], palavras_por_bloco=por_bloco, trilha=trilha)
        arquivos.gravar_json(midia / "cenas.json", cenas_peca)
        publico = trabalho / "publico"
        assinaturas = trabalho / "assinaturas.json"
        assinaturas.write_text(json.dumps(outras, ensure_ascii=False), encoding="utf-8")
        log_montagem = _montar(midia, midia / narrar_base.ARQUIVO_AUDIO, midia / narrar_base.ARQUIVO_ALINHAMENTO,
                               publico, assinaturas)
        avisos += [l.strip() for l in log_montagem.splitlines() if l.strip().startswith("aviso:")]
        timeline = arquivos.ler_json(publico / "timeline.json")
        if int(timeline["fps"]) != FPS:
            raise ErroProducaoReel(f"a linha do tempo saiu a {timeline['fps']} fps; o perfil reel pede {FPS}")
        shutil.copyfile(publico / "timeline.json", midia / "timeline.json")
        shutil.copyfile(publico / "trilha.wav", midia / "trilha.wav")

        # 4. render do template, com a Alma por props, e os cartões da legenda
        etapa[0] = "renderizar"
        alma_props, avisos_alma = props_alma(alma, publico, raiz=raiz, cache_fontes=cache_fontes,
                                             porta_voz=voz_registro, canal=e["canal"])
        avisos += avisos_alma
        composicao = _id_composicao(manifesto["template_id"])
        projeto = preparar_projeto(pasta_template, trabalho / "projeto", composicao)
        versao = (manifesto.get("versoes") or {}).get("remotion") or remotion.VERSAO_KIT
        if versao != remotion.VERSAO_KIT:
            raise ErroProducaoReel(f"o template pede o Remotion {versao}; o render de template roda sobre o kit "
                                   f"({remotion.VERSAO_KIT})")
        props = {"alma": alma_props, "timeline": timeline, "cta": e["cta"],
                 "audio": {"narracao": "narracao.mp3", "trilha": "trilha.wav"}, "camada": "tudo"}
        bruto = remotion.renderizar(composicao, trabalho / "bruto.mp4", props, projeto=projeto, public_dir=publico)
        provedores["renderizar_motion"] = PROVEDOR_MOTION

        etapa[0] = "legendar"
        props_legenda = {**props, "camada": "legenda", "audio": {"narracao": None, "trilha": None}}

        def stills(quadros: list[int], destino: Path, nomes: list[str]) -> None:
            remotion.stills(composicao, quadros, destino, props_legenda, nomes=nomes, projeto=projeto, public_dir=publico)

        leg = _gravar_legenda(timeline, midia, cta=e["cta"], ritmo=ritmo, palavras_por_bloco=por_bloco, stills=stills)
        arq_srt = saida / "final.srt"
        srt.gravar_srt(leg.pop("srt"), arq_srt)
        provedores["legendar"] = PROVEDOR_LEGENDA

        # 5. mistura normalizada
        etapa[0] = "normalizar"
        final = saida / "final.mp4"
        loud = ffmpeg.normalizar_audio(bruto, final)
        provedores["editar_video"] = PROVEDOR_VIDEO

        # 6. verificação de entrega
        etapa[0] = "verificar"
        art = verificar.Artefatos(caps_txt=midia / "caps.txt", legendas=midia / "legendas.json",
                                  alinhamento=midia / narrar_base.ARQUIVO_ALINHAMENTO, roteiro=arq_roteiro)
        resultado = verificar.verificar(final, PERFIL, art)
        if not resultado["aprovado"]:
            raise ErroVerificacaoReprovada(peca_id, f"verificação reprovada no perfil {PERFIL}: "
                                           + "; ".join(a["detalhe"] for a in resultado["achados"]),
                                           resultado["achados"])
    except _ErroComPeca as erro:
        falhou(str(erro))
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        falhou(f"{etapa[0]}: {type(erro).__name__}: {erro}")
        raise
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    duracao = ffmpeg.sondar(final)["duracao"]
    segundos = round(time.monotonic() - inicio, 3)
    registrar = [
        (final, "final", FORMATO),
        (arq_srt, "srt", FORMATO),
        (midia / "legendas.json", "legenda", None),
        (midia / narrar_base.ARQUIVO_AUDIO, "audio", None),
        (midia / narrar_base.ARQUIVO_ALINHAMENTO, "alinhamento", None),
        (arq_roteiro, "roteiro", None),
    ]
    legenda_post = None
    if e["legenda"]:
        legenda_post = texto / "legenda.txt"
        legenda_post.write_text(e["legenda"].strip() + "\n", encoding="utf-8")
        registrar.append((legenda_post, "legenda", None))
    for caminho, papel, formato in registrar:
        modelo.registrar_arquivo(raiz, peca_id, caminho, papel=papel, formato=formato)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["conteudo"]["roteiro"] = relativo(pasta, arq_roteiro)
        if legenda_post is not None:
            atual["conteudo"]["legenda"] = relativo(pasta, legenda_post)

    modelo._atualizar(raiz, peca_id, aplicar)
    modelo.registrar_producao(raiz, peca_id, capacidades=list(provedores), provedores=provedores, segundos=segundos)
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade="renderizar_motion", provedor=PROVEDOR_MOTION,
                     detalhe=f"reel narrado de {str(round(duracao, 1)).replace('.', ',')} s aprovado no perfil {PERFIL}",
                     arquivos=[c for c, _, _ in registrar], segundos=segundos, template_id=manifesto["template_id"])
    final_peca = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final_peca["status"],
        "tipo": TIPO,
        "template": manifesto["template_id"],
        "pasta": relativo(raiz, pasta),
        "video": relativo(raiz, final),
        "duracao": duracao,
        "arquivos": final_peca["arquivos"],
        "narracao": {"provedor": narr["provedor"], "duracao_s": narr["duracao_s"], "palavras": narr["palavras"]},
        "montagem": {"cenas": len(timeline["cenas"]), "quadros": timeline["totalFrames"], "trilha": trilha},
        "legenda": {"blocos": leg["blocos"], "palavras_por_bloco": leg["palavras_por_bloco"], "cta": leg["cta"],
                    "ritmo_cadencia": leg["ritmo_cadencia"]},
        "loudness": loud,
        "verificacao": resultado,
        "segundos": segundos,
        "avisos": avisos,
    }

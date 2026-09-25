"""Produção do reel de corte: um trecho de vídeo longo vira reel 9:16 com a fala original.

A entrada é um objeto JSON:

    {
      "video": "fontes/aula.mp4",                       vídeo longo local, relativo à raiz da instalação
      "titulo": "...",
      "gancho": ["ATÉ TRÊS", "LINHAS CURTAS"],          gancho textual fixo no topo (obrigatório salvo sem_gancho)
      "sem_gancho": false,                              a válvula --sem-gancho da origem
      "trecho": {"inicio": s, "fim": s} | null,         sem trecho nem plano: os momentos escolhem
      "plano": [{"inicio", "fim", "por_que"}] | null,   corte de vários trechos
      "faixas_ja_usadas": [[s, s], ...] | null,
      "enquadramento": "auto" | "rosto" | "central" | "fundo_desfocado",
      "sem_split": false,
      "correcao": "texto do alinhamento corrigido" | null,   grafias corrigidas (recasar)
      "broll": [{"t", "dur", "termo", "por_que"}] | null,
      "legenda": "texto do post" | null,
      "porta_voz", "serie", "pack", "oferta", "slug"     (opcionais)
    }

O caminho, na ordem (origem: `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:33-54` e os scripts
de `Instragram-Videos/pipeline/`):

1. confere a entrada (erro cita o campo; nada é criado) e cria a peça em `roteiro`;
2. **transcreve** o vídeo longo em varredura (modelo rápido, idioma da Alma) e **escolhe o trecho** pelos
   momentos (a nota é desempate; quem leu os candidatos passa `trecho` ou `plano`);
3. **corta** com reenquadramento 9:16 (`corte.cortar`): segue o rosto, compõe screencast, ou fundo
   desfocado sem rosto; grava `corte.json` (a procedência: vídeo, trechos, enquadramento, `cta: null`);
4. **transcreve o corte** em alinhamento (modelo maior, beam 5): é o texto que vai QUEIMADO na tela; com
   `correcao`, recasa as grafias corrigidas sobre os tempos;
5. **b-roll** opcional pelo banco de imagens, com as regras de colocação cobradas antes de buscar;
6. **legenda** sem CTA e sem atraso (fala gravada: `offset 0`);
7. **compõe** (porta de `compose_cut.py`): b-roll, legenda e o **gancho textual fixo no topo** o vídeo
   inteiro (até 3 linhas, fonte e cores da Alma, escada 84 → 42 px, aviso abaixo de 56 px, na faixa entre
   o topo da interface e o começo do quadro 16:9 do fundo desfocado); o vídeo fecha 0,25 s depois do
   último cartão na grade de quadros; depois a **mistura normalizada** em duas passadas;
8. **verifica** no perfil `corte` (50 a 185 s, cauda ≤ 0,80 s depois da última legenda, sem CTA);
   reprovado, `geracao_falhou` e a peça fica em `roteiro`;
9. registra arquivos (final, srt, legenda, alinhamento, roteiro transcrito, fonte), produção e
   `geracao_concluida`, e passa a peça para `produzida`.

Uso:

    from expxmedia.producao import reel_corte
    r = reel_corte.produzir(raiz, {"video": "fontes/aula.mp4", "titulo": "...", "gancho": ["..."]})
"""
from __future__ import annotations

import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from expxmedia.alma import carregar as alma_carregar
from expxmedia.ambiente.verificar import Verificador
from expxmedia.corte import broll as broll_mod
from expxmedia.corte import cortar, momentos
from expxmedia.legendar import reel as legenda_reel
from expxmedia.legendar import srt
from expxmedia.nucleo import arquivos, rastro
from expxmedia.nucleo.raiz import ErroCaminho, absoluto, relativo
from expxmedia.peca import modelo
from expxmedia.transcrever import recasar, whisper
from expxmedia.video import ffmpeg, montar_pagina, verificar
from expxmedia.video.verificar import ultimo_cartao

__all__ = [
    "ErroProducaoCorte",
    "ErroEntradaCorte",
    "ErroVerificacaoReprovada",
    "GeometriaGancho",
    "GEOMETRIA_GANCHO",
    "CAMPOS",
    "PERFIL",
    "ler_entrada",
    "desenhar_gancho",
    "compor",
    "produzir",
]

TIPO, FORMATO, PERFIL = "reel", "9:16", "corte"
CAMPOS = ("video", "titulo", "gancho", "sem_gancho", "trecho", "plano", "faixas_ja_usadas", "enquadramento",
          "sem_split", "correcao", "broll", "legenda", "porta_voz", "serie", "pack", "oferta", "slug")
PROVEDOR_TRANSCREVER, PROVEDOR_VIDEO, PROVEDOR_LEGENDA, PROVEDOR_BANCO = "whisper_local", "ffmpeg", "local", "pexels"

MAX_LINHAS_GANCHO = 3  # origem: Instragram-Videos/pipeline/compose_cut.py:81
GANCHO_TAM_MAX, GANCHO_TAM_MIN, GANCHO_PASSO = 84, 42, 2  # range(84, 40, -2); origem: Instragram-Videos/pipeline/compose_cut.py:84
GANCHO_TAM_AVISO = 56  # origem: Instragram-Videos/pipeline/compose_cut.py:88
GANCHO_MARGEM = 180  # cabe em W - 180; origem: Instragram-Videos/pipeline/compose_cut.py:86
GANCHO_ENTRELINHA = 1.22  # origem: Instragram-Videos/pipeline/compose_cut.py:91
GANCHO_PAD_X = 80  # origem: Instragram-Videos/pipeline/compose_cut.py:92
GANCHO_PAD_Y = 50  # origem: Instragram-Videos/pipeline/compose_cut.py:93
GANCHO_TOPO_TEXTO = 25  # origem: Instragram-Videos/pipeline/compose_cut.py:100
GANCHO_RAIO = 26  # origem: Instragram-Videos/pipeline/compose_cut.py:98
FECHO_S = 0.25  # o vídeo fecha 0,25 s depois do último cartão; origem: Instragram-Videos/pipeline/compose_cut.py:35
CRF = "19"  # origem: Instragram-Videos/pipeline/compose_cut.py:116
PRESET = "slow"  # origem: Instragram-Videos/pipeline/compose_cut.py:116
AUDIO_BITRATE = "192k"  # origem: Instragram-Videos/pipeline/compose_cut.py:117
AUDIO_TAXA = 48000  # origem: Instragram-Videos/pipeline/compose_cut.py:109
CAUDA_ERRO = 1200  # origem: Instragram-Videos/pipeline/compose_cut.py:119
OFFSET_FALA_GRAVADA = 0.0  # fala gravada não tem beat antes; origem: Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:44 (--offset 0)


@dataclass(frozen=True)
class GeometriaGancho:
    """Faixa do gancho: parâmetro do formato (a interface do canal por cima do vídeo)."""
    largura: int
    altura: int
    fps: int
    topo_ui: int  # acima disso a interface do canal cobre
    faixa_fim: int  # no fundo desfocado o quadro 16:9 começa logo abaixo


GEOMETRIA_GANCHO = GeometriaGancho(
    largura=montar_pagina.GEOMETRIA_VERTICAL.largura,
    altura=montar_pagina.GEOMETRIA_VERTICAL.altura,
    fps=montar_pagina.GEOMETRIA_VERTICAL.fps,
    topo_ui=montar_pagina.GEOMETRIA_VERTICAL.topo_ui,  # origem: Instragram-Videos/pipeline/compose_cut.py:78
    faixa_fim=640,  # origem: Instragram-Videos/pipeline/compose_cut.py:79
)


class ErroProducaoCorte(RuntimeError):
    """A produção do reel de corte não terminou."""


class ErroEntradaCorte(ValueError):
    """Entrada fora do formato; `campo` diz qual. Nada foi criado."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


class ErroVerificacaoReprovada(ErroProducaoCorte):
    """O MP4 saiu e reprovou no perfil corte; a peça ficou em `roteiro`."""

    def __init__(self, peca_id: str, mensagem: str, achados: list[dict[str, Any]]) -> None:
        super().__init__(f"{peca_id}: {mensagem}")
        self.peca_id = peca_id
        self.achados = achados


# ---------------------------------------------------------------- entrada


def _trecho(valor: Any, campo: str) -> dict[str, Any]:
    if not isinstance(valor, dict) or not all(isinstance(valor.get(k), (int, float)) for k in ("inicio", "fim")) \
            or valor["fim"] <= valor["inicio"]:
        raise ErroEntradaCorte(campo, "trecho é {inicio, fim} em segundos, com fim depois do início")
    return {**valor, "inicio": float(valor["inicio"]), "fim": float(valor["fim"])}


def ler_entrada(raiz: Path, dados: Any) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None."""
    if not isinstance(dados, dict):
        raise ErroEntradaCorte("entrada", "a entrada é um objeto JSON")
    extras = sorted(set(dados) - set(CAMPOS))
    if extras:
        raise ErroEntradaCorte(extras[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    e = {campo: dados.get(campo) for campo in CAMPOS}
    for campo in ("video", "titulo"):
        if not isinstance(e[campo], str) or not e[campo].strip():
            raise ErroEntradaCorte(campo, "texto obrigatório")
    try:
        video = absoluto(raiz, e["video"].strip())
    except ErroCaminho as erro:
        raise ErroEntradaCorte("video", str(erro)) from None
    if not video.is_file():
        raise ErroEntradaCorte("video", f"o vídeo {Path(e['video']).name} não existe na instalação")
    e["video"] = relativo(raiz, video)
    e["sem_gancho"] = bool(e["sem_gancho"])
    gancho = e["gancho"]
    if isinstance(gancho, str):
        gancho = gancho.strip().splitlines()
    gancho = [str(l).strip() for l in (gancho or []) if str(l).strip()] if isinstance(gancho, (list, type(None))) else None
    if gancho is None:
        raise ErroEntradaCorte("gancho", "lista de 1 a 3 linhas curtas")
    if not gancho and not e["sem_gancho"]:
        # origem: Instragram-Videos/pipeline/compose_cut.py:71-74
        raise ErroEntradaCorte("gancho", "o corte leva gancho fixo no topo: até 3 linhas curtas em CAIXA ALTA, "
                                         "prometendo só o que a fala entrega (ou sem_gancho de propósito)")
    if len(gancho) > MAX_LINHAS_GANCHO:
        # origem: Instragram-Videos/pipeline/compose_cut.py:81-83
        raise ErroEntradaCorte("gancho", f"{len(gancho)} linhas — o teto é {MAX_LINHAS_GANCHO}: mais que isso a caixa "
                                         "invade o quadro do vídeo e ninguém lê de relance")
    e["gancho"] = [] if e["sem_gancho"] else gancho
    if e["trecho"] is not None and e["plano"] is not None:
        raise ErroEntradaCorte("plano", "informe trecho ou plano, não os dois")
    if e["trecho"] is not None:
        e["trecho"] = _trecho(e["trecho"], "trecho")
    if e["plano"] is not None:
        if not isinstance(e["plano"], list) or not e["plano"]:
            raise ErroEntradaCorte("plano", "lista de trechos {inicio, fim, por_que}")
        e["plano"] = [_trecho(t, "plano") for t in e["plano"]]
    e["faixas_ja_usadas"] = [list(map(float, f)) for f in (e["faixas_ja_usadas"] or [])]
    e["enquadramento"] = e["enquadramento"] or "auto"
    if e["enquadramento"] not in cortar.MODOS:
        raise ErroEntradaCorte("enquadramento", f"um de {', '.join(cortar.MODOS)}")
    e["sem_split"] = bool(e["sem_split"])
    if e["correcao"] is not None and (not isinstance(e["correcao"], str) or not e["correcao"].strip()):
        raise ErroEntradaCorte("correcao", "texto corrigido ou null")
    if e["broll"] is not None:
        if not isinstance(e["broll"], list) or not all(isinstance(p, dict) for p in e["broll"]):
            raise ErroEntradaCorte("broll", "lista de inserções {t, dur, termo, por_que} ou null")
    for campo in ("legenda", "porta_voz", "serie", "pack", "oferta", "slug"):
        if e[campo] is not None and (not isinstance(e[campo], str) or not e[campo].strip()):
            raise ErroEntradaCorte(campo, "texto ou null")
    return e


# ---------------------------------------------------------------- gancho e composição


def desenhar_gancho(linhas: list[str], destino: Path, *, estilo: montar_pagina.EstiloMontagem,
                    geometria: GeometriaGancho = GEOMETRIA_GANCHO) -> dict[str, Any]:
    """PNG transparente do quadro inteiro com a caixa do gancho no topo. Devolve a caixa e o tamanho.

    Cores e fonte da Alma (os papéis do cartão de impacto: caixa em `destaque_2`, letra em `texto`).
    origem: Instragram-Videos/pipeline/compose_cut.py:75-107
    """
    W, H = geometria.largura, geometria.altura
    avisos = []
    tam = GANCHO_TAM_MAX
    for tam in range(GANCHO_TAM_MAX, GANCHO_TAM_MIN - 1, -GANCHO_PASSO):
        f = ImageFont.truetype(str(estilo.fonte), tam)
        if max(f.getlength(l) for l in linhas) <= W - GANCHO_MARGEM:
            break
    f = ImageFont.truetype(str(estilo.fonte), tam)
    if tam < GANCHO_TAM_AVISO:
        avisos.append(f"o gancho só coube a {tam}px — linha comprida demais para ler de relance; encurte ou "
                      "quebre a linha")
    alt_linha = round(tam * GANCHO_ENTRELINHA)
    cx_w = round(max(f.getlength(l) for l in linhas)) + GANCHO_PAD_X
    cx_h = alt_linha * len(linhas) + GANCHO_PAD_Y
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (W - cx_w) // 2
    y0 = max(geometria.topo_ui, geometria.topo_ui + (geometria.faixa_fim - geometria.topo_ui - cx_h) // 2)
    d.rounded_rectangle([x0, y0, x0 + cx_w, y0 + cx_h], radius=GANCHO_RAIO, fill=estilo.cartao_fundo)
    for n, l in enumerate(linhas):
        d.text((W / 2, y0 + GANCHO_TOPO_TEXTO + n * alt_linha + alt_linha / 2), l, font=f,
               fill=estilo.cartao_texto, anchor="mm")
    img.save(destino)
    return {"linhas": list(linhas), "tamanho": tam, "x0": x0, "x1": x0 + cx_w, "y0": y0, "y1": y0 + cx_h,
            "avisos": avisos}


def _sh(args: list[str], **kw: Any) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, **kw)
    except FileNotFoundError as e:
        raise ErroProducaoCorte(f"binário não encontrado: {args[0]}") from e


def compor(pasta: Path, saida: Path, *, brolls: list[dict[str, Any]], gancho_png: str | None,
           geometria: GeometriaGancho = GEOMETRIA_GANCHO, corte: str = "corte9x16.mp4") -> dict[str, Any]:
    """b-roll + legendas + gancho sobre o corte, e a mistura normalizada em `saida`.

    Entradas relativas à `pasta` (o ffmpeg roda com `cwd` nela). origem: Instragram-Videos/pipeline/compose_cut.py:28-140
    """
    W, H, FPS = geometria.largura, geometria.altura, geometria.fps
    leg = arquivos.ler_json(pasta / "legendas.json")
    dur_fonte = ffmpeg.sondar(pasta / corte)["duracao"] or 0.0
    dur = min(leg["duracao"], dur_fonte)
    _, _, fim_cartao = ultimo_cartao(pasta / "caps.txt")
    if fim_cartao > 0:
        # o vídeo fecha no último cartão de legenda, nunca depois (sem tela muda no fim)
        dur = min(dur, math.floor(round((fim_cartao + FECHO_S) * FPS, 6)) / FPS)
    atraso_ms = round(leg.get("offset_audio", 0.0) * 1000)

    entradas = ["-i", corte]
    for b in brolls:
        entradas += ["-i", b["arquivo"]]
    entradas += ["-f", "concat", "-safe", "0", "-i", "caps.txt"]
    i_caps = 1 + len(brolls)
    partes, atual = [], "0:v"
    for k, b in enumerate(brolls, start=1):
        t, d = float(b["t"]), float(b["dur"])
        # setpts desloca o clipe para o instante da inserção; enable liga e desliga
        partes.append(f"[{k}:v]setpts=PTS-STARTPTS+{t}/TB[b{k}]")
        partes.append(f"[{atual}][b{k}]overlay=0:0:enable='between(t,{t},{round(t + d, 3)})'[v{k}]")
        atual = f"v{k}"
    partes.append(f"[{i_caps}:v]format=rgba,fps={FPS},scale={W}:{H}[c]")
    partes.append(f"[{atual}][c]overlay=0:0:shortest=0[vc]")
    atual = "vc"
    if gancho_png:
        entradas += ["-loop", "1", "-i", gancho_png]
        partes.append(f"[{i_caps + 1}:v]format=rgba[g]")
        partes.append(f"[{atual}][g]overlay=0:0:shortest=0[vg]")
        atual = "vg"
    partes.append(f"[{atual}]null[v]")
    partes.append(f"[0:a]aresample={AUDIO_TAXA},asetpts=PTS-STARTPTS"
                  + (f",adelay=delays={atraso_ms}:all=1" if atraso_ms else "") + ",apad[a]")
    bruto = pasta / "bruto.mp4"
    r = _sh(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", ";".join(partes),
             "-map", "[v]", "-map", "[a]", "-t", str(dur),
             "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart", bruto.name], cwd=pasta)
    if r.returncode:
        raise ErroProducaoCorte(f"erro na composição:\n{r.stderr[-CAUDA_ERRO:]}")
    saida.parent.mkdir(parents=True, exist_ok=True)
    try:
        loud = ffmpeg.normalizar_audio(bruto, saida)
    finally:
        bruto.unlink(missing_ok=True)
    return {"video": saida, "duracao": dur, "loudness": loud}


# ---------------------------------------------------------------- produção


def _porta_voz(alma: dict[str, Any], pedido: str | None) -> str | None:
    vozes = [v for v in alma.get("porta_vozes") or [] if isinstance(v, dict)]
    if pedido:
        if not any(v.get("id") == pedido for v in vozes):
            raise ErroEntradaCorte("porta_voz", f"o porta-voz {pedido} não existe na Alma")
        return pedido
    achado = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    return achado.get("id") if achado else None


def produzir(
    raiz: Path | str,
    dados: Any,
    *,
    cache_fontes: Path | str | None = None,
    origem: str = "skill",
    agente: str | None = None,
    url_pexels: str | None = None,
) -> dict[str, Any]:
    """Produz um reel de corte a partir da entrada (ver o módulo)."""
    raiz = Path(raiz)
    e = ler_entrada(raiz, dados)
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducaoCorte(str(erro)) from None
    idioma = whisper.idioma_da_alma(alma.dados)
    if idioma is None:
        raise ErroProducaoCorte("a Alma não tem empresa.idioma: a transcrição precisa do idioma")
    config_momentos = momentos.config_da_alma(alma.dados) if e["trecho"] is None and e["plano"] is None else None
    porta_voz = _porta_voz(alma.dados, e["porta_voz"])

    conteudo = {"gancho": " / ".join(e["gancho"]) if e["gancho"] else None, "gancho_tipo": None, "cta": None,
                "cta_forma": "nenhum"}
    peca = modelo.criar(raiz, tipo=TIPO, titulo=e["titulo"], formatos=[FORMATO], pack=e["pack"] or "nucleo",
                        slug=e["slug"], status="roteiro", serie=e["serie"], porta_voz=porta_voz, oferta=e["oferta"],
                        conteudo=conteudo, origem=origem, agente=agente)
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    midia, texto, saida = pasta / "midia", pasta / "texto", pasta / "saida"
    for p in (midia, texto, saida):
        p.mkdir(exist_ok=True)
    inicio = time.monotonic()
    provedores: dict[str, str] = {}
    avisos: list[str] = []
    etapa = ["transcrever"]
    video = absoluto(raiz, e["video"])

    def falhou(detalhe: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=None, provedor=None, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3))

    try:
        verificador = Verificador(raiz)
        provedores["transcrever"] = verificador.escolher_provedor("transcrever")
        verificador.escolher_provedor("editar_video")

        # 1. varredura e escolha do trecho
        if e["plano"] is not None:
            trechos = e["plano"]
        elif e["trecho"] is not None:
            trechos = [e["trecho"]]
        else:
            varredura = whisper.transcrever(video, idioma=idioma, modo="varredura")
            arquivos.gravar_json(midia / "transcricao.json", varredura)
            etapa[0] = "momentos"
            cands = momentos.candidatos(varredura, config=config_momentos, faixas_ja_usadas=e["faixas_ja_usadas"])
            arquivos.gravar_json(midia / "candidatos.json", cands)
            primeiro = cands["candidatos"][0]
            trechos = [{"inicio": primeiro["inicio"], "fim": primeiro["fim"],
                        "por_que": "primeiro do ranking dos momentos (desempate mecânico)"}]

        # 2. corte com reenquadramento
        etapa[0] = "cortar"
        corte = cortar.cortar_trechos(video, trechos, midia, modo=e["enquadramento"], sem_split=e["sem_split"],
                                      faixas_ja_usadas=e["faixas_ja_usadas"])
        avisos += corte["avisos"]
        shutil.rmtree(midia / "pecas", ignore_errors=True)
        registro_corte = {"video": e["video"], "trechos": corte["trechos"], "inicio": corte["inicio"],
                          "fim": corte["fim"], "duracao": corte["duracao"], "montagem": corte["montagem"],
                          "cta": None}  # o corte não pede comentário (M7: a chave está lá)
        arquivos.gravar_json(midia / "corte.json", registro_corte)
        provedores["editar_video"] = PROVEDOR_VIDEO

        # 3. alinhamento: o texto que vai à tela
        etapa[0] = "alinhar"
        alinh = whisper.transcrever(midia / "corte9x16.mp4", idioma=idioma, modo="alinhamento")
        arquivos.gravar_json(midia / "transcricao_corte.json", alinh)
        roteiro_txt, alinhamento = whisper.para_alinhamento(alinh["palavras"])
        if e["correcao"] is not None:
            alinhamento, trechos_corrigidos = recasar.recasar(alinhamento, e["correcao"])
            roteiro_txt = "".join(alinhamento["characters"])
            if trechos_corrigidos:
                avisos.append(f"{trechos_corrigidos} trecho(s) de grafia recasados sobre os tempos")
        arq_alinhamento = midia / "alinhamento.json"
        arquivos.gravar_json(arq_alinhamento, alinhamento)
        arq_roteiro = texto / "roteiro.txt"
        arq_roteiro.write_text(roteiro_txt + "\n", encoding="utf-8")

        # 4. b-roll
        etapa[0] = "broll"
        insercoes: list[dict[str, Any]] = []
        if e["broll"]:
            problemas = broll_mod.validar_plano(e["broll"], corte["duracao"])
            if problemas:
                raise ErroProducaoCorte("plano de b-roll fora das regras: " + "; ".join(problemas))
            for i, p in enumerate(sorted(e["broll"], key=lambda q: float(q["t"]))):
                kw = {"url_base": url_pexels} if url_pexels else {}
                achado = broll_mod.buscar_broll(raiz, p["termo"], midia, duracao=float(p["dur"]), indice=i, **kw)
                if achado is None:
                    avisos.append(f"b-roll '{p['termo']}' sem resultado válido: a inserção ficou de fora")
                    continue
                achado.pop("descartados", None)
                insercoes.append({"t": round(float(p["t"]), 2), **achado, "por_que": p.get("por_que")})
            provedores["banco_imagens"] = PROVEDOR_BANCO
        total_broll = sum(float(b["dur"]) for b in insercoes)
        arquivos.gravar_json(midia / "brolls.json", {
            "insercoes": insercoes, "total_s": round(total_broll, 2),
            "fracao_do_corte": round(total_broll / corte["duracao"], 3) if corte["duracao"] else 0.0,
            "motivo": None if insercoes else "corte sem b-roll"})

        # 5. legenda sem CTA, fala gravada sem atraso
        etapa[0] = "legendar"
        estilo_leg, avisos_leg = legenda_reel.estilo_da_alma(alma, raiz=raiz, cache=cache_fontes)
        avisos += avisos_leg
        leg = legenda_reel.legendar_reel(alinhamento, roteiro_txt, midia, estilo=estilo_leg, cta=None, sem_cta=True,
                                         offset=OFFSET_FALA_GRAVADA)
        avisos += [a["detalhe"] for a in leg["achados"]]
        arq_srt = saida / "final.srt"
        srt.gravar_srt([{"start": ini, "end": fim, "lines": [txt]}
                        for (_, ini, fim), txt in zip(leg["entradas"], leg["textos"])], arq_srt)
        provedores["legendar"] = PROVEDOR_LEGENDA

        # 6. gancho e composição
        etapa[0] = "montar"
        gancho = None
        if e["gancho"]:
            estilo_mont, avisos_mont = montar_pagina.estilo_da_alma(alma, raiz=raiz, cache=cache_fontes)
            avisos += [a for a in avisos_mont if a not in avisos]
            gancho = desenhar_gancho(e["gancho"], midia / "gancho.png", estilo=estilo_mont)
            avisos += gancho.pop("avisos")
        final = saida / "final.mp4"
        mont = compor(midia, final, brolls=insercoes, gancho_png="gancho.png" if gancho else None)
        if not mont["loudness"]["dentro_do_alvo"]:
            avisos.append(f"loudness fora do alvo depois do limitador: {mont['loudness']['lufs']} LUFS, "
                          f"pico {mont['loudness']['pico']} dBFS")

        # 7. verificação no perfil corte
        etapa[0] = "verificar"
        art = verificar.Artefatos(caps_txt=midia / "caps.txt", legendas=midia / "legendas.json",
                                  alinhamento=arq_alinhamento, roteiro=arq_roteiro)
        resultado = verificar.verificar(final, PERFIL, art)
        if not resultado["aprovado"]:
            raise ErroVerificacaoReprovada(peca_id, "verificação reprovada no perfil corte: "
                                           + "; ".join(a["detalhe"] for a in resultado["achados"]),
                                           resultado["achados"])
        avisos += [a["detalhe"] for a in resultado["avisos"]]
    except ErroVerificacaoReprovada as erro:
        falhou(str(erro))
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        falhou(f"{etapa[0]}: {type(erro).__name__}: {erro}")
        raise

    segundos = round(time.monotonic() - inicio, 3)
    registrar = [
        (final, "final", FORMATO),
        (arq_srt, "srt", FORMATO),
        (midia / "legendas.json", "legenda", None),
        (arq_alinhamento, "alinhamento", None),
        (arq_roteiro, "roteiro", None),
        (midia / "corte.json", "fonte", None),
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
                     agente=agente, capacidade="editar_video", provedor=PROVEDOR_VIDEO,
                     detalhe=f"reel de corte de {str(round(mont['duracao'], 1)).replace('.', ',')} s aprovado no "
                             f"perfil {PERFIL}", arquivos=[c for c, _, _ in registrar], segundos=segundos)
    final_peca = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final_peca["status"],
        "tipo": TIPO,
        "pasta": relativo(raiz, pasta),
        "video": relativo(raiz, final),
        "duracao": mont["duracao"],
        "arquivos": final_peca["arquivos"],
        "trecho": {"inicio": corte["inicio"], "fim": corte["fim"]},
        "corte": {"montagem": corte["montagem"],
                  "enquadramento": [t["enquadramento"] for t in corte["trechos"]]},
        "legenda": {"blocos": leg["blocos"], "palavras_por_bloco": leg["palavras_por_bloco"]},
        "gancho": gancho,
        "broll": insercoes,
        "loudness": mont["loudness"],
        "verificacao": resultado,
        "segundos": segundos,
        "avisos": avisos,
    }

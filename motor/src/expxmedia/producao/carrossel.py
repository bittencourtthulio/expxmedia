"""Produção de carrossel: N slides PNG (e, no carrossel misto, slides MP4), prancha e legenda.txt.

Mesma entrada e mesmo caminho do post único (`producao.post`), com três diferenças: o carrossel
aceita vários slides, na ordem da entrada; sai com a prancha (`previa/prancha.png`, papel
`previa`); e a legenda é obrigatória (`texto/legenda.txt`, papel `legenda`). Kind que não existe
no template é erro antes do render, citando o kind e os kinds disponíveis.

**Carrossel misto (D-06).** Um slide é de vídeo quando traz `"midia": "video"` ou quando o kind dele é
declarado com `midia: video` no template. Ele é renderizado em Remotion pela composição `SlideVideo` do
kit, no formato do carrossel (4:5, 1080x1350), com a Alma por props, e sai em `slides/slide_NN.mp4`. Os
slots do slide de vídeo são os do kind no template (quando o template o declara) ou os do `SlideVideo`:
`etiqueta`, `titulo` e `texto`, mais `duracao_s` (padrão 6 s). Na peça, o slide registra
`midia: video` com `duracao_s` medida no MP4; os de imagem seguem com `duracao_s: null`
(CONTRATO-peca, "Carrossel misto"). A prancha usa um quadro de cada vídeo.

Uso:

    from expxmedia.producao import carrossel
    r = carrossel.produzir(raiz, entrada, base_imagens="pasta/das/imagens")
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.motion import remotion
from expxmedia.nucleo import rastro
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.producao.post import (
    PASTA_RENDER,
    ErroEntradaProducao,
    ErroProducao,
    ErroRenderReprovado,
    ErroSlots,
    ler_entrada,
    produzir_estatico,
)
from expxmedia.render_html import prancha as _prancha
from expxmedia.render_html import renderizar as _renderizar
from expxmedia.template import galeria_local
from expxmedia.video import ffmpeg
from expxmedia.video.verificar import FPS

__all__ = ["ErroProducao", "ErroEntradaProducao", "ErroSlots", "ErroRenderReprovado", "KIND_SLIDE_VIDEO",
           "COMPOSICAO_VIDEO", "produzir"]

TIPO = "carrossel"
COMPOSICAO_VIDEO = "SlideVideo"
CAP_HTML, PROV_HTML = "renderizar_html", "playwright"
CAP_MOTION, PROV_MOTION = "renderizar_motion", "remotion"
DURACAO_PADRAO_S = 6.0
DURACAO_MIN_S, DURACAO_MAX_S = 3.0, 60.0  # vídeo filho de carrossel: até 60 s
QUADRO_PREVIA = 0.6  # quadro da prancha: 60% do vídeo, como a prévia das cenas (motion.previa)
# Slots do slide de vídeo quando o template não declara o kind (os do SlideVideo do kit).
KIND_SLIDE_VIDEO: dict[str, Any] = {
    "midia": "video",
    "duracao_s": DURACAO_PADRAO_S,
    "fit": None,
    "requisitos": [CAP_MOTION],
    "slots": {
        "etiqueta": {"tipo": "texto", "max": 24, "obrigatorio": False, "nota": "pílula do topo"},
        "titulo": {"tipo": "texto", "max": 60, "obrigatorio": True, "nota": "entra palavra a palavra"},
        "texto": {"tipo": "texto", "max": 140, "obrigatorio": False, "nota": "apoio embaixo"},
    },
}


def _eh_video(slide: dict[str, Any], kinds: dict[str, Any]) -> bool:
    return slide.get("midia") == "video" or (kinds.get(slide.get("kind")) or {}).get("midia") == "video"


def _achar_template(raiz: Path, template_id: str, embarcados: Path | str | None) -> Path:
    base_emb = Path(embarcados) if embarcados is not None else galeria_local.pasta_embarcados()
    item = next((i for i in galeria_local.listar(raiz, embarcados=base_emb) if i["template_id"] == template_id), None)
    if item is None:
        raise ErroEntradaProducao("template", f"template '{template_id}' não encontrado")
    if item["erro"] is not None:
        raise ErroEntradaProducao("template", f"template '{template_id}' fora do contrato: {item['erro']}")
    dados = item["dados"]
    if dados.get("tipo") != TIPO or dados.get("motor") not in ("html", "html_remotion"):
        raise ErroEntradaProducao("template", f"template '{template_id}' é {dados.get('tipo')}/{dados.get('motor')}, "
                                              "não carrossel html")
    if dados.get("status") in galeria_local.STATUS_FORA_DA_BUSCA:
        raise ErroEntradaProducao("template", f"template '{template_id}' está {dados['status']}")
    return Path(raiz) / item["caminho"] if item["galeria"] == "local" else base_emb.parent / item["caminho"]


def _duracao(slide: dict[str, Any], kind: dict[str, Any], n: int) -> float:
    valor = slide.get("duracao_s", kind.get("duracao_s") or DURACAO_PADRAO_S)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not DURACAO_MIN_S <= valor <= DURACAO_MAX_S:
        raise ErroSlots([f"slide {n} ({slide.get('kind')}): duracao_s de {DURACAO_MIN_S:g} a {DURACAO_MAX_S:g} s"])
    return float(valor)


def _validar_misto(m: dict[str, Any], slides: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any], dict[str, Any] | None]]:
    """[(n, slide, kind_video|None)]; erros de slot antes de qualquer render, com a numeração da entrada."""
    kinds = m.get("kinds") or {}
    erros: list[str] = []
    plano = []
    for n, s in enumerate(slides, 1):
        video = _eh_video(s, kinds)
        if video:
            declarado = kinds.get(s["kind"]) or {}
            kind = declarado if declarado.get("midia") == "video" else KIND_SLIDE_VIDEO
            limpo = {k: v for k, v in s.items() if k not in ("midia", "duracao_s")}
            modelo_kind = {"tipo": TIPO, "kinds": {s["kind"]: kind}}
        else:
            kind, limpo, modelo_kind = None, dict(s), m
        for erro in _renderizar.validar_copy(modelo_kind, {"slides": [limpo]}):
            erros.append(erro.replace("slide 1", f"slide {n}", 1))
        plano.append((n, s, kind))
    if erros:
        raise ErroSlots(erros)
    return plano


def _produzir_misto(raiz: Path, dados: Any, *, base_imagens=None, embarcados=None, cache_fontes=None,
                    origem: str = "skill", agente: str | None = None) -> dict[str, Any]:
    from expxmedia.producao.reel import props_alma  # a Alma por props das composições do kit

    entrada = ler_entrada(dados, TIPO)
    pasta_template = _achar_template(raiz, entrada["template"].strip(), embarcados)
    m = _renderizar.carregar_template(pasta_template)
    plano = _validar_misto(m, entrada["slides"])
    duracoes = {n: _duracao(s, kind, n) for n, s, kind in plano if kind is not None}
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducao(str(erro)) from None

    formato = m["formato"]
    peca = modelo.criar(
        raiz, tipo=TIPO, titulo=entrada["titulo"], formatos=[formato], pack=entrada["pack"] or "nucleo",
        slug=entrada["slug"], status="roteiro", serie=entrada["serie"], template=m["template_id"],
        porta_voz=entrada["porta_voz"], oferta=entrada["oferta"], conteudo=dict(entrada["conteudo"] or {}),
        origem=origem, agente=agente,
    )
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    temporaria = pasta / PASTA_RENDER
    (pasta / "slides").mkdir(exist_ok=True)
    (pasta / "previa").mkdir(exist_ok=True)
    inicio = time.monotonic()
    imagens = [(n, s) for n, s, kind in plano if kind is None]
    videos = [(n, s) for n, s, kind in plano if kind is not None]
    etapa = [CAP_HTML]

    def falhou(detalhe: str, capacidade: str, provedor: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=capacidade, provedor=provedor, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3), template_id=m["template_id"])

    slides_peca: dict[int, dict[str, Any]] = {}
    miniaturas: dict[int, Path] = {}
    gerados: list[Path] = []
    relatorio: dict[str, Any] = {"slides": [], "fontes": []}
    avisos: list[str] = []
    try:
        if imagens:
            relatorio = _renderizar.renderizar(
                pasta_template, {"slides": [s for _, s in imagens]}, alma, temporaria / "html", raiz=raiz,
                base_copy=base_imagens, cache_fontes=cache_fontes, gerar_prancha=False,
            )
            if not relatorio.get("ok"):
                reprovado = ErroRenderReprovado(peca_id, relatorio)
                falhou("; ".join(reprovado.problemas), CAP_HTML, PROV_HTML)
                raise reprovado
            for item in relatorio["slides"]:
                n = imagens[item["slide"] - 1][0]
                destino = pasta / "slides" / f"slide_{n:02d}.png"
                (temporaria / "html" / item["arquivo"]).replace(destino)
                gerados.append(destino)
                miniaturas[n] = destino
                slides_peca[n] = {"n": n, "kind": item["kind"], "midia": "imagem",
                                  "arquivo": relativo(pasta, destino), "duracao_s": None}
        etapa[0] = CAP_MOTION
        publico = temporaria / "publico"
        alma_props, avisos_alma = props_alma(alma, publico, raiz=raiz, cache_fontes=cache_fontes)
        avisos += avisos_alma
        for n, s in videos:
            props = {"alma": alma_props, "etiqueta": s.get("etiqueta"), "titulo": s.get("titulo") or "",
                     "texto": s.get("texto"), "duracao_s": duracoes[n]}
            destino = pasta / "slides" / f"slide_{n:02d}.mp4"
            remotion.renderizar(COMPOSICAO_VIDEO, destino, props, public_dir=publico)
            quadro = int(round(duracoes[n] * QUADRO_PREVIA * FPS))
            miniaturas[n] = remotion.stills(COMPOSICAO_VIDEO, [quadro], temporaria / "stills", props,
                                            nomes=[f"slide_{n:02d}.png"], public_dir=publico)[0]
            gerados.append(destino)
            slides_peca[n] = {"n": n, "kind": s["kind"], "midia": "video", "arquivo": relativo(pasta, destino),
                              "duracao_s": round(ffmpeg.sondar(destino)["duracao"], 2)}
        prancha = pasta / "previa" / "prancha.png"
        _prancha.gerar_prancha([miniaturas[n] for n in sorted(miniaturas)], prancha)
    except ErroRenderReprovado:
        shutil.rmtree(temporaria, ignore_errors=True)
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        shutil.rmtree(temporaria, ignore_errors=True)
        falhou(f"{type(erro).__name__}: {erro}", etapa[0], PROV_HTML if etapa[0] == CAP_HTML else PROV_MOTION)
        raise
    if imagens:
        (temporaria / "html" / _prancha.NOME_RELATORIO).replace(pasta / "previa" / _prancha.NOME_RELATORIO)
    shutil.rmtree(temporaria, ignore_errors=True)
    segundos = round(time.monotonic() - inicio, 3)

    for destino in sorted(gerados):
        modelo.registrar_arquivo(raiz, peca_id, destino, papel="slide", formato=formato)
    legenda = pasta / "texto" / "legenda.txt"
    legenda.parent.mkdir(exist_ok=True)
    legenda.write_text(entrada["legenda"].strip() + "\n", encoding="utf-8")
    modelo.registrar_arquivo(raiz, peca_id, legenda, papel="legenda", formato=None)
    modelo.registrar_arquivo(raiz, peca_id, prancha, papel="previa", formato=None)
    slides = [slides_peca[n] for n in sorted(slides_peca)]

    def aplicar(atual: dict[str, Any]) -> None:
        atual["slides"] = slides
        atual["conteudo"]["legenda"] = relativo(pasta, legenda)

    modelo._atualizar(raiz, peca_id, aplicar)
    capacidades = ([CAP_HTML] if imagens else []) + [CAP_MOTION]
    provedores = {c: (PROV_HTML if c == CAP_HTML else PROV_MOTION) for c in capacidades}
    modelo.registrar_producao(raiz, peca_id, capacidades=capacidades, provedores=provedores, segundos=segundos)
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade=CAP_MOTION, provedor=PROV_MOTION,
                     detalhe=f"carrossel misto: {len(imagens)} slide(s) de imagem e {len(videos)} de vídeo de "
                             f"{m['template_id']}", arquivos=gerados + [legenda, prancha], segundos=segundos,
                     template_id=m["template_id"])
    final = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    avisos += [f"slide {imagens[s['slide'] - 1][0]} ({s['kind']}): {a['detalhe']}"
               for s in relatorio["slides"] for a in s.get("avisos") or []]
    return {
        "peca_id": peca_id,
        "status": final["status"],
        "tipo": TIPO,
        "template": m["template_id"],
        "pasta": relativo(raiz, pasta),
        "slides": final["slides"],
        "arquivos": final["arquivos"],
        "segundos": segundos,
        "avisos": avisos,
    }


def produzir(raiz: Path | str, dados: Any, **opcoes: Any) -> dict[str, Any]:
    """Produz um carrossel: de imagem pelo caminho estático; com slide de vídeo, o carrossel misto."""
    raiz = Path(raiz)
    slides = dados.get("slides") if isinstance(dados, dict) else None
    misto = isinstance(slides, list) and any(isinstance(s, dict) and s.get("midia") == "video" for s in slides)
    if not misto and isinstance(dados, dict) and isinstance(dados.get("template"), str) and isinstance(slides, list):
        try:
            kinds = _renderizar.carregar_template(_achar_template(raiz, dados["template"].strip(),
                                                                  opcoes.get("embarcados"))).get("kinds") or {}
        except Exception:  # noqa: BLE001 — o caminho estático dá o erro certo
            kinds = {}
        misto = any(isinstance(s, dict) and _eh_video(s, kinds) for s in slides)
    if misto:
        return _produzir_misto(raiz, dados, **opcoes)
    return produzir_estatico(raiz, dados, tipo=TIPO, **opcoes)

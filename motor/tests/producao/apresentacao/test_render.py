"""T-05.10: cenas da apresentação no kit e render em MP4 16:9 + PNG por slide.

- Integração: renderizar um deck de 3 slides gera nesta máquina um MP4 1920×1080 h264 com 240
  quadros por slide e 3 PNGs 1920×1080 (o último quadro de cada slide), com as cores da Alma.
- Funcional: cada tipo de slide do schema do deck tem componente registrado nas cenas do kit
  (conferido executando o módulo das cenas em Node, não só lendo o texto).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from expxmedia.alma import carregar as alma_carregar
from expxmedia.motion import remotion
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.producao.apresentacao import palco
from expxmedia.producao.apresentacao import render
from fixtures.fontes_ficticias import semear_cache

MOTOR = Path(__file__).resolve().parents[3]
KIT = MOTOR / "kit-remotion"
PASTA_CENAS = KIT / "src" / "composicoes" / "Apresentacao"

DECK_3 = {
    "titulo": "Três slides",
    "tema": None,
    "slides": [
        {"tipo": "titulo", "kicker": "Fornada", "titulo": "Pão de <b>verdade</b> leva tempo", "subtitulo": "O que muda quando a massa descansa"},
        {"tipo": "estatisticas", "titulo": "Os números da fornada", "numeros": [
            {"valor": 48, "sufixo": " h", "rotulo": "de fermentação", "fonte": "caderno da padaria, 2026-09-25"},
            {"valor": 2, "sufixo": "", "rotulo": "fornadas por dia", "fonte": "quadro do balcão, 2026-09-25"}]},
        {"tipo": "cta", "titulo": None, "texto": "Separe o seu antes de acabar", "url": None, "imagem": None},
    ],
}


def _hex(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _conta(img, cor, tol=10):
    alvo = _hex(cor)
    return sum(1 for px in img.get_flattened_data() if all(abs(a - b) <= tol for a, b in zip(px[:3], alvo)))


# ---------------------------------------------------------------- integração


@pytest.mark.integracao_local
def test_deck_de_3_slides_gera_mp4_16x9_e_3_pngs(instalacao, tmp_path, requer_binario):
    requer_binario("node")
    ffprobe = requer_binario("ffprobe")
    if not remotion.projeto_pronto(remotion.KIT, remotion.VERSAO_KIT):
        pytest.fail("kit Remotion não instalado: rode a preparação do ambiente (T-01.08)")
    alma = alma_carregar.carregar(instalacao)
    r = render.renderizar(DECK_3, alma, tmp_path / "saida", raiz=instalacao, pasta_pngs=tmp_path / "slides",
                          cache_fontes=semear_cache(tmp_path / "fontes"), contar_slides=False)

    assert r["mp4"] == (tmp_path / "saida" / "apresentacao.mp4").resolve()
    sonda = json.loads(subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
         "stream=codec_name,width,height,r_frame_rate,nb_read_frames", "-of", "json", str(r["mp4"])],
        capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert (sonda["codec_name"], sonda["width"], sonda["height"]) == ("h264", 1920, 1080)
    assert sonda["r_frame_rate"] == "30/1"
    assert int(sonda["nb_read_frames"]) == 3 * 240 == r["quadros"]

    assert [p.name for p in r["pngs"]] == ["slide_01.png", "slide_02.png", "slide_03.png"]
    cores = alma.dados["visual"]["cores"]
    imgs = []
    for png in r["pngs"]:
        assert png.parent == (tmp_path / "slides").resolve()
        img = Image.open(png).convert("RGB")
        assert img.size == (1920, 1080)
        imgs.append(img)
    # último quadro: o conteúdo inteiro já entrou, e é o do slide certo (cada PNG é diferente)
    assert len({im.tobytes() for im in imgs}) == 3
    # o CTA fica na cor da casa (destaque da Alma): o chip com o destino da Alma aparece no último slide
    assert _conta(imgs[2], cores["destaque"]) > 5000
    # o fundo da Alma domina o quadro (nenhuma paleta fixa da origem)
    for img in imgs:
        centro = img.crop((200, 200, 1720, 880)).resize((76, 34))
        assert _conta(centro, cores["fundo"], tol=24) > 0.3 * 76 * 34
    assert not (tmp_path / "saida" / "publico").exists()
    assert not list((tmp_path / "saida").glob(".render-*")), "o public dir temporário foi apagado"


# ---------------------------------------------------------------- funcional


def _esbuild():
    esbuild = KIT / "node_modules" / ".bin" / "esbuild"
    if not esbuild.is_file() or shutil.which("node") is None:
        pytest.fail("kit Remotion sem esbuild/node: rode a preparação do ambiente (T-01.08)")
    return esbuild


@pytest.mark.integracao_local
def test_cada_tipo_do_schema_tem_componente_nas_cenas(tmp_path):
    esbuild = _esbuild()
    sonda = tmp_path / "sonda.tsx"
    sonda.write_text(
        f'import {{ CENAS }} from "{PASTA_CENAS / "cenas"}";\n'
        f'import {{ composicao }} from "{PASTA_CENAS / "index"}";\n'
        "console.log(JSON.stringify({\n"
        "  cenas: Object.fromEntries(Object.entries(CENAS).map(([k, v]) => [k, typeof v === 'function' ? v.name : null])),\n"
        "  id: composicao.id, w: composicao.width, h: composicao.height, fps: composicao.fps,\n"
        "  meta: composicao.calculateMetadata({ props: { ...composicao.defaultProps, framesPorSlide: 240,\n"
        "    deck: { ...composicao.defaultProps.deck, slides: [1, 2, 3] } } }),\n"
        "}));\n",
        encoding="utf-8",
    )
    saida = tmp_path / "sonda.cjs"
    r = subprocess.run([str(esbuild), str(sonda), "--bundle", "--platform=node", "--format=cjs", "--jsx=automatic",
                        f"--outfile={saida}", "--log-level=error"], cwd=KIT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([shutil.which("node"), str(saida)], cwd=KIT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout.strip().splitlines()[-1])
    assert sorted(res["cenas"]) == sorted(_deck.TIPOS), "um componente por tipo do schema, nem mais nem menos"
    # cada tipo aponta para a cena de mesmo nome (Titulo, Declaracao, ...), como no Root da origem
    for tipo, componente in res["cenas"].items():
        assert componente and componente.lower() == tipo, (tipo, componente)
    assert (res["id"], res["w"], res["h"], res["fps"]) == ("Apresentacao", 1920, 1080, 30)
    assert res["meta"] == {"durationInFrames": 720}


def test_quadros_dos_pngs_sao_o_ultimo_de_cada_slide():
    assert render.FRAMES_POR_SLIDE == 240
    assert render.quadros_dos_pngs(3) == [239, 479, 719]
    assert render.quadros_dos_pngs(2, 30) == [29, 59]


def test_cenas_sem_cor_literal_de_marca_e_sem_fps_proprio():
    cenas = (PASTA_CENAS / "cenas.tsx").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{6}\b", cenas), "cor vem da Alma, não de hex no código"
    assert not re.search(r"\bfps\b\s*(?:[:=]\s*\{?\s*)30\b", cenas)
    indice = (PASTA_CENAS / "index.tsx").read_text(encoding="utf-8")
    assert "FPS" in indice and "calculateMetadata" in indice


def test_props_levam_cta_da_alma_imagens_publicadas_e_fontes_em_arquivo(instalacao, tmp_path):
    alma = alma_carregar.carregar(instalacao)
    ativos = tmp_path / "ativos"
    ativos.mkdir()
    (ativos / "print.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    d = json.loads(json.dumps(DECK_3))
    d["slides"][2]["imagem"] = "print.png"
    d["tema"] = {"nome": "Assunto", "cor": None, "logo": "falta.png"}
    publico = tmp_path / "publico"
    p, avisos = render.props(d, alma, publico, ativos=ativos, raiz=instalacao, cache_fontes=semear_cache(tmp_path / "f"))
    cta = p["deck"]["slides"][2]
    assert cta["titulo"] == alma.dados["cta"]["padrao"] and cta["url"] == alma.dados["cta"]["destino"]
    assert cta["imagem"] == "ativos/print.png" and (publico / "ativos" / "print.png").is_file()
    assert p["deck"]["tema"]["logo"] is None and any("falta.png" in a for a in avisos)
    assert p["alma"]["cores"] == alma.dados["visual"]["cores"]
    for papel, familia in (("titulo", "Fraunces"), ("texto", "Nunito Sans")):
        fonte = p["alma"]["fontes"][papel]
        assert fonte["familia"] == familia
        assert {a["peso"] for a in fonte["arquivos"]} == {400, 700}
        assert all((publico / a["caminho"]).is_file() and not Path(a["caminho"]).is_absolute() for a in fonte["arquivos"])
    assert (p["rotulo"], p["empresa"], p["idioma"], p["framesPorSlide"]) == ("Assunto", "Trigo Dourado", "pt-BR", 240)


def test_deck_invalido_para_antes_do_render(instalacao, tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(remotion, "renderizar", lambda *a, **k: chamadas.append(a))
    ruim = json.loads(json.dumps(DECK_3))
    ruim["slides"][0]["tipo"] = "grafico"
    with pytest.raises(palco.ErroDeck) as erro:
        render.renderizar(ruim, alma_carregar.carregar(instalacao), tmp_path, contar_slides=False)
    assert "tipos aceitos" in str(erro.value) and chamadas == []
    with pytest.raises(palco.ErroDeck):  # o deck de 3 slides não é uma apresentação inteira
        render.renderizar(DECK_3, alma_carregar.carregar(instalacao), tmp_path)
    assert chamadas == []

"""T-03.04: prancha dos slides lado a lado e render.json com a impressão digital da renderização."""
from __future__ import annotations

import json

from PIL import Image

from expxmedia.render_html import prancha, renderizar

CSS = """.slide{display:flex;flex-direction:column;padding:80px;background:var(--alma-fundo);color:var(--alma-texto);font-family:var(--alma-fonte-texto)}
h1{font-size:96px;margin:0}.slide.b{background:var(--alma-fundo_alt);color:var(--alma-texto_inverso)}"""
KINDS = {"a": {"vazio_ok": True, "fit": "fixo", "slots": {"t": {"tipo": "texto", "max": 40, "obrigatorio": True}}},
         "b": {"vazio_ok": True, "fit": "fixo", "slots": {"t": {"tipo": "texto", "max": 40, "obrigatorio": True}}}}
FRAG = {"a": "<h1>{{t}}</h1>", "b": "<h1>{{t}}</h1>"}
COPY = {"slides": [{"kind": "a", "t": "Um"}, {"kind": "b", "t": "Dois"}, {"kind": "a", "t": "Três"}]}


def test_numeros_calibrados_da_origem():
    assert (prancha.LADO, prancha.ALTURA, prancha.FOLGA, prancha.FUNDO) == (432, 540, 16, (40, 40, 40))


def test_tres_slides_geram_prancha_lado_a_lado_e_render_json_com_um_registro_por_slide(criar_template, alma_neutra, tmp_path):
    saida = tmp_path / "saida"
    r = renderizar.renderizar(criar_template(KINDS, CSS, FRAG), COPY, alma_neutra(fundo="#ffffff", fundo_alt="#101010"), saida)
    assert r["ok"], r
    assert r["prancha"] == "_prancha.png"
    with Image.open(saida / "_prancha.png") as img:
        folha = img.convert("RGB")
    assert folha.size == (3 * 432 + 4 * 16, 540 + 2 * 16)
    assert folha.getpixel((5, 5)) == (40, 40, 40)                     # a folga
    centro = lambda i: (16 + i * (432 + 16) + 5, 16 + 540 - 5)       # canto de baixo de cada célula, longe do texto
    assert folha.getpixel(centro(0)) == (255, 255, 255)
    assert folha.getpixel(centro(1)) == (16, 16, 16)                  # o do meio é o slide escuro
    assert folha.getpixel(centro(2)) == (255, 255, 255)
    relatorio = json.loads((saida / "render.json").read_text(encoding="utf-8"))
    assert next(iter(relatorio)) == "expxmedia_render"               # M2: a chave de versão vem primeiro
    assert [(s["slide"], s["kind"], s["arquivo"]) for s in relatorio["slides"]] == [(1, "a", "slide_1.png"), (2, "b", "slide_2.png"),
                                                                                   (3, "a", "slide_3.png")]
    assert relatorio["impressao"] == r["impressao"] and len(r["impressao"]) == 16
    texto = (saida / "render.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in texto and str(tmp_path.resolve()) not in texto  # M9: nenhum caminho absoluto
    assert relatorio["em"][-6] in "+-" and relatorio["em"][-3] == ":"  # M5: momento com fuso


def test_mesmas_entradas_mesma_impressao_digital(criar_template, alma_neutra, tmp_path):
    template = criar_template(KINDS, CSS, FRAG)
    a = renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "s1")
    b = renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "s2")
    ler = lambda p: json.loads((p / "render.json").read_text(encoding="utf-8"))["impressao"]
    assert ler(tmp_path / "s1") == ler(tmp_path / "s2") == a["impressao"] == b["impressao"]
    # qualquer entrada que muda o PNG muda a impressão: a copy, a Alma, o CSS
    outra_copy = {"slides": [*COPY["slides"][:2], {"kind": "a", "t": "Quatro"}]}
    assert renderizar.renderizar(template, outra_copy, alma_neutra(), tmp_path / "s3")["impressao"] != a["impressao"]
    assert renderizar.renderizar(template, COPY, alma_neutra(destaque="#123456"), tmp_path / "s4")["impressao"] != a["impressao"]
    (template / "template.css").write_text(CSS + "h1{letter-spacing:1px}", encoding="utf-8")
    assert renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "s5")["impressao"] != a["impressao"]
    # e o que não muda o PNG não muda: título e status do template
    (template / "template.css").write_text(CSS, encoding="utf-8")
    manifesto = json.loads((template / "template.json").read_text(encoding="utf-8"))
    manifesto.update(titulo="Outro título", status="validado")
    (template / "template.json").write_text(json.dumps(manifesto), encoding="utf-8")
    assert renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "s6")["impressao"] == a["impressao"]


def test_prancha_sem_render(tmp_path):
    for i, cor in enumerate([(255, 0, 0), (0, 255, 0)], 1):
        Image.new("RGB", (1080, 1350), cor).save(tmp_path / f"slide_{i}.png")
    destino = prancha.gerar_prancha([tmp_path / "slide_1.png", tmp_path / "slide_2.png"], tmp_path / "_prancha.png")
    with Image.open(destino) as img:
        assert img.size == (2 * 432 + 3 * 16, 540 + 2 * 16)
        assert img.convert("RGB").getpixel((16 + 432 + 16 + 100, 100)) == (0, 255, 0)

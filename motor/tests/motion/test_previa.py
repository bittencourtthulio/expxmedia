"""T-05.04: prévia com guias da área segura.

- Integração: gerar a prévia de uma linha do tempo de 3 cenas produz 3 imagens e uma folha com as três.
- Funcional: cada imagem de prévia tem pixels da cor das guias nas linhas y=220 e y=1500 (na escala da
  prévia) e o quadro de cada cena é o de 60% da duração.
"""
import json
from pathlib import Path

import pytest
from PIL import Image

from expxmedia.motion import previa, remotion

TIMELINE = {
    "fps": 30,
    "totalFrames": 90,
    "cenas": [
        {"id": "abre", "inicio": 0, "dur": 30},
        {"id": "meio", "inicio": 30, "dur": 25},
        {"id": "fecha", "inicio": 55, "dur": 35},
    ],
    "blocos": [],
}


def _linha_tem_guia(img, y_canvas, escala):
    y = round(y_canvas * escala)
    for yy in (y - 1, y, y + 1):
        linha = [img.getpixel((x, yy)) for x in range(0, img.width, 7)]
        vermelhos = sum(1 for r, g, b in linha if r >= 200 and g <= 60 and b <= 60)
        if vermelhos >= 0.9 * len(linha):
            return True
    return False


def test_numeros_da_origem():
    assert previa.ESCALA == 0.3
    assert previa.POSICAO == 0.6
    assert previa.GUIAS == (220, 1500)
    assert previa.COR_GUIA == (255, 0, 0)
    assert previa.COLUNAS == 5
    assert previa.QUALIDADE == 85
    assert [previa.quadro_da_cena(c) for c in TIMELINE["cenas"]] == [18, 45, 76]


def test_guias_e_quadros_com_still_falso(tmp_path, monkeypatch):
    pedidos = {}

    def still_falso(composicao, quadros, pasta, props=None, *, escala, nomes, **kw):
        pedidos.update(composicao=composicao, quadros=quadros, escala=escala, props=props, kw=kw)
        feitos = []
        for nome in nomes:
            p = Path(pasta) / nome
            Image.new("RGB", (round(1080 * escala), round(1920 * escala)), (20, 40, 200)).save(p)
            feitos.append(p)
        return feitos

    monkeypatch.setattr(remotion, "stills", still_falso)
    cenas = TIMELINE["cenas"] * 2 + [{"id": "extra", "inicio": 90, "dur": 10}]  # 7 cenas: 2 linhas na folha
    res = previa.gerar_previa("Qualquer", {"cenas": cenas}, tmp_path / "p", {"a": 1}, public_dir=tmp_path)
    assert pedidos["quadros"] == [18, 45, 76, 18, 45, 76, 96]
    assert pedidos["escala"] == 0.3 and pedidos["props"] == {"a": 1}
    assert pedidos["kw"]["public_dir"] == tmp_path
    assert len(res["imagens"]) == 7
    for png in res["imagens"]:
        img = Image.open(png).convert("RGB")
        assert _linha_tem_guia(img, 220, 0.3) and _linha_tem_guia(img, 1500, 0.3), png
        assert not _linha_tem_guia(img, 900, 0.3)
    folha = Image.open(res["folha"])
    assert res["folha"].suffix == ".jpg"
    assert folha.size == (5 * 324, 2 * 576)


def test_timeline_vazia_e_recusada(tmp_path):
    with pytest.raises(ValueError):
        previa.gerar_previa("Vazio", {"cenas": []}, tmp_path)


@pytest.mark.integracao_local
def test_previa_de_3_cenas_gera_3_imagens_e_uma_folha(tmp_path, requer_binario):
    requer_binario("node")
    arq_tl = tmp_path / "timeline.json"
    arq_tl.write_text(json.dumps(TIMELINE), encoding="utf-8")
    res = previa.gerar_previa("Vazio", arq_tl, tmp_path / "previa", {"duracaoFrames": 90})
    imagens = res["imagens"]
    assert len(imagens) == 3 and all(p.is_file() for p in imagens)
    assert [p.parent for p in imagens] == [tmp_path / "previa"] * 3
    for png in imagens:
        img = Image.open(png).convert("RGB")
        assert img.size == (324, 576)
        assert _linha_tem_guia(img, 220, 0.3), f"{png.name} sem guia em y=220"
        assert _linha_tem_guia(img, 1500, 0.3), f"{png.name} sem guia em y=1500"
        # o fundo da Vazio (preto) continua fora das guias
        assert img.getpixel((img.width // 2, round(900 * 0.3))) == (0, 0, 0)
    folha = Image.open(res["folha"]).convert("RGB")
    assert res["folha"] == tmp_path / "previa" / "previa.jpg"
    assert folha.size == (3 * 324, 576)
    # as três imagens estão na folha, lado a lado (guia visível em cada coluna)
    for col in range(3):
        y = round(220 * 0.3)
        r, g, b = folha.getpixel((col * 324 + 162, y))
        assert r > 180 and g < 90 and b < 90

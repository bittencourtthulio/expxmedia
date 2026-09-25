"""T-04.08: legenda do reel em PNG com card final (porta de `Instragram-Videos/pipeline/captions.py`).

Paridade com o G3 (D-16, D-47): com as entradas do golden, a `alma-golden-reel.json` (que aponta para a
fonte local usada na origem, só nos testes) e o termo multi-palavra do léxico da origem, os blocos
(`caps.txt`) e o `legendas.json` saem iguais e cada PNG difere do golden em no máximo 1% dos pixels
(algum canal acima de 8/255).

A copy do card final ("Comenta <CTA> / para receber o link") é da origem e entra aqui como parâmetro do
teste: no núcleo ela nunca é fixa no código (M13).
"""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from expxmedia.legendar import reel

GOLDEN = Path(__file__).resolve().parents[1] / "golden"
G3 = GOLDEN / "G3"
ALMA_REEL = json.loads((GOLDEN / "G4" / "alma-golden-reel.json").read_text(encoding="utf-8"))
CARD_ORIGEM = ("Comenta {cta}", "para receber o link")  # copy da origem: captions.py:156-157
# o léxico da origem tem um termo de várias palavras (pronuncia.py: TERMOS_MULTI)
PRONUNCIA_ORIGEM = [{"termo": "software house", "fala": "sóftwer ráuse"}, {"termo": "hooks", "fala": "rúks"}]


def _fonte_disponivel():
    return Path(ALMA_REEL["visual"]["fontes"]["titulo"]["arquivo"]).is_file()


def _diferenca(a, b):
    """Fração de pixels em que algum canal RGBA difere mais de 8/255."""
    x = np.asarray(Image.open(a).convert("RGBA"), dtype=np.int16)
    y = np.asarray(Image.open(b).convert("RGBA"), dtype=np.int16)
    assert x.shape == y.shape
    return float((np.abs(x - y).max(axis=2) > 8).mean())


def _legendar_g3(destino, **kw):
    estilo, avisos = reel.estilo_da_alma(ALMA_REEL)
    assert avisos == []
    al = json.loads((G3 / "entradas" / "alignment.json").read_text(encoding="utf-8"))
    roteiro = (G3 / "entradas" / "roteiro.txt").read_text(encoding="utf-8")
    cta = (G3 / "entradas" / "cta.txt").read_text(encoding="utf-8").strip()
    kw.setdefault("termos_multi", reel.termos_multi(PRONUNCIA_ORIGEM))
    return reel.legendar_reel(al, roteiro, destino, estilo=estilo, cta=cta, card_final=CARD_ORIGEM, **kw)


# ------------------------------------------------------------------ integração

@pytest.mark.integracao_local
def test_paridade_com_o_g3(tmp_path):
    if not _fonte_disponivel():
        pytest.skip("fonte local da alma-golden-reel ausente (só existe no macOS, D-47)")
    r = _legendar_g3(tmp_path)

    assert json.loads((tmp_path / "legendas.json").read_text(encoding="utf-8")) == \
        json.loads((G3 / "legendas.json").read_text(encoding="utf-8"))
    assert (tmp_path / "caps.txt").read_text(encoding="utf-8") == (G3 / "caps.txt").read_text(encoding="utf-8")
    assert r["blocos"] == 37 and r["palavras_por_bloco"] == 5 and r["cta"] == "FIRECRAWL"

    golden_pngs = sorted(p.name for p in (G3 / "caps").glob("*.png"))
    assert sorted(p.name for p in (tmp_path / "caps").glob("*.png")) == golden_pngs
    for nome in golden_pngs:
        frac = _diferenca(tmp_path / "caps" / nome, G3 / "caps" / nome)
        assert frac <= 0.01, f"{nome}: {frac:.2%} dos pixels diferem"
        # a caixa ocupa exatamente o mesmo retângulo (1 px de deslocamento passaria no 1%)
        assert Image.open(tmp_path / "caps" / nome).getbbox() == Image.open(G3 / "caps" / nome).getbbox(), nome
    assert r["achados"] == []


@pytest.mark.integracao_local
def test_termo_multi_palavra_nao_racha_e_cores_vem_da_alma(tmp_path):
    if not _fonte_disponivel():
        pytest.skip("fonte local da alma-golden-reel ausente (só existe no macOS, D-47)")
    r = _legendar_g3(tmp_path)
    assert [t for t in r["textos"] if "software" in t.split()] == \
        [t for t in r["textos"] if "house" in t.split()]

    # outra Alma, outra cor de destaque: o CTA do card sai com a cor nova
    alma = json.loads(json.dumps(ALMA_REEL))
    alma["visual"]["cores"]["destaque"] = "#FF00FF"
    estilo, _ = reel.estilo_da_alma(alma)
    assert estilo.cor_cta == (255, 0, 255, 255)
    assert estilo.cor_texto == (255, 255, 255, 255) and estilo.cor_caixa == (0, 0, 0, 205)


# ------------------------------------------------------------------ funcional

def _alinhamento(palavras):
    """Alinhamento por caractere a partir de [(palavra, início, fim)], espaço entre palavras."""
    chars, cs, ce = [], [], []
    for i, (w, s, e) in enumerate(palavras):
        if i:
            chars.append(" "); cs.append(palavras[i - 1][2]); ce.append(s)
        passo = (e - s) / len(w)
        for k, c in enumerate(w):
            chars.append(c); cs.append(s + k * passo); ce.append(s + (k + 1) * passo)
    return {"characters": chars, "character_start_times_seconds": cs, "character_end_times_seconds": ce}


def _estilo_embarcado():
    alma = json.loads(json.dumps(ALMA_REEL))
    alma["visual"]["fontes"] = {"titulo": {"familia": None, "origem": "google"},
                                "texto": {"familia": None, "origem": "google"}}
    estilo, avisos = reel.estilo_da_alma(alma)
    assert avisos and "embarcada" in avisos[0]  # a troca de fonte nunca é silenciosa
    return estilo


def test_roteiro_sem_a_palavra_do_cta_levanta_erro(tmp_path):
    al = _alinhamento([("Isto", 0.0, 0.3), ("funciona.", 0.4, 0.9)])
    with pytest.raises(reel.ErroCtaAusente, match="PALAVRA"):
        reel.legendar_reel(al, "Isto funciona.", tmp_path, estilo=_estilo_embarcado(), cta="palavra")


def test_sem_cta_declarado_nao_infere_pela_caixa_alta(tmp_path):
    al = _alinhamento([("Baixe", 0.0, 0.3), ("o", 0.35, 0.4), ("PDF.", 0.45, 0.9)])
    with pytest.raises(reel.ErroCtaNaoDeclarado, match="caixa alta"):
        reel.legendar_reel(al, "Baixe o PDF.", tmp_path, estilo=_estilo_embarcado(), cta=None)
    # declarado sem CTA: sem card final e sem palavra destacada
    r = reel.legendar_reel(al, "Baixe o PDF.", tmp_path, estilo=_estilo_embarcado(), cta=None, sem_cta=True)
    assert r["cta"] is None and not (tmp_path / "caps" / "end.png").exists()


def test_alinhamento_com_metade_dos_cartoes_curtos_devolve_achado_de_legibilidade(tmp_path):
    palavras, t = [], 0.0
    for _ in range(4):
        palavras.append(("Sim.", t, t + 0.3)); t += 0.9           # cartão de 0,3 s: curto
        for w in ("Isto", "fica", "bastante."):                   # cartão de ~1,2 s
            palavras.append((w, t, t + 0.35)); t += 0.42
        t += 0.6
    al = _alinhamento(palavras)
    roteiro = " ".join(w for w, *_ in palavras)
    r = reel.legendar_reel(al, roteiro, tmp_path, estilo=_estilo_embarcado(), cta=None, sem_cta=True)
    assert r["blocos"] == 8
    (achado,) = r["achados"]
    assert achado["checagem"] == "legibilidade"
    assert achado["obtido"] == 0.5
    assert "35%" in achado["esperado"] and "0.7" in achado["esperado"]


def test_card_final_desce_a_escada_e_segura_2_2_s(tmp_path):
    al = _alinhamento([("Comenta", 0.0, 0.4), ("SUPERCALIFRAGILISTICO", 0.5, 1.6)])
    r = reel.legendar_reel(al, "Comenta SUPERCALIFRAGILISTICO", tmp_path, estilo=_estilo_embarcado(),
                           cta="supercalifragilistico", card_final=("Comenta {cta}", "agora mesmo"))
    png, ini, fim = r["entradas"][-1]
    assert png == "caps/end.png"
    assert round(fim - ini, 3) == 2.2
    assert round(ini - r["entradas"][-2][2], 3) == 0.15
    assert r["tamanho_card"] < 88  # CTA longo não coube a 88 px
    alfa = np.asarray(Image.open(tmp_path / "caps" / "end.png"))[..., 3]
    ys, xs = np.nonzero(alfa)
    # texto na largura útil (1080 − 140 = 940) + 72 px de caixa: a caixa começa em x ≥ 34
    assert xs.min() >= 34 and xs.max() <= 1080 - 34
    assert ys.max() == 1499  # a base da caixa para uma linha antes da área segura (1920 − 420 − 1)
    assert r["duracao"] == round(fim + 0.4, 2)


def test_termo_multi_palavra_do_lexico_nao_racha_entre_blocos_nem_linhas(tmp_path):
    pal = [(w, i * 0.3, i * 0.3 + 0.25) for i, w in
           enumerate(["Nossa", "empresa", "de", "software", "house", "cresceu", "muito", "este", "ano."])]
    al = _alinhamento(pal)
    roteiro = " ".join(w for w, *_ in pal)
    sem = reel.legendar_reel(al, roteiro, tmp_path / "sem", estilo=_estilo_embarcado(), cta=None, sem_cta=True)
    assert sem["palavras_por_bloco"] == 4
    assert sem["textos"][0] == "Nossa empresa de software"  # sem o léxico, o termo racha
    termos = reel.termos_multi([{"termo": "Software House", "fala": "x"}, {"termo": "hooks", "fala": "y"}])
    assert termos == (("software", "house"),)
    com = reel.legendar_reel(al, roteiro, tmp_path / "com", estilo=_estilo_embarcado(), cta=None, sem_cta=True,
                             termos_multi=termos)
    assert com["textos"][0] == "Nossa empresa de software house"


def test_constantes_calibradas():
    assert reel.ESCADA_LEGENDA == (78, 72, 66, 60, 54)
    assert reel.ESCADA_CARD == (88, 80, 72, 66, 60, 54, 48)
    assert reel.CAIXA_BASE == 1499 and reel.SEGURA_CTA == 2.2 and reel.OFFSET_PADRAO == 0.6
    assert reel.palavras_por_bloco(4.07) == 5 and reel.palavras_por_bloco(1.0) == 3 and reel.palavras_por_bloco(9) == 6

"""T-02.06: catálogo de capacidades do núcleo, derivadas e fornecidas por pack."""
import re
from pathlib import Path

import pytest

from expxmedia.ambiente import catalogo

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contrato" / "CONTRATO-capacidades.md"

FORNECE_INSTAGRAM = {
    "id": "metricas_instagram",
    "descricao": "alcance, salvos e retenção por peça publicada no Instagram",
    "provedores": [
        {"id": "meta_graph", "env": ["META_GRAPH_TOKEN", "META_IG_USER_ID"], "cli": None, "binarios": []}
    ],
    "como_habilitar": "Coloque META_GRAPH_TOKEN e META_IG_USER_ID no .env. Onde conseguir: developers.facebook.com.",
}


def _capacidades_do_contrato():
    """Ids e provedores da tabela 'O catálogo do núcleo' do contrato, lidos do Markdown."""
    texto = CONTRATO.read_text(encoding="utf-8")
    secao = texto.split("## O catálogo do núcleo", 1)[1].split("Exemplos de capacidades", 1)[0]
    tabela = {}
    for linha in secao.splitlines():
        m = re.match(r"^\| `([a-z_]+)` \|[^|]*\| ([^|]+) \|", linha)
        if m:
            tabela[m.group(1)] = re.findall(r"`([a-z_]+)`", m.group(2))
    return tabela


# ---------- funcional: exatamente as capacidades do contrato ----------

def test_catalogo_tem_exatamente_as_capacidades_do_contrato():
    tabela = _capacidades_do_contrato()
    assert len(tabela) == 16  # guarda contra leitura errada da tabela
    cat = catalogo.Catalogo()
    assert [c.id for c in cat.capacidades()] == list(tabela)
    for cap_id, provedores in tabela.items():
        cap = cat.obter(cap_id)
        assert cap.origem == "nucleo"
        assert [p.id for p in cap.provedores if not p.somente_teste] == provedores, cap_id


def test_legendar_e_derivada_de_narrar_ou_transcrever():
    legendar = catalogo.Catalogo().obter("legendar")
    assert legendar.derivada_de == ("narrar", "transcrever")
    (local,) = legendar.provedores
    assert local.id == "local" and local.env == () and local.cli is None and local.binarios == ()
    # nenhuma outra capacidade do núcleo é derivada
    outras = [c.id for c in catalogo.Catalogo().capacidades() if c.derivada_de]
    assert outras == ["legendar"]


def test_nomes_canonicos_do_env():
    cat = catalogo.Catalogo()
    env = lambda cap, prov: cat.obter(cap).provedor(prov).env
    assert env("narrar", "elevenlabs") == ("ELEVENLABS_API_KEY",)
    assert env("avatar", "heygen") == ("HEYGEN_API_KEY",)
    assert env("imagem_ia", "openrouter") == ("OPENROUTER_API_KEY",)
    assert env("banco_imagens", "pexels") == ("PEXELS_API_KEY",)
    expx = ("EXPXFLOW_API_KEY", "EXPXFLOW_CLIENT_ID", "EXPXFLOW_BASE_URL")
    for cap in ("publicar", "agendar", "automacao_dm"):
        assert env(cap, "expxflow") == expx
    for cap in ("publicar", "agendar"):
        assert env(cap, "meta_graph") == ("META_GRAPH_TOKEN", "META_IG_USER_ID")
    assert env("publicar", "youtube_api") == ("YOUTUBE_CLIENT_SECRET_FILE",)
    assert cat.obter("publicar").provedor("youtube_api").marcadores == ("oauth_youtube",)
    assert "youtube_api" not in [p.id for p in cat.obter("agendar").provedores]
    # meta_graph só agenda com o agendador local instalado
    assert cat.obter("agendar").provedor("meta_graph").marcadores == ("agendador_local",)
    assert cat.obter("publicar").provedor("meta_graph").marcadores == ()
    assert "META_PAGE_ID" in cat.obter("publicar").provedor("meta_graph").env_opcional


def test_satisfeito_por_binario_e_cli():
    cat = catalogo.Catalogo()
    assert cat.obter("renderizar_html").provedor("playwright").binarios == ("chromium-playwright",)
    assert cat.obter("capturar_pagina").provedor("playwright").binarios == ("chromium-playwright",)
    assert cat.obter("renderizar_motion").provedor("remotion").binarios == ("node>=20", "ffmpeg")
    assert cat.obter("editar_video").provedor("ffmpeg").binarios == ("ffmpeg",)
    assert cat.obter("transcrever").provedor("whisper_local").binarios == ("whisper|faster-whisper",)
    for cap in ("rosto_ia", "video_ia"):
        assert cat.obter(cap).provedor("higgsfield").cli == "higgsfield"
    galeria = cat.obter("galeria_compartilhada").provedor("github")
    assert galeria.cli == "gh" and galeria.marcadores == ("aceite_galeria",)


def test_porta_voz_nas_capacidades_que_dependem_dele():
    cat = catalogo.Catalogo()
    assert cat.obter("narrar").porta_voz == "voz.voz_id"
    assert cat.obter("avatar").porta_voz == "avatar.avatar_id"
    assert cat.obter("rosto_ia").porta_voz == "rosto_ia.id"
    com_porta_voz = [c.id for c in cat.capacidades() if c.porta_voz]
    assert com_porta_voz == ["narrar", "avatar", "rosto_ia"]


def test_provedor_de_teste_so_com_a_flag():
    cat = catalogo.Catalogo()
    for cap in ("narrar", "avatar"):
        assert [p.id for p in cat.obter(cap).provedores_ativos(teste=False)] != []
        assert "teste" not in [p.id for p in cat.obter(cap).provedores_ativos(teste=False)]
        ativos = [p.id for p in cat.obter(cap).provedores_ativos(teste=True)]
        assert ativos[-1] == "teste"  # sempre depois do real: a ordem da tabela decide (regra 2)
        assert cat.obter(cap).provedor("teste").somente_teste
    todos_de_teste = [c.id for c in cat.capacidades() for p in c.provedores if p.somente_teste]
    assert todos_de_teste == ["narrar", "avatar"]
    assert catalogo.FLAG_TESTE == "EXPXMEDIA_PROVEDORES_TESTE"


def test_todo_provedor_real_diz_como_habilitar():
    for cap in catalogo.Catalogo().capacidades():
        for prov in cap.provedores:
            assert prov.como_habilitar.strip(), (cap.id, prov.id)
            for nome in prov.env:
                assert nome in prov.como_habilitar, (cap.id, prov.id, nome)


# ---------- integração: capacidade fornecida por pack com os mesmos campos ----------

def test_capacidade_de_pack_aparece_com_os_mesmos_campos():
    cat = catalogo.Catalogo()
    cat.registrar_pack("expx-instagram", [FORNECE_INSTAGRAM])
    do_pack = cat.descrever("metricas_instagram")
    do_nucleo = cat.descrever("narrar")
    assert set(do_pack) == set(do_nucleo)
    assert set(do_pack["provedores"][0]) == set(do_nucleo["provedores"][0])
    assert do_pack["origem"] == "expx-instagram" and do_nucleo["origem"] == "nucleo"
    assert do_pack["provedores"][0]["env"] == ["META_GRAPH_TOKEN", "META_IG_USER_ID"]
    assert do_pack["provedores"][0]["como_habilitar"] == FORNECE_INSTAGRAM["como_habilitar"]
    assert "metricas_instagram" in [c.id for c in cat.capacidades()]
    assert cat.capacidades()[-1].id == "metricas_instagram"  # depois das do núcleo
    # descrever de todas as capacidades tem a mesma forma
    formas = {tuple(sorted(cat.descrever(c.id))) for c in cat.capacidades()}
    assert len(formas) == 1


def test_sem_o_pack_a_capacidade_nao_existe():
    cat = catalogo.Catalogo()
    assert "metricas_instagram" not in [c.id for c in cat.capacidades()]
    with pytest.raises(catalogo.ErroCatalogo, match="metricas_instagram"):
        cat.obter("metricas_instagram")


def test_pack_nao_pode_repetir_id_do_nucleo_nem_vir_malformado():
    cat = catalogo.Catalogo()
    repetida = dict(FORNECE_INSTAGRAM, id="narrar")
    with pytest.raises(catalogo.ErroCatalogo, match="narrar"):
        cat.registrar_pack("expx-x", [repetida])
    sem_provedor = dict(FORNECE_INSTAGRAM, provedores=[])
    with pytest.raises(catalogo.ErroCatalogo):
        cat.registrar_pack("expx-x", [sem_provedor])
    sem_como = {k: v for k, v in FORNECE_INSTAGRAM.items() if k != "como_habilitar"}
    with pytest.raises(catalogo.ErroCatalogo, match="como_habilitar"):
        cat.registrar_pack("expx-x", [sem_como])
    cat.registrar_pack("expx-instagram", [FORNECE_INSTAGRAM])
    with pytest.raises(catalogo.ErroCatalogo, match="metricas_instagram"):
        cat.registrar_pack("expx-outro", [FORNECE_INSTAGRAM])


def test_catalogos_sao_independentes():
    a = catalogo.Catalogo()
    a.registrar_pack("expx-instagram", [FORNECE_INSTAGRAM])
    assert "metricas_instagram" not in [c.id for c in catalogo.Catalogo().capacidades()]

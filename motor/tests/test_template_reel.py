"""T-05.05: template de reel embarcado (templates/reel/narrado-cartao), código Remotion sobre o kit (D-05, D-31).

- Funcional: o template passa em `template.validar` no modo `template` sem nenhum achado (sem cor literal,
  imports só de react, remotion e @expxmedia/template), com versões travadas e dependências exatas; o
  cenas.json traz eventos e sons de todo kind; o exemplo usa todos os kinds, na ordem da sequência, e as
  âncoras casam com o roteiro. Controles: cor de marca no código e import do kit por caminho relativo reprovam.
- Integração: o projeto de render do template passa no `tsc`, e o exemplo renderiza com a Alma fictícia e
  o provedor de teste e passa no perfil `reel` da verificação, com as cores da Alma no quadro.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from expxmedia.motion import remotion
from expxmedia.nucleo import arquivos
from expxmedia.peca import modelo
from expxmedia.producao import reel
from expxmedia.template import galeria_local, validar
from expxmedia.video import verificar
from fixtures.fontes_ficticias import semear_cache

PASTA = Path(__file__).resolve().parents[2] / "templates" / "reel" / "narrado-cartao"


def _json(nome):
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- funcional


def test_validar_modo_template_sem_achado():
    assert validar.validar_template(PASTA, modo="template") == []


def test_manifesto_trava_versoes_e_dependencias_exatas():
    m = _json("template.json")
    assert list(m)[0] == "expxmedia_template"
    assert (m["tipo"], m["motor"], m["formato"], m["canvas"]) == ("reel", "remotion", "9:16", {"w": 1080, "h": 1920})
    assert m["versoes"]["remotion"] == remotion.VERSAO_KIT == "4.0.528"
    assert m["versoes"]["motor"]
    assert m["requisitos"] == ["narrar", "renderizar_motion", "legendar"]
    assert m["template_id"] == reel.TEMPLATE_PADRAO
    pacote = _json("package.json")
    assert pacote["dependencies"] == m["dependencias"]
    for nome, versao in pacote["dependencies"].items():
        assert versao[0].isdigit() and not any(c in versao for c in "^~*x<>"), (nome, versao)
    kit = json.loads((remotion.KIT / "package.json").read_text(encoding="utf-8"))["dependencies"]
    assert all(kit[n] == v for n, v in pacote["dependencies"].items())  # as mesmas do kit que renderiza
    assert m["origem"] == {"tipo": "criado", "id_compartilhado": None, "inspiracao": None}
    assert not (PASTA / "referencia").exists() and not (PASTA / "previa").exists()


def test_todo_kind_tem_eventos_e_o_exemplo_prova_todos():
    m, esqueleto, exemplo = _json("template.json"), _json("cenas.json"), _json("exemplo.json")
    assert sorted(esqueleto["kinds"]) == sorted(m["kinds"]) == sorted(m["sequencia"])
    for kind, padrao in esqueleto["kinds"].items():
        for ref, *_ in padrao["sons"]:
            assert all(k == "0" or k in padrao["ev"] for k in ref.split("+")), (kind, ref)
    assert [c["kind"] for c in exemplo["cenas"]] == m["sequencia"]
    reel._conferir_cenas(m, esqueleto, exemplo["cenas"])
    reel.conferir_ancoras(exemplo["roteiro"], exemplo["cenas"])
    assert exemplo["template"] == m["template_id"]
    assert 130 <= len(exemplo["roteiro"].split()) <= 180 and exemplo["cta"] in exemplo["roteiro"]
    # a composição registra os mesmos kinds do manifesto
    cenas_tsx = (PASTA / "src" / "cenas.tsx").read_text(encoding="utf-8")
    for kind in m["kinds"]:
        assert f"  {kind}: " in cenas_tsx, kind


def test_galeria_local_encontra_o_template(instalacao, monkeypatch):
    # narrar habilitada pelo provedor de teste: sem ela a busca descarta o template (requisito efetivo)
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    assert reel.TEMPLATE_PADRAO not in [a["template_id"] for a in galeria_local.buscar(instalacao, tipo="reel", formato="9:16")]
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    achados = galeria_local.buscar(instalacao, tipo="reel", formato="9:16")
    assert reel.TEMPLATE_PADRAO in [a["template_id"] for a in achados]
    pasta, dados = reel.achar_template(instalacao, None)
    assert pasta.resolve() == PASTA.resolve() and dados["motor"] == "remotion"


def test_controle_cor_de_marca_e_import_do_kit_reprovam(tmp_path):
    copia = tmp_path / "narrado-cartao"
    shutil.copytree(PASTA, copia)
    cenas = copia / "src" / "cenas.tsx"
    cenas.write_text(cenas.read_text(encoding="utf-8") + '\nexport const FUNDO_FIXO = "#1D3547";\n', encoding="utf-8")
    comp = copia / "src" / "Composicao.tsx"
    comp.write_text('import { mola as m2 } from "../../../../motor/kit-remotion/src/kit/anim";\n'
                    + comp.read_text(encoding="utf-8"), encoding="utf-8")
    tipos = sorted(a["tipo"] for a in validar.validar_template(copia, modo="template"))
    assert tipos == ["cor_literal", "import_proibido"]


# ---------------------------------------------------------------- integração


@pytest.mark.integracao_local
def test_projeto_de_render_do_template_passa_no_tsc(tmp_path, requer_binario):
    node = requer_binario("node")
    projeto = reel.preparar_projeto(PASTA, tmp_path / "projeto", "reel-teste")
    indice = (projeto / "node_modules" / "@expxmedia" / "template" / "index.ts").read_text(encoding="utf-8")
    assert all(m in indice for m in reel.MODULOS_KIT)
    assert (projeto / "src" / "composicoes" / "reel-teste" / "Composicao.tsx").is_file()
    tsc = remotion.KIT / "node_modules" / "typescript" / "bin" / "tsc"
    r = subprocess.run([node, str(tsc), "-p", str(projeto / "tsconfig.json")], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]


@pytest.fixture(scope="module")
def produzido(tmp_path_factory):
    import importlib.util

    spec = importlib.util.spec_from_file_location("_fix_inst_reel", Path(__file__).parent / "fixtures" / "instalacao.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    for binario in ("node", "ffmpeg", "ffprobe"):
        if shutil.which(binario) is None:
            pytest.skip(f"binário ausente: {binario}")
    base = tmp_path_factory.mktemp("template-reel")
    raiz = modulo.montar_instalacao(base / "instalacao")
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    cache = semear_cache(base / "fontes")
    r = reel.produzir(raiz, _json("exemplo.json"), cache_fontes=cache, opcoes_narrar={"palavras_por_segundo": 3.5})
    return raiz, r


@pytest.mark.integracao_local
def test_exemplo_renderiza_com_a_alma_ficticia_e_passa_no_perfil_reel(produzido):
    raiz, r = produzido
    assert r["status"] == "produzida" and r["template"] == reel.TEMPLATE_PADRAO
    assert r["verificacao"]["aprovado"] is True and r["verificacao"]["perfil"] == "reel", r["verificacao"]
    pasta = modelo.pasta(raiz, r["peca_id"])
    midia = pasta / "midia"
    refeita = verificar.verificar(pasta / "saida" / "final.mp4", "reel", verificar.Artefatos(
        caps_txt=midia / "caps.txt", legendas=midia / "legendas.json", alinhamento=midia / "alinhamento.json",
        roteiro=pasta / "texto" / "roteiro.txt"))
    assert refeita["aprovado"], refeita["achados"]
    assert set(verificar.PERFIS["reel"].checagens) == set(verificar.ONZE)
    s = verificar.ffmpeg.sondar(pasta / "saida" / "final.mp4")
    assert (s["largura"], s["altura"], s["fps"]) == (1080, 1920, "30/1")
    assert 30 <= r["duracao"] <= 70
    peca = modelo.carregar(raiz, r["peca_id"])
    assert peca["template"] == reel.TEMPLATE_PADRAO
    assert peca["producao"]["provedores"]["renderizar_motion"] == "remotion"


@pytest.mark.integracao_local
def test_quadro_veste_as_cores_da_alma(produzido, tmp_path):
    raiz, r = produzido
    final = modelo.pasta(raiz, r["peca_id"]) / "saida" / "final.mp4"
    alma = arquivos.ler_json(raiz / "alma" / "alma.json")
    cores = alma["visual"]["cores"]
    quadro = tmp_path / "q.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3", "-i", str(final), "-frames:v", "1", str(quadro)], check=True)
    px = np.asarray(Image.open(quadro).convert("RGB"), int)

    def fracao(hexa, tol=10):
        alvo = np.array([int(hexa[i:i + 2], 16) for i in (1, 3, 5)])
        return float((np.abs(px - alvo).max(axis=2) <= tol).mean())

    assert fracao(cores["fundo"]) > 0.15  # fundo da tela
    assert fracao(cores["texto"]) > 0.05  # cartão escuro da 1ª cena
    assert fracao(cores["destaque"]) > 0.002  # legenda dita, barra, etiqueta
    assert fracao("#E4602A", tol=4) == 0.0  # nada da cor de marca do reel de origem

"""T-01.05: kit Remotion com versões travadas e registro gerado (D-17, D-46).

- Funcional: o package.json declara os pacotes do kit em versão exata (sem ^ nem ~), nas versões
  do plano, e cada um está instalado em node_modules na versão declarada; o package-lock.json
  trava as mesmas versões.
- Integração: scripts/registrar.mjs descobre as pastas de src/composicoes/* e grava o registro
  de forma atômica; `npx remotion compositions src/index.ts` lista a composição Vazio.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

MOTOR = Path(__file__).resolve().parents[1]
KIT = MOTOR / "kit-remotion"
REGISTRO = KIT / "src" / "composicoes" / "registro.generated.ts"

REMOTION = "4.0.528"  # D-17
ESPERADO = {
    "remotion": REMOTION,
    "@remotion/bundler": REMOTION,
    "@remotion/renderer": REMOTION,
    "@remotion/cli": REMOTION,
    "@remotion/fonts": REMOTION,
    "@remotion/captions": REMOTION,
    "@remotion/layout-utils": REMOTION,
    "react": "19.3.0",  # D-17
    "react-dom": "19.3.0",
    "typescript": "5.8.3",
    "@types/react": "19.3.0",  # origem: Instragram-Videos/remotion/node_modules/@types/react/package.json:3
    "@fontsource/inter": "5.3.0",  # origem: Instragram-Videos/remotion/package.json:10
}
EXATA = re.compile(r"^\d+\.\d+\.\d+$")


def _package():
    return json.loads((KIT / "package.json").read_text(encoding="utf-8"))


def _declarados():
    pkg = _package()
    return {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}


# ---------------------------------------------------------------- funcional


def test_package_declara_todos_os_pacotes_do_plano_nas_versoes_do_plano():
    declarados = _declarados()
    faltando = sorted(set(ESPERADO) - set(declarados))
    assert not faltando, f"pacotes ausentes do package.json: {faltando}"
    for nome, versao in ESPERADO.items():
        assert declarados[nome] == versao, f"{nome}: declarado {declarados[nome]!r}, plano {versao!r}"


def test_nenhuma_versao_declarada_usa_intervalo():
    for nome, versao in _declarados().items():
        assert "^" not in versao and "~" not in versao, f"{nome} usa intervalo: {versao}"
        assert EXATA.match(versao), f"{nome} não está em versão exata: {versao}"


@pytest.mark.parametrize("nome", sorted(ESPERADO))
def test_pacote_instalado_na_versao_declarada(nome):
    declarada = _declarados()[nome]
    manifesto = KIT / "node_modules" / nome / "package.json"
    assert manifesto.is_file(), f"{nome} não está em node_modules (rode npm ci no kit)"
    instalada = json.loads(manifesto.read_text(encoding="utf-8"))["version"]
    assert instalada == declarada, f"{nome}: instalado {instalada}, declarado {declarada}"


def test_lock_trava_as_versoes_declaradas():
    lock = json.loads((KIT / "package-lock.json").read_text(encoding="utf-8"))
    raiz = lock["packages"][""]
    assert {**raiz.get("dependencies", {}), **raiz.get("devDependencies", {})} == _declarados()
    for nome, versao in _declarados().items():
        assert lock["packages"][f"node_modules/{nome}"]["version"] == versao, nome


def test_registro_gerado_fica_fora_do_git_e_root_nao_lista_composicoes():
    ignorados = (KIT / ".gitignore").read_text(encoding="utf-8").split()
    for padrao in ("node_modules/", "out/", "src/composicoes/registro.generated.ts"):
        assert padrao in ignorados, f"{padrao} faltando em motor/kit-remotion/.gitignore"
    root = (KIT / "src" / "Root.tsx").read_text(encoding="utf-8")
    assert "registro.generated" in root
    assert "Vazio" not in root, "o Root não pode citar composição: ela vem do registro gerado (D-46)"


# ---------------------------------------------------------------- integração


def _registrar(kit, node):
    return subprocess.run(
        [node, "scripts/registrar.mjs"], cwd=kit, capture_output=True, text=True, timeout=60
    )


@pytest.mark.integracao_local
def test_registrar_descobre_pastas_e_grava_atomicamente(tmp_path, requer_binario):
    node = requer_binario("node")
    kit = tmp_path / "kit"
    shutil.copytree(KIT / "scripts", kit / "scripts")
    shutil.copytree(KIT / "src", kit / "src", ignore=shutil.ignore_patterns("registro.generated.ts"))
    comps = kit / "src" / "composicoes"
    # pasta nova: basta criar a pasta, nada no Root
    (comps / "Outra").mkdir()
    (comps / "Outra" / "index.tsx").write_text(
        (comps / "Vazio" / "index.tsx").read_text(encoding="utf-8").replace('"Vazio"', '"Outra"'),
        encoding="utf-8",
    )
    # pasta sem index.tsx é ignorada
    (comps / "SemIndice").mkdir()
    (comps / "SemIndice" / "nota.txt").write_text("x", encoding="utf-8")

    r = _registrar(kit, node)
    assert r.returncode == 0, r.stderr
    gerado = (comps / "registro.generated.ts").read_text(encoding="utf-8")
    assert 'from "./Vazio"' in gerado and 'from "./Outra"' in gerado
    assert "SemIndice" not in gerado
    # ordem estável (alfabética) para o registro não mudar à toa
    assert gerado.index('"./Outra"') < gerado.index('"./Vazio"')
    # atômico: nenhum temporário sobra ao lado do registro
    sobras = [p.name for p in comps.iterdir() if p.is_file() and p.name != "registro.generated.ts"]
    assert sobras == [], sobras

    # rodar de novo sem mudança produz o mesmo conteúdo
    assert _registrar(kit, node).returncode == 0
    assert (comps / "registro.generated.ts").read_text(encoding="utf-8") == gerado


@pytest.mark.integracao_local
def test_remotion_compositions_lista_vazio(requer_binario):
    node = requer_binario("node")
    npx = requer_binario("npx")
    r = _registrar(KIT, node)
    assert r.returncode == 0, r.stderr
    assert 'from "./Vazio"' in REGISTRO.read_text(encoding="utf-8")

    r = subprocess.run(
        [npx, "--no-install", "remotion", "compositions", "src/index.ts", '--props={"duracaoFrames":45}'],
        cwd=KIT, capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    linha = next((l for l in r.stdout.splitlines() if l.split()[:1] == ["Vazio"]), None)
    assert linha is not None, r.stdout
    # id, fps, dimensão e duração vinda das props (45 != 90 padrão: prova o calculateMetadata)
    assert re.match(r"^Vazio\s+30\s+1080x1920\s+45\b", linha), linha

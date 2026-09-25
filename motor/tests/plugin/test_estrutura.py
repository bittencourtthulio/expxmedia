"""T-09.03: skills e comandos de Alma e ambiente, e a estrutura do plugin do núcleo (D-11, D-33).

- Todo `expxmedia-motor <subcomando>` citado numa skill ou comando do núcleo existe no CLI (--help).
- Todo SKILL.md tem frontmatter com `name` e `description`, e `name` é o nome da pasta.
- Os subcomandos que as skills de Alma e ambiente usam (cli_comandos/alma_ambiente.py) funcionam:
  extrair o site para a proposta, confirmar a proposta como Alma, gerar o .env.example, criar o .env
  sem sobrescrever e gravar uma chave vinda do stdin sem ecoar o valor.

As funções `comandos_citados` e `comandos_inexistentes` servem aos test_skill_* da F-09.2:

    from plugin.test_estrutura import comandos_inexistentes
    assert comandos_inexistentes(texto_da_skill) == []
"""
from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path

import pytest

from expxmedia import cli
from expxmedia.alma import carregar, schema
from stubs.servidor import servidor_stub  # noqa: F401  (fixture)
from test_marca import varrer

TESTES = Path(__file__).resolve().parents[1]
REPO = TESTES.parents[1]
NUCLEO = REPO / "nucleo"
SITE = TESTES / "fixtures" / "site-ficticio"

_RE_COMANDO = re.compile(r"expxmedia-motor((?:[ \t]+[a-z][a-z0-9-]*)+)")
_RE_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


# ---------------------------------------------------------------- utilitários (usados pela F-09.2)


def _subcomandos(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser] | None:
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return dict(acao.choices)
    return None


def comandos_citados(texto: str) -> list[tuple[str, ...]]:
    """Cada `expxmedia-motor a b ...` do texto, cortado onde o CLI deixa de ter subcomando.

    O que vem depois do último nível de subcomando é argumento ou prosa e fica de fora.
    """
    parser = cli.construir_parser()
    citados = []
    for m in _RE_COMANDO.finditer(texto):
        tokens = m.group(1).split()
        caminho: list[str] = []
        atual = parser
        for token in tokens:
            filhos = _subcomandos(atual)
            if filhos is None:
                break
            caminho.append(token)
            if token not in filhos:
                break
            atual = filhos[token]
        if caminho and tuple(caminho) not in citados:
            citados.append(tuple(caminho))
    return citados


def comandos_inexistentes(texto: str) -> list[str]:
    """Os comandos citados no texto que o CLI não conhece (vazio quando todos existem)."""
    parser = cli.construir_parser()
    faltam = []
    for caminho in comandos_citados(texto):
        atual = parser
        for token in caminho:
            filhos = _subcomandos(atual) or {}
            if token not in filhos:
                faltam.append(" ".join(caminho))
                break
            atual = filhos[token]
        else:
            if _subcomandos(atual) is not None:
                faltam.append(" ".join(caminho) + " (grupo sem subcomando)")
    return faltam


def frontmatter(texto: str) -> dict[str, str]:
    """Chaves de primeiro nível do frontmatter YAML simples (`chave: valor` e bloco `>`/`|`)."""
    m = _RE_FRONTMATTER.match(texto)
    if not m:
        return {}
    dados: dict[str, str] = {}
    chave = None
    for linha in m.group(1).splitlines():
        topo = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", linha)
        if topo:
            chave, valor = topo.group(1), topo.group(2).strip()
            dados[chave] = "" if valor in (">", "|", ">-", "|-") else valor.strip("\"'")
        elif chave and linha.startswith((" ", "\t")):
            dados[chave] = (dados[chave] + " " + linha.strip()).strip()
    return dados


def _arquivos_do_plugin() -> list[Path]:
    return sorted([*NUCLEO.glob("skills/*/*.md"), *NUCLEO.glob("commands/*.md"), *NUCLEO.glob("agents/*.md")])


def _rodar(capsys, *argv, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    codigo = cli.main(list(argv))
    saida = capsys.readouterr().out
    return codigo, json.loads(saida)


# ---------------------------------------------------------------- integração


def test_skills_de_alma_e_ambiente_existem_com_comandos():
    for nome in ("alma", "ambiente"):
        assert (NUCLEO / "skills" / nome / "SKILL.md").is_file()
        assert (NUCLEO / "commands" / f"{nome}.md").is_file()


def test_todo_comando_citado_existe_no_help_do_cli(capsys):
    citados_total = []
    for arquivo in _arquivos_do_plugin():
        texto = arquivo.read_text(encoding="utf-8")
        assert comandos_inexistentes(texto) == [], f"{arquivo.relative_to(REPO)} cita comando inexistente"
        citados_total += comandos_citados(texto)
    for caminho in sorted(set(citados_total)):
        codigo = cli.main([*caminho, "--help"])
        ajuda = capsys.readouterr().out
        assert codigo == 0 and "usage:" in ajuda, caminho
    # as skills do portão usam de fato o motor, nos subcomandos combinados
    esperados = {("alma", "validar"), ("alma", "extrair-site"), ("alma", "confirmar"), ("capacidades",),
                 ("ambiente", "exemplo"), ("ambiente", "criar-env"), ("ambiente", "gravar-chave")}
    assert esperados <= set(citados_total)


def test_verificador_de_comandos_aponta_o_inventado():
    texto = ("Rode `expxmedia-motor alma validar` e depois `expxmedia-motor alma inventar --x 1`.\n"
             "Em seguida expxmedia-motor capacidades e confira; por fim expxmedia-motor peca.")
    assert comandos_citados(texto) == [("alma", "validar"), ("alma", "inventar"), ("capacidades",), ("peca",)]
    assert comandos_inexistentes(texto) == ["alma inventar", "peca (grupo sem subcomando)"]


def test_plugin_sem_marca():
    achados = varrer([NUCLEO])
    assert not achados, achados


# ---------------------------------------------------------------- funcional


def test_frontmatter_de_toda_skill_tem_name_e_description_e_name_e_a_pasta():
    skills = sorted(NUCLEO.glob("skills/*/SKILL.md"))
    assert skills
    for skill in skills:
        dados = frontmatter(skill.read_text(encoding="utf-8"))
        assert dados.get("name") == skill.parent.name, skill
        assert len(dados.get("description", "")) >= 40, f"{skill}: description curta demais"


def test_comandos_tem_description_e_chamam_a_skill():
    for nome in ("alma", "ambiente"):
        texto = (NUCLEO / "commands" / f"{nome}.md").read_text(encoding="utf-8")
        assert frontmatter(texto).get("description"), nome
        assert f"skills/{nome}/SKILL.md" in texto or f"skill `{nome}`" in texto


def test_frontmatter_le_bloco_dobrado():
    texto = "---\nname: x\ndescription: >\n  primeira linha\n  segunda\n---\ncorpo\n"
    assert frontmatter(texto) == {"name": "x", "description": "primeira linha segunda"}
    assert frontmatter("sem frontmatter") == {}


def test_skill_alma_segue_o_contrato():
    texto = " ".join((NUCLEO / "skills" / "alma" / "SKILL.md").read_text(encoding="utf-8").split())
    for trecho in ("confirmo tudo", "pendências", "inferido", "entrevista", "uma pergunta por vez",
                   "nunca invente", "confirmada_em"):
        assert trecho.lower() in texto.lower(), trecho


def test_skill_ambiente_segue_o_contrato():
    texto = " ".join((NUCLEO / "skills" / "ambiente" / "SKILL.md").read_text(encoding="utf-8").split())
    for trecho in ("cole a chave no arquivo", "nunca na conversa", "girar a chave", "Onde conseguir",
                   "sem chave nenhuma"):
        assert trecho.lower() in texto.lower(), trecho


def test_cli_extrair_site_grava_proposta_e_logo(servidor_stub, tmp_path, capsys):
    for rota, arquivo in (("/", "index.html"), ("/sobre.html", "sobre.html"), ("/produtos.html", "produtos.html"),
                          ("/contato.html", "contato.html")):
        servidor_stub.rota("GET", rota, corpo=(SITE / arquivo).read_bytes(), cabecalhos={"Content-Type": "text/html"})
    servidor_stub.rota("GET", "/estilo.css", corpo=(SITE / "estilo.css").read_bytes(), cabecalhos={"Content-Type": "text/css"})
    servidor_stub.rota("GET", "/assets/logo.svg", corpo=(SITE / "assets" / "logo.svg").read_bytes(),
                       cabecalhos={"Content-Type": "image/svg+xml"})
    raiz = tmp_path / "nova"
    raiz.mkdir()

    codigo, dados = _rodar(capsys, "alma", "extrair-site", "--url", servidor_stub.url, "--raiz", str(raiz))

    assert codigo == 0, dados
    assert dados["proposta"] == "alma/proposta.json"
    proposta = json.loads((raiz / "alma" / "proposta.json").read_text(encoding="utf-8"))
    assert proposta["visual"]["cores"]["destaque"] == "#2F7D4F"
    assert (raiz / "alma" / "assets" / "logo.svg").is_file()
    assert "empresa.fuso" in dados["pendencias"]
    assert {p["papel"] for p in dados["paginas"]} == {"inicio", "sobre", "produtos", "contato"}
    assert not (raiz / "alma" / "alma.json").exists()  # nada vira Alma antes do "confirmo tudo"


def test_cli_extrair_site_fora_do_ar_sai_1(servidor_stub, tmp_path, capsys):
    codigo, dados = _rodar(capsys, "alma", "extrair-site", "--url", servidor_stub.url, "--raiz", str(tmp_path))
    assert codigo == cli.ERRO and dados["erro"] == "site_indisponivel"


def test_cli_confirmar_grava_a_alma_so_sem_violacao(instalacao, capsys):
    alma = json.loads((instalacao / "alma" / "alma.json").read_text(encoding="utf-8"))
    alma["confirmada_em"] = None
    alma["empresa"]["fuso"] = None
    proposta = instalacao / "alma" / "proposta.json"
    proposta.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")
    (instalacao / "alma" / "alma.json").unlink()

    codigo, dados = _rodar(capsys, "alma", "confirmar", "--raiz", str(instalacao))
    assert codigo == cli.ENTRADA_INVALIDA
    assert [v["caminho"] for v in dados["violacoes"]] == ["empresa.fuso"]
    assert not (instalacao / "alma" / "alma.json").exists()

    alma["empresa"]["fuso"] = "America/Sao_Paulo"
    proposta.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")
    codigo, dados = _rodar(capsys, "alma", "confirmar", "--raiz", str(instalacao))
    assert codigo == 0, dados
    gravada = json.loads((instalacao / "alma" / "alma.json").read_text(encoding="utf-8"))
    assert schema.validar(gravada) == []
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00$", gravada["confirmada_em"])
    assert gravada["atualizado_em"] == gravada["confirmada_em"]
    assert carregar.portao(instalacao)["aberto"] is True
    assert dados["portao"]["aberto"] is True
    assert not proposta.exists()  # a proposta confirmada vira a Alma


def test_cli_ambiente_exemplo_criar_env_e_gravar_chave(instalacao, capsys, monkeypatch):
    (instalacao / ".env").unlink()
    codigo, dados = _rodar(capsys, "ambiente", "exemplo", "--raiz", str(instalacao))
    assert codigo == 0 and dados["arquivo"] == ".env.example"
    exemplo = (instalacao / ".env.example").read_text(encoding="utf-8")
    assert "ELEVENLABS_API_KEY=" in exemplo and "Onde conseguir" in exemplo

    codigo, dados = _rodar(capsys, "ambiente", "criar-env", "--raiz", str(instalacao))
    assert codigo == 0 and dados["criado"] is True
    assert (instalacao / ".env").read_text(encoding="utf-8") == exemplo
    assert ".env" in (instalacao / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert carregar.portao(instalacao)["aberto"] is True

    segredo = "sk-teste-0123456789"
    codigo, dados = _rodar(capsys, "ambiente", "gravar-chave", "--nome", "ELEVENLABS_API_KEY", "--raiz",
                           str(instalacao), stdin=segredo + "\n", monkeypatch=monkeypatch)
    assert codigo == 0, dados
    assert segredo not in json.dumps(dados)
    assert "girar" in dados["aviso"]
    linhas = (instalacao / ".env").read_text(encoding="utf-8").splitlines()
    assert f"ELEVENLABS_API_KEY={segredo}" in linhas
    assert sum(1 for l in linhas if l.startswith("ELEVENLABS_API_KEY=")) == 1

    # criar-env nunca sobrescreve o .env que já existe
    codigo, dados = _rodar(capsys, "ambiente", "criar-env", "--raiz", str(instalacao))
    assert codigo == 0 and dados["criado"] is False
    assert f"ELEVENLABS_API_KEY={segredo}" in (instalacao / ".env").read_text(encoding="utf-8")
    # e a capacidade passa a constar como habilitada
    codigo, dados = _rodar(capsys, "capacidades", "--capacidade", "narrar", "--raiz", str(instalacao))
    assert dados["habilitada"] is True


def test_cli_gravar_chave_recusa_nome_fora_do_catalogo_e_valor_vazio(instalacao, capsys, monkeypatch):
    codigo, dados = _rodar(capsys, "ambiente", "gravar-chave", "--nome", "MINHA_CHAVE", "--raiz", str(instalacao),
                           stdin="x", monkeypatch=monkeypatch)
    assert codigo == cli.ENTRADA_INVALIDA and "MINHA_CHAVE" in dados["mensagem"]
    codigo, dados = _rodar(capsys, "ambiente", "gravar-chave", "--nome", "PEXELS_API_KEY", "--raiz", str(instalacao),
                           stdin="  \n", monkeypatch=monkeypatch)
    assert codigo == cli.ENTRADA_INVALIDA
    assert (instalacao / ".env").read_text(encoding="utf-8") == ""

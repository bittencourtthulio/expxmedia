"""T-02.14: CLI expxmedia-motor com registro por módulo e o módulo base (D-11)."""
import json
import os
import re
import secrets
import subprocess
from pathlib import Path

import pytest

from expxmedia import cli

MOTOR = Path(__file__).resolve().parents[1]
CLI_COMANDOS = MOTOR / "src" / "expxmedia" / "cli_comandos"


def _rodar_subprocesso(*argv, cwd=MOTOR):
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    return subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", *argv],
        cwd=cwd, capture_output=True, text=True, timeout=120, env=ambiente,
    )


def _rodar(capsys, *argv):
    codigo = cli.main(list(argv))
    saida = capsys.readouterr().out
    return codigo, json.loads(saida)


@pytest.fixture(autouse=True)
def _sem_provedores_teste(monkeypatch):
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)


# ---------------------------------------------------------------- integração


def test_capacidades_em_subprocesso_sai_0_com_json_valido(instalacao):
    feito = _rodar_subprocesso("capacidades", "--raiz", str(instalacao))
    assert feito.returncode == 0, feito.stderr
    dados = json.loads(feito.stdout)
    ids = [c["capacidade"] for c in dados["capacidades"]]
    assert "narrar" in ids and "renderizar_html" in ids
    narrar = next(c for c in dados["capacidades"] if c["capacidade"] == "narrar")
    assert narrar["habilitada"] is False and "ELEVENLABS_API_KEY" in narrar["como_habilitar"]


def test_modulo_novo_em_cli_comandos_aparece_no_help_sem_editar_cli(instalacao):
    nome = f"zz_teste_descoberta_{secrets.token_hex(3)}"
    comando = f"sonda-{secrets.token_hex(3)}"
    modulo = CLI_COMANDOS / f"{nome}.py"
    cli_antes = (MOTOR / "src" / "expxmedia" / "cli.py").read_bytes()
    modulo.write_text(
        "def registrar(subparsers):\n"
        f"    p = subparsers.add_parser({comando!r}, help='comando injetado pelo teste')\n"
        "    p.set_defaults(func=lambda args: {'sonda': True})\n",
        encoding="utf-8",
    )
    try:
        ajuda = _rodar_subprocesso("--help")
        assert ajuda.returncode == 0, ajuda.stderr
        assert comando in ajuda.stdout
        rodado = _rodar_subprocesso(comando, "--raiz", str(instalacao))
        assert rodado.returncode == 0, rodado.stderr
        assert json.loads(rodado.stdout)["sonda"] is True
    finally:
        modulo.unlink()
        for cache in (CLI_COMANDOS / "__pycache__").glob(f"{nome}.*"):
            cache.unlink()
    assert (MOTOR / "src" / "expxmedia" / "cli.py").read_bytes() == cli_antes
    assert comando not in _rodar_subprocesso("--help").stdout


def test_raiz_padrao_e_encontrada_a_partir_do_cwd(instalacao):
    subpasta = instalacao / "pecas"
    feito = _rodar_subprocesso("peca", "criar", "--tipo", "reel", "--formato", "9:16", "--titulo", "Pelo cwd",
                               cwd=subpasta)
    assert feito.returncode == 0, feito.stderr
    peca_id = json.loads(feito.stdout)["peca_id"]
    assert list((instalacao / "pecas").glob(f"*/{peca_id}-pelo-cwd/peca.json"))


# ---------------------------------------------------------------- funcional


def test_peca_criar_devolve_peca_id_do_contrato_e_cria_peca_json(capsys, instalacao):
    codigo, dados = _rodar(capsys, "peca", "criar", "--tipo", "post_unico", "--formato", "4:5",
                           "--raiz", str(instalacao))
    assert codigo == 0
    assert re.fullmatch(r"P-\d{8}-[0-9A-F]{4}", dados["peca_id"])
    achados = list((instalacao / "pecas").glob(f"*/{dados['peca_id']}-*/peca.json"))
    assert len(achados) == 1
    peca = json.loads(achados[0].read_text(encoding="utf-8"))
    assert peca["peca_id"] == dados["peca_id"] and peca["tipo"] == "post_unico" and peca["formatos"] == ["4:5"]
    assert dados["caminho"] == achados[0].relative_to(instalacao).as_posix()


def test_peca_criar_com_titulo_e_serie(capsys, instalacao):
    codigo, dados = _rodar(capsys, "--raiz", str(instalacao), "peca", "criar", "--tipo", "carrossel",
                           "--formato", "1:1", "--titulo", "Pão de fermentação natural", "--serie", "receitas")
    assert codigo == 0
    assert dados["peca"]["titulo"] == "Pão de fermentação natural" and dados["peca"]["serie"] == "receitas"
    assert dados["peca"]["slug"] == "pao-de-fermentacao-natural"


def test_entrada_invalida_sai_2_com_json(capsys, instalacao):
    codigo, dados = _rodar(capsys, "peca", "criar", "--tipo", "reel", "--formato", "4:5", "--raiz", str(instalacao))
    assert codigo == 2
    assert dados["ok"] is False and dados["erro"] == "entrada_invalida" and "4:5" in dados["mensagem"]
    # erro do argparse também sai em JSON, com código 2
    codigo, dados = _rodar(capsys, "peca", "criar", "--formato", "4:5", "--raiz", str(instalacao))
    assert codigo == 2 and dados["erro"] == "entrada_invalida" and "--tipo" in dados["mensagem"]


def test_peca_status_consulta_e_muda_e_transicao_invalida_sai_2(capsys, instalacao):
    _, criada = _rodar(capsys, "peca", "criar", "--tipo", "reel", "--formato", "9:16", "--raiz", str(instalacao))
    peca_id = criada["peca_id"]
    codigo, dados = _rodar(capsys, "peca", "status", peca_id, "--raiz", str(instalacao))
    assert codigo == 0 and dados["status"] == "ideia" and dados["permitidos"] == ["descartada", "roteiro"]
    codigo, dados = _rodar(capsys, "peca", "status", peca_id, "--novo", "roteiro", "--raiz", str(instalacao))
    assert codigo == 0 and dados["status"] == "roteiro" and dados["anterior"] == "ideia"
    codigo, dados = _rodar(capsys, "peca", "status", peca_id, "--novo", "publicada", "--raiz", str(instalacao))
    assert codigo == 2 and "roteiro -> publicada" in dados["mensagem"]


def test_capacidade_unica_e_desconhecida(capsys, instalacao):
    codigo, dados = _rodar(capsys, "capacidades", "--capacidade", "narrar", "--raiz", str(instalacao))
    assert codigo == 0 and dados["capacidade"] == "narrar" and dados["habilitada"] is False
    codigo, dados = _rodar(capsys, "capacidades", "--capacidade", "voar", "--raiz", str(instalacao))
    assert codigo == 2 and "voar" in dados["mensagem"]


def test_capacidade_nao_habilitada_sai_3_com_como_habilitar(capsys, instalacao):
    from expxmedia.ambiente.verificar import Verificador

    def falhar(args):
        Verificador(args.raiz).escolher_provedor("narrar")

    parser = cli.construir_parser()
    grupo = cli.grupo(parser._subparsers._group_actions[0], "teste3", help="x")
    grupo.add_parser("narrar").set_defaults(func=falhar)
    codigo = cli.executar(parser, ["teste3", "narrar", "--raiz", str(instalacao)])
    dados = json.loads(capsys.readouterr().out)
    assert codigo == 3
    assert dados["erro"] == "capacidade_nao_habilitada" and "ELEVENLABS_API_KEY" in dados["como_habilitar"]


def test_erro_generico_sai_1(capsys, instalacao):
    parser = cli.construir_parser()
    sub = parser._subparsers._group_actions[0].add_parser("quebra")
    sub.set_defaults(func=lambda args: 1 / 0)
    assert cli.executar(parser, ["quebra", "--raiz", str(instalacao)]) == 1
    assert json.loads(capsys.readouterr().out)["erro"] == "erro"


def test_grupo_e_compartilhado_entre_modulos():
    parser = cli.construir_parser()
    acao = parser._subparsers._group_actions[0]
    a = cli.grupo(acao, "produzir", help="produção")
    b = cli.grupo(acao, "produzir", help="produção")
    assert a is b
    a.add_parser("um")
    b.add_parser("dois")
    assert {"um", "dois"} <= set(a.choices)


def test_alma_validar(capsys, instalacao):
    codigo, dados = _rodar(capsys, "alma", "validar", "--raiz", str(instalacao))
    assert codigo == 0 and dados["valida"] is True and dados["violacoes"] == []
    alma_json = instalacao / "alma" / "alma.json"
    alma = json.loads(alma_json.read_text(encoding="utf-8"))
    del alma["visual"]["cores"]["destaque"]
    alma_json.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")
    codigo, dados = _rodar(capsys, "alma", "validar", "--raiz", str(instalacao))
    assert codigo == 2 and dados["valida"] is False
    assert any(v["caminho"] == "visual.cores.destaque" for v in dados["violacoes"])


def test_galeria_buscar(capsys, instalacao, tmp_path):
    codigo, dados = _rodar(capsys, "galeria", "buscar", "--tipo", "reel", "--formato", "9:16",
                           "--embarcados", str(tmp_path / "vazio"), "--raiz", str(instalacao))
    assert codigo == 0 and dados["templates"] == [] and dados["descartados"] == []
    pasta = instalacao / "galeria" / "templates" / "reel-incompleto-abcdef"
    pasta.mkdir(parents=True)
    (pasta / "template.json").write_text(json.dumps({
        "expxmedia_template": 1, "template_id": "reel-incompleto-abcdef", "tipo": "reel", "formato": "9:16",
    }), encoding="utf-8")
    codigo, dados = _rodar(capsys, "galeria", "buscar", "--tipo", "reel", "--formato", "9:16",
                           "--embarcados", str(tmp_path / "vazio"), "--raiz", str(instalacao))
    assert codigo == 0 and dados["templates"] == []
    assert [(d["template_id"], d["motivo"]) for d in dados["descartados"]] == [("reel-incompleto-abcdef", "invalido")]


def test_sem_raiz_encontrada_sai_2(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, dados = _rodar(capsys, "capacidades")
    assert codigo == 2 and dados["erro"] == "entrada_invalida"

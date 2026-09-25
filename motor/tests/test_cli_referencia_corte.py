"""T-06.09: CLI de referência e corte — referencia analisar/criar/montar/previa/render, produzir reel-corte e
produzir abertura (D-11).

- Integração: cada subcomando novo aparece no --help, e `referencia analisar` num vídeo sintético, em
  subprocesso, sai 0 e grava `analise/` (formato.json, folhas, quadros e o esqueleto da leitura).
- Funcional: `referencia montar` com um cenas.json de âncora ausente sai com código diferente de 0 citando a
  cena, sem montar nada; o mesmo em `previa` e `render`, sem chegar ao Remotion.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from expxmedia import cli
from expxmedia.nucleo import arquivos
from expxmedia.producao import abertura, reel_corte, reel_referencia
from expxmedia.referencia import analisar as mod_analisar

MOTOR = Path(__file__).resolve().parents[1]

ROTEIRO = ("Todo mundo acha que precisa de mais tempo. Na verdade falta um jeito de decidir. "
           "Primeiro você lista o que importa. Depois corta o resto sem dó. Salve para lembrar amanhã.")
TRILHA = {"bpm": 112, "acordes": [[98, [392, 493.88, 587.33]], [110, [440, 523.25, 659.25]]],
          "instrumentos": {"kick": 0.3, "palma": 0.08, "chimbal": 0.03, "pluck": 0.02, "pad": 0.03, "baixo": 0.2},
          "arpejo": [0, 1, 2, 1], "ganho": 0.55, "semente": 11}
CENAS = [
    {"id": "tempo", "ancora": "Todo mundo acha", "ev": {"relogio": 0.3}, "sons": [["relogio", "tick"]]},
    {"id": "decidir", "ancora": "Na verdade falta", "ev": {"balanca": 0.4}, "sons": [["balanca", "pop"]]},
    {"id": "lista", "ancora": "Primeiro você lista", "ev": {}, "sons": []},
    {"id": "fecho", "ancora": "Salve para lembrar", "ev": {"pede": 0.2}, "sons": []},
]


def _rodar(capsys, *argv):
    codigo = cli.main([str(a) for a in argv])
    return codigo, json.loads(capsys.readouterr().out)


def _escrever(pasta: Path, nome: str, dados) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / nome
    arquivo.write_text(dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return arquivo


def _video_sintetico(destino: Path) -> Path:
    """6 s mudos, 3 s vermelho e 3 s azul: um corte em 3 s e uma folha de contato."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=540x960:r=30:d=3",
           "-f", "lavfi", "-i", "color=c=blue:s=540x960:r=30:d=3",
           "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "6", str(destino)]
    subprocess.run(cmd, check=True, capture_output=True)
    return destino


def _criar_reel(capsys, raiz: Path, slug: str = "decidir-rapido", cenas=None) -> Path:
    codigo, dados = _rodar(capsys, "referencia", "criar", slug, "--titulo", "Decidir rápido",
                           "--origem-url", "https://exemplo.invalid/r/1", "--raiz", raiz)
    assert codigo == 0, dados
    pasta = raiz / dados["pasta"]
    (pasta / "roteiro.txt").write_text(ROTEIRO + "\n", encoding="utf-8")
    arquivos.gravar_json(pasta / "reel" / "cenas.json", {
        "trilha": json.loads(json.dumps(TRILHA)), "troca": [{"f": -3, "tipo": "whoosh", "desde": 1}],
        "legenda": {"palavras_por_bloco": 3}, "cauda_s": 1.4, "apresentador": False,
        "cenas": json.loads(json.dumps(cenas if cenas is not None else CENAS))})
    return pasta


def _proibir_render(monkeypatch):
    def proibido(*a, **k):
        raise AssertionError("não devia chegar ao Remotion")

    monkeypatch.setattr(reel_referencia.remotion, "renderizar", proibido)
    monkeypatch.setattr(reel_referencia.remotion, "stills", proibido)


# ---------------------------------------------------------------- integração


def test_subcomandos_novos_aparecem_no_help(capsys):
    for argv, esperados in ((["referencia", "--help"], ("analisar", "criar", "montar", "previa", "render")),
                            (["produzir", "--help"], ("reel-corte", "abertura")),
                            (["referencia", "analisar", "--help"], ("--video", "--pasta", "--sem-fala", "--idioma")),
                            (["referencia", "criar", "--help"], ("slug", "--titulo", "--origem-url")),
                            (["referencia", "montar", "--help"], ("--pasta",)),
                            (["referencia", "previa", "--help"], ("--pasta", "--porta-voz", "--canal")),
                            (["referencia", "render", "--help"], ("--pasta", "--porta-voz", "--canal")),
                            (["produzir", "reel-corte", "--help"], ("--entrada",)),
                            (["produzir", "abertura", "--help"], ("--pasta", "--prompt", "--tipo", "--dispensar"))):
        codigo = cli.main(argv)
        saida = capsys.readouterr().out
        assert codigo == 0 and all(e in saida for e in esperados), (argv, saida)
    codigo = cli.main(["--help"])
    assert codigo == 0 and "referencia" in capsys.readouterr().out


@pytest.mark.integracao_local
def test_referencia_analisar_em_subprocesso_sai_0_e_grava_analise(instalacao, tmp_path, requer_binario):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    video = _video_sintetico(tmp_path / "ref.mp4")
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "referencia", "analisar",
         "--video", str(video), "--pasta", "meu-reel", "--raiz", str(instalacao)],
        cwd=MOTOR, capture_output=True, text=True, timeout=300, env=ambiente,
    )
    assert feito.returncode == 0, feito.stdout + feito.stderr
    dados = json.loads(feito.stdout)
    analise = instalacao / "referencias" / "meu-reel" / "analise"
    assert dados["ok"] is True and dados["analise"] == "referencias/meu-reel/analise"
    assert dados["formato"] == "referencias/meu-reel/analise/formato.json"
    assert dados["leitura"] == "referencias/meu-reel/analise/leitura.md"
    formato = arquivos.ler_json(analise / "formato.json")
    assert formato["duracao"] == pytest.approx(6.0, abs=0.1) and formato["origem"] == "ref.mp4"
    assert (formato["largura"], formato["altura"]) == (540, 960)
    assert formato["cortes"] and formato["cortes"][0] == pytest.approx(3.0, abs=0.1)
    assert formato["fala"] is None  # vídeo mudo
    assert dados["duracao"] == formato["duracao"] and dados["cenas"] == formato["cenas"] == 2
    assert dados["folhas"] == ["referencias/meu-reel/analise/folhas/folha_00.jpg"]
    assert (analise / "folhas" / "folha_00.jpg").is_file() and (analise / "leitura.md").is_file()
    assert dados["quadros"] == len(formato["quadros"]) > 0
    assert all((analise / q["arquivo"]).is_file() for q in formato["quadros"])
    assert not any(Path(v).is_absolute() for v in (dados["analise"], dados["formato"], dados["leitura"]))


def test_referencia_analisar_video_ausente_e_falha_da_analise(instalacao, tmp_path, capsys, monkeypatch):
    codigo, dados = _rodar(capsys, "referencia", "analisar", "--video", tmp_path / "nao.mp4", "--pasta", "x-y",
                           "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "campo 'video'" in dados["mensagem"]
    assert not (instalacao / "referencias").exists()

    video = _escrever(tmp_path, "ref.mp4", "não é vídeo")
    pedidos = {}

    def analisar_falso(v, pasta, **kw):
        pedidos.update(video=v, pasta=pasta, kw=kw)
        raise mod_analisar.ErroAnalise("ffprobe falhou")

    monkeypatch.setattr(mod_analisar, "analisar", analisar_falso)
    codigo, dados = _rodar(capsys, "referencia", "analisar", "--video", video, "--pasta", "referencias/meu-reel",
                           "--sem-fala", "--idioma", "pt", "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "analise" and "ffprobe falhou" in dados["mensagem"]
    assert pedidos["pasta"] == instalacao / "referencias" / "meu-reel"
    assert pedidos["kw"]["com_fala"] is False and pedidos["kw"]["idioma"] == "pt"


# ---------------------------------------------------------------- funcional


def test_referencia_montar_com_ancora_ausente_sai_nao_zero_citando_a_cena(instalacao, capsys, monkeypatch):
    cenas = json.loads(json.dumps(CENAS))
    cenas[1]["ancora"] = "Nenhuma palavra daqui"
    pasta = _criar_reel(capsys, instalacao, cenas=cenas)
    _proibir_render(monkeypatch)
    for sub in ("montar", "previa", "render"):
        codigo, dados = _rodar(capsys, "referencia", sub, "--pasta", "decidir-rapido", "--raiz", instalacao)
        assert codigo != 0 and codigo == cli.ENTRADA_INVALIDA, (sub, dados)
        assert dados["ok"] is False and dados["erro"] == "cenas_recusado"
        assert dados["erros"] == ['cena 2 (decidir): âncora "Nenhuma palavra daqui" não casou com o roteiro, em ordem']
        assert "cena 2 (decidir)" in dados["mensagem"]
    assert not (pasta / "midia" / "timeline.json").exists() and not (pasta / "previa").exists()
    assert list((instalacao / "pecas").rglob("peca.json")) == []


def test_referencia_montar_sem_narracao_e_codigo_recusado(instalacao, capsys, monkeypatch):
    pasta = _criar_reel(capsys, instalacao)
    _proibir_render(monkeypatch)
    # cenas aprovadas, mas sem narração: diz a etapa que falta (saída 1)
    codigo, dados = _rodar(capsys, "referencia", "montar", "--pasta", "referencias/decidir-rapido", "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "referencia" and "narração" in dados["mensagem"]

    reel_tsx = pasta / "reel" / "src" / "Reel.tsx"
    reel_tsx.write_text('import { execSync } from "child_process";\n' + reel_tsx.read_text(encoding="utf-8"),
                        encoding="utf-8")
    codigo, dados = _rodar(capsys, "referencia", "montar", "--pasta", "decidir-rapido", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and dados["erro"] == "codigo_recusado"
    assert {"tipo": "import_proibido", "arquivo": "src/Reel.tsx", "linha": 1,
            "detalhe": "módulo proibido: child_process"} in dados["achados"]


def test_referencia_montar_previa_render_devolvem_caminhos_relativos(instalacao, capsys, monkeypatch):
    _criar_reel(capsys, instalacao)
    pasta_abs = instalacao / "referencias" / "decidir-rapido"
    monkeypatch.setattr(reel_referencia, "montar", lambda raiz, pasta: (
        pedidos.append(("montar", Path(pasta))) or
        {"fps": 30, "totalFrames": 300, "cenas": [{}, {}, {}, {}], "_avisos": ["aviso: x"]}))
    monkeypatch.setattr(reel_referencia, "previa", lambda raiz, pasta, **kw: (
        pedidos.append(("previa", Path(pasta), kw)) or {"folha": "referencias/decidir-rapido/previa/01/previa.jpg",
                                                       "imagens": [], "quadros": [], "volta": 1, "avisos": []}))
    monkeypatch.setattr(reel_referencia, "renderizar", lambda raiz, pasta, **kw: (
        pedidos.append(("render", Path(pasta), kw)) or {"peca_id": "p", "video": "pecas/p/saida/final.mp4"}))
    pedidos: list = []
    codigo, dados = _rodar(capsys, "referencia", "montar", "--pasta", "decidir-rapido", "--raiz", instalacao)
    assert codigo == 0 and dados == {"ok": True, "pasta": "referencias/decidir-rapido",
                                     "timeline": "referencias/decidir-rapido/midia/timeline.json",
                                     "trilha": "referencias/decidir-rapido/midia/trilha.wav",
                                     "cenas": 4, "quadros": 300, "avisos": ["aviso: x"]}
    codigo, dados = _rodar(capsys, "referencia", "previa", "--pasta", "decidir-rapido", "--porta-voz", "ana",
                           "--canal", "@c", "--raiz", instalacao)
    assert codigo == 0 and dados["volta"] == 1
    codigo, dados = _rodar(capsys, "referencia", "render", "--pasta", "decidir-rapido", "--raiz", instalacao)
    assert codigo == 0 and dados["peca_id"] == "p"
    assert [p[:2] for p in pedidos] == [("montar", pasta_abs), ("previa", pasta_abs), ("render", pasta_abs)]
    assert pedidos[1][2] == {"porta_voz": "ana", "canal": "@c"}
    assert pedidos[2][2] == {"porta_voz": None, "canal": None, "origem": "skill"}


def test_referencia_criar_duplicado_slug_invalido_e_pasta_fora(instalacao, capsys):
    _criar_reel(capsys, instalacao)
    marcador = arquivos.ler_json(instalacao / "referencias" / "decidir-rapido" / "referencia.json")
    assert marcador["titulo"] == "Decidir rápido" and marcador["origem_url"] == "https://exemplo.invalid/r/1"
    codigo, dados = _rodar(capsys, "referencia", "criar", "decidir-rapido", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "já existe" in dados["mensagem"]
    codigo, dados = _rodar(capsys, "referencia", "criar", "Slug Ruim", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "slug inválido" in dados["mensagem"]
    codigo, dados = _rodar(capsys, "referencia", "montar", "--pasta", "nao-existe", "--raiz", instalacao)
    assert codigo == cli.ERRO and "não é um reel sob medida" in dados["mensagem"]
    codigo, dados = _rodar(capsys, "referencia", "montar", "--pasta", "/fora/da/raiz", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA


def test_produzir_reel_corte_entrada_invalida_sai_2_citando_o_campo(instalacao, tmp_path, capsys):
    (instalacao / "fontes").mkdir(exist_ok=True)
    (instalacao / "fontes" / "aula.mp4").write_bytes(b"x")
    base = {"video": "fontes/aula.mp4", "titulo": "Corte", "gancho": ["UMA", "DUAS", "TRÊS", "QUATRO"]}
    for conteudo, trecho in ((base, "campo 'gancho'"), ({**base, "gancho": ["A"], "video": "fontes/nao.mp4"},
                                                          "campo 'video'"),
                             ({**base, "gancho": ["A"], "cor": "#fff"}, "campo 'cor'"),
                             ("{ruim", "campo 'entrada': JSON inválido")):
        entrada = _escrever(tmp_path / "entrada", "corte.json", conteudo)
        codigo, dados = _rodar(capsys, "produzir", "reel-corte", "--entrada", entrada, "--raiz", instalacao)
        assert codigo == cli.ENTRADA_INVALIDA and trecho in dados["mensagem"], dados
    assert list((instalacao / "pecas").rglob("peca.json")) == []


def test_produzir_reel_corte_repassa_e_traduz_a_verificacao(instalacao, tmp_path, capsys, monkeypatch):
    pedidos = []

    def produzir_falso(raiz, dados, **kw):
        pedidos.append((raiz, dados, kw))
        if dados.get("titulo") == "reprova":
            raise reel_corte.ErroVerificacaoReprovada("p1", "verificação reprovada no perfil corte: curto",
                                                      [{"checagem": "duracao", "detalhe": "curto"}])
        if dados.get("titulo") == "quebra":
            raise reel_corte.ErroProducaoCorte("cortar: ffmpeg falhou")
        return {"peca_id": "p0", "video": "pecas/p0/saida/final.mp4"}

    monkeypatch.setattr(reel_corte, "produzir", produzir_falso)
    entrada = _escrever(tmp_path / "entrada", "corte.json", {"video": "fontes/a.mp4", "titulo": "ok", "gancho": ["A"]})
    codigo, dados = _rodar(capsys, "produzir", "reel-corte", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == 0 and dados == {"ok": True, "peca_id": "p0", "video": "pecas/p0/saida/final.mp4"}
    assert pedidos[0][0] == instalacao and pedidos[0][1]["titulo"] == "ok" and pedidos[0][2] == {"origem": "skill"}

    _escrever(tmp_path / "entrada", "corte.json", {"titulo": "reprova"})
    codigo, dados = _rodar(capsys, "produzir", "reel-corte", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "verificacao_reprovada" and dados["peca_id"] == "p1"
    assert dados["achados"] == [{"checagem": "duracao", "detalhe": "curto"}]

    _escrever(tmp_path / "entrada", "corte.json", {"titulo": "quebra"})
    codigo, dados = _rodar(capsys, "produzir", "reel-corte", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "producao" and "ffmpeg falhou" in dados["mensagem"]


def test_produzir_abertura_gera_dispensa_e_recusa(instalacao, capsys, monkeypatch):
    pasta = instalacao / "pecas" / "x" / "midia"
    pasta.mkdir(parents=True)
    pedidos = []

    def gerar_falso(raiz, p, **kw):
        pedidos.append((raiz, Path(p), kw))
        if kw["prompt"] == "caro":
            raise abertura.ErroAbertura("o teto de 80 créditos/dia de abertura já foi gasto")
        return {"metodo": "abertura-gerada", "duracao": 2.5, "rosto": None, "montado_em": None, "avisos": []}

    monkeypatch.setattr(abertura, "gerar", gerar_falso)
    codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/x/midia", "--prompt", "bread rising",
                           "--estilo", "warm light", "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados["abertura"] == "pecas/x/midia/abertura.mp4" and dados["marcador"] == "pecas/x/midia/abertura.json"
    assert dados["duracao"] == 2.5 and dados["montado_em"] is None
    raiz, p, kw = pedidos[0]
    assert (raiz, p) == (instalacao, pasta)
    assert kw == {"prompt": "bread rising", "tipo": "objeto", "porta_voz": None, "duracao": abertura.DURACAO_NA_TELA,
                  "estilo": "warm light", "transformar_no_conteudo": True, "pedido_por": "skill"}

    codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/x/midia", "--prompt", "caro",
                           "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "abertura" and "80 créditos" in dados["mensagem"]

    # entrada inválida do próprio módulo (sem o gerar falso): tipo desconhecido e porta_voz sem id
    monkeypatch.undo()
    for extra, trecho in ((["--tipo", "robo"], "tipo de abertura desconhecido"),
                          (["--tipo", "porta_voz"], "id do porta-voz")):
        codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/x/midia", "--prompt", "p", *extra,
                               "--raiz", instalacao)
        assert codigo == cli.ENTRADA_INVALIDA and trecho in dados["mensagem"], dados
    codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/x/midia", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "--prompt" in dados["mensagem"]
    codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/nao", "--prompt", "p", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "campo 'pasta'" in dados["mensagem"]

    (pasta / "abertura.mp4").write_bytes(b"x")
    (pasta / "abertura.json").write_text("{}", encoding="utf-8")
    codigo, dados = _rodar(capsys, "produzir", "abertura", "--pasta", "pecas/x/midia", "--dispensar", "--raiz", instalacao)
    assert codigo == 0 and dados == {"ok": True, "pasta": "pecas/x/midia", "dispensada": True}
    assert not (pasta / "abertura.mp4").exists() and not (pasta / "abertura.json").exists()

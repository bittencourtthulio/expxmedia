"""T-06.03: montar, prévia, render e verificação do reel sob medida (D-18, D-19, D-36).

Integração: com um reel sob medida de exemplo (cenas desenhadas com a paleta literal da "referência",
leitura escrita, roteiro de 155 palavras) e o provedor de teste, o encadeamento — validador de código,
cenas.json, narração uma vez, montagem, prévia com as guias, render, normalização da mistura e verificação
no perfil sob_medida — gera o MP4 aprovado e a peça `produzida`.

Funcional: um `Reel.tsx` que importa `child_process` é recusado antes do render (e antes de narrar) com o
achado do validador; cenas.json recusado e roteiro fora de 130-180 palavras também param antes de narrar; a
prévia tem no máximo três voltas.
"""
from __future__ import annotations

import json

import pytest
from PIL import Image

from expxmedia.motion import remotion
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.producao import reel_referencia
from expxmedia.referencia import sob_medida
from expxmedia.video import ffmpeg, verificar
from fixtures.fontes_ficticias import semear_cache

PARAGRAFOS = [
    "Toda semana a sua lista de tarefas cresce mais rápido do que você consegue resolver. "
    "Cada pedido novo parece urgente, cada mensagem parece importante, e no fim do dia sobra a sensação "
    "de que nada andou de verdade.",
    "O problema quase nunca é falta de esforço. Falta um critério simples para pesar o que entra. "
    "Quando tudo tem o mesmo peso, a decisão vira sorteio e o que é importante perde para o que "
    "grita mais alto.",
    "Então corte sem medo. Tire da lista o que não muda nada em um mês. Passe adiante o que outra "
    "pessoa resolve melhor. O que sobrar é pouco, e esse pouco merece a sua melhor hora do dia.",
    "Faça isso toda segunda de manhã, antes de abrir qualquer mensagem. Em poucas semanas a lista "
    "encolhe e o trabalho que importa volta a andar. Salve este vídeo para lembrar na próxima segunda "
    "e siga para ver mais ideias simples.",
]
ROTEIRO = " ".join(PARAGRAFOS)

CENAS_JSON = {
    "trilha": {"bpm": 104, "acordes": [[98, [392, 493.88, 587.33]], [87.31, [349.23, 440, 523.25]],
                                        [110, [440, 523.25, 659.25]], [130.81, [523.25, 659.25, 783.99]]],
               "instrumentos": {"kick": 0.3, "palma": 0.07, "chimbal": 0.03, "sino": 0.018, "pad": 0.03, "baixo": 0.18},
               "arpejo": [0, 2, 1, 2, 0, 2, 1, 2], "ganho": 0.55, "semente": 13},
    "troca": [{"f": -3, "tipo": "whoosh", "desde": 1, "vol": 0.6}, {"f": 5, "tipo": "pop", "desde": 0, "vol": 0.4}],
    "legenda": {"palavras_por_bloco": 3},
    "cauda_s": 1.4,
    "apresentador": False,
    "cenas": [
        {"id": "pilha", "ancora": "Toda semana a sua", "ev": {"cai": 0.15, "transborda": 0.6},
         "sons": [["cai", "pagina"], ["transborda", "impacto", 0.1, 0.7]]},
        {"id": "balanca", "ancora": "O problema quase nunca", "ev": {"entra": 0.1, "pesa": 0.5},
         "sons": [["entra", "clack"], ["pesa", "descida", 0.2]]},
        {"id": "corte", "ancora": "Então corte sem medo", "ev": {"tesoura": 0.25, "sobra": 0.7},
         "sons": [["tesoura", "snip"], ["sobra", "check"]]},
        {"id": "fecho", "ancora": "Faça isso toda segunda", "ev": {"selo": 0.3},
         "sons": [["selo", "carimbo"]]},
    ],
}

# Paleta literal da "referência" (D-36): o sob medida pode usar a cor da referência, o validador deixa.
AREIA = (0xE9, 0xD8, 0xB4)
CENAS_TSX = """import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { clamp, mola, pilhaFonte, useAlma } from "@expxmedia/template";

export type CenaT = { id: string; ev: Record<string, number>; inicio: number; dur: number; [campo: string]: unknown };
export type PropsCena = { f: number; d: number; ev: (nome: string) => number; cena: CenaT };

const P = { areia: "#E9D8B4", tinta: "#1F2A36", coral: "#E86A4F", menta: "#5FB49C", papel: "#FFF8EC" };

const Pilha: React.FC<PropsCena> = ({ f, ev }) => {
  const cai = ev("cai");
  const transborda = ev("transborda");
  return (
    <AbsoluteFill>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920}>
        {[0, 1, 2, 3, 4].map((i) => {
          const s = mola(f, cai + i * 6);
          return <rect key={i} x={340} y={900 - i * 110 - (1 - s) * 400} width={400} height={90} rx={14}
            fill={i % 2 ? P.coral : P.tinta} opacity={s} />;
        })}
        <circle cx={760} cy={420} r={60 * mola(f, transborda)} fill={P.coral} />
      </svg>
    </AbsoluteFill>
  );
};

const Balanca: React.FC<PropsCena> = ({ f, ev }) => {
  const giro = interpolate(f, [ev("pesa"), ev("pesa") + 20], [0, -14], clamp);
  return (
    <AbsoluteFill>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920}>
        <rect x={530} y={420} width={20} height={520} fill={P.tinta} />
        <g transform={`rotate(${giro} 540 430)`} opacity={mola(f, ev("entra"))}>
          <rect x={290} y={410} width={500} height={24} rx={12} fill={P.tinta} />
          <circle cx={320} cy={520} r={80} fill={P.papel} />
          <circle cx={760} cy={520} r={80} fill={P.coral} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

const Corte: React.FC<PropsCena> = ({ f, ev }) => {
  const x = interpolate(f, [ev("tesoura"), ev("tesoura") + 18], [300, 800], clamp);
  return (
    <AbsoluteFill>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920}>
        {[0, 1, 2].map((i) => (
          <rect key={i} x={320} y={460 + i * 150} width={440} height={100} rx={16} fill={P.papel}
            opacity={i === 2 ? 1 : 1 - mola(f, ev("sobra"))} />
        ))}
        <line x1={300} y1={620} x2={x} y2={620} stroke={P.coral} strokeWidth={10} strokeDasharray="30 18" />
      </svg>
    </AbsoluteFill>
  );
};

const Fecho: React.FC<PropsCena> = ({ f, ev }) => {
  const { fontes } = useAlma();
  const s = mola(f, ev("selo"));
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 480 }}>
      <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 96, color: P.papel,
        transform: `scale(${s})` }}>SEGUNDA</div>
    </AbsoluteFill>
  );
};

export const CENAS: Record<string, React.FC<PropsCena>> = { pilha: Pilha, balanca: Balanca, corte: Corte, fecho: Fecho };
export const FUNDOS: Record<string, string> = { pilha: P.areia, balanca: P.menta, corte: P.areia, fecho: P.coral };
"""

LEITURA = "# Leitura da referência\n\n" + "\n".join(
    f"## {n}. {t}\n\nTexto da seção {n}.\n" for n, t in enumerate(
        ("Ideia em uma frase", "Tela fixa", "Legenda", "Personagem ou elemento-guia", "Cena a cena", "Ritmo", "Som",
         "Fecho", "O que não vai"), 1))


def _contar_narrar(monkeypatch) -> list:
    chamadas = []
    original = narrar_base.narrar

    def contado(*a, **k):
        chamadas.append(a)
        return original(*a, **k)

    monkeypatch.setattr(reel_referencia.narrar_base, "narrar", contado)
    return chamadas


def _exemplo(raiz, slug="exemplo-ref"):
    r = sob_medida.criar(raiz, slug, titulo="Lista que encolhe", origem_url="https://exemplo.invalid/r/2")
    pasta = raiz / r["pasta"]
    (pasta / "analise").mkdir(exist_ok=True)
    (pasta / "analise" / "leitura.md").write_text(LEITURA, encoding="utf-8")
    (pasta / "roteiro.txt").write_text(ROTEIRO + "\n", encoding="utf-8")
    (pasta / "legenda.txt").write_text("Uma lista que encolhe toda segunda.\n#produtividade\n", encoding="utf-8")
    arquivos.gravar_json(pasta / "reel" / "cenas.json", CENAS_JSON)
    (pasta / "reel" / "src" / "cenas.tsx").write_text(CENAS_TSX, encoding="utf-8")
    return pasta


@pytest.fixture
def ambiente(instalacao, tmp_path, monkeypatch):
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    return instalacao, semear_cache(tmp_path / "fontes")


def _eventos(raiz):
    eventos, corrompidas = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert corrompidas == 0
    return eventos


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_encadeamento_gera_mp4_aprovado_no_perfil_sob_medida(ambiente, monkeypatch, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    raiz, cache = ambiente
    assert len(ROTEIRO.split()) == 155
    pasta = _exemplo(raiz)
    chamadas = _contar_narrar(monkeypatch)

    r = reel_referencia.produzir(raiz, pasta, cache_fontes=cache, opcoes_narrar={"palavras_por_segundo": 3.5})

    assert len(chamadas) == 1  # narra uma vez
    assert r["status"] == "produzida"
    assert r["verificacao"] == {"aprovado": True, "perfil": "sob_medida", "achados": [], "avisos": []}
    assert 30.0 <= r["duracao"] <= 70.0
    assert r["codigo"] == []  # o validador no modo sob_medida não achou nada nas cores literais

    # montagem: linha do tempo pelas âncoras, trilha sintetizada, na pasta do reel
    midia = pasta / "midia"
    timeline = arquivos.ler_json(midia / "timeline.json")
    assert [c["id"] for c in timeline["cenas"]] == ["pilha", "balanca", "corte", "fecho"]
    fim_fala = max(arquivos.ler_json(midia / "alinhamento.json")["character_end_times_seconds"])
    assert timeline["totalFrames"] == round((fim_fala + 1.4) * 30)
    assert (midia / "trilha.wav").stat().st_size > 1000

    # prévia com guias: um quadro de cada cena a 60%, linhas vermelhas em 220 e 1500, com a paleta literal
    previa = pasta / "previa" / "01"
    assert (previa / "previa.jpg").is_file() and r["previa"] == "referencias/exemplo-ref/previa/01/previa.jpg"
    pngs = sorted(previa.glob("previa-*.png"))
    assert [p.name for p in pngs] == ["previa-01-pilha.png", "previa-02-balanca.png", "previa-03-corte.png",
                                      "previa-04-fecho.png"]
    im = Image.open(pngs[0]).convert("RGB")
    assert im.getpixel((5, round(220 * 0.3))) == (255, 0, 0) and im.getpixel((5, round(1500 * 0.3))) == (255, 0, 0)
    px = im.getpixel((30, 270))
    assert all(abs(a - b) <= 12 for a, b in zip(px, AREIA)), px
    # o selo de quem publica, na cor de fundo da Alma fictícia (#FFF8EE), embaixo do conteúdo (y ~1360-1460)
    fundo_alma = (0xFF, 0xF8, 0xEE)
    faixa_selo = [im.getpixel((x, y)) for y in range(400, 440) for x in range(20, 300)]
    assert any(all(abs(a - b) <= 6 for a, b in zip(p, fundo_alma)) for p in faixa_selo)
    faixa_topo = [im.getpixel((x, y)) for y in range(100, 140) for x in range(20, 300)]
    assert not any(all(abs(a - b) <= 6 for a, b in zip(p, fundo_alma)) for p in faixa_topo)

    # peça produzida com o MP4 normalizado e aprovado de novo no perfil sob_medida
    peca = modelo.carregar(raiz, r["peca_id"])
    assert peca["status"] == "produzida" and peca["tipo"] == "reel" and peca["formatos"] == ["9:16"]
    assert arquivos.ler_json(pasta / "referencia.json")["peca_id"] == r["peca_id"]
    base = modelo.pasta(raiz, r["peca_id"])
    final = base / "saida" / "final.mp4"
    assert r["video"] == relativo(raiz, final) and r["pasta"] == relativo(raiz, base)
    s = ffmpeg.sondar(final)
    assert (s["largura"], s["altura"], s["fps"]) == (1080, 1920, "30/1")
    lufs, pico = ffmpeg.medir(final)
    assert abs(lufs + 14) <= 1 and pico <= -1.0
    refeita = verificar.verificar(final, "sob_medida", verificar.Artefatos(
        alinhamento=base / "midia" / "alinhamento.json", roteiro=base / "texto" / "roteiro.txt",
        legenda_post=base / "texto" / "legenda.txt"))
    assert refeita["aprovado"], refeita["achados"]
    papeis = {a["caminho"]: a["papel"] for a in peca["arquivos"]}
    assert papeis == {"saida/final.mp4": "final", "texto/roteiro.txt": "roteiro", "texto/legenda.txt": "legenda",
                      "midia/narracao.mp3": "audio", "midia/alinhamento.json": "alinhamento",
                      "previa/previa.jpg": "previa"}
    assert peca["conteudo"]["roteiro"] == "texto/roteiro.txt" and peca["conteudo"]["legenda"] == "texto/legenda.txt"
    assert peca["producao"]["provedores"] == {"narrar": "teste", "renderizar_motion": "remotion", "editar_video": "ffmpeg"}
    # a trilha fica registrada na peça: um reel de template não a repete, e este reel não conta como outro
    assert arquivos.ler_json(base / "midia" / "cenas.json")["trilha"] == CENAS_JSON["trilha"]
    assert sob_medida.validar_cenas(raiz, pasta) == []
    tipos = [ev["evento"] for ev in _eventos(raiz) if ev.get("peca_id") == r["peca_id"]]
    assert "geracao_concluida" in tipos and "geracao_falhou" not in tipos

    # a narração já existe: nenhuma chamada nova ao provedor
    assert reel_referencia.narrar(raiz, pasta) is None and len(chamadas) == 1


# ------------------------------------------------------------------ funcional


def _proibir_render(monkeypatch):
    def proibido(*a, **k):
        raise AssertionError("não devia chegar ao Remotion")

    monkeypatch.setattr(reel_referencia.remotion, "renderizar", proibido)
    monkeypatch.setattr(reel_referencia.remotion, "stills", proibido)


def test_reel_que_importa_child_process_e_recusado_antes_do_render(ambiente, monkeypatch):
    raiz, cache = ambiente
    pasta = _exemplo(raiz)
    reel_tsx = pasta / "reel" / "src" / "Reel.tsx"
    reel_tsx.write_text('import { execSync } from "child_process";\n' + reel_tsx.read_text(encoding="utf-8")
                        + '\nexport const x = () => execSync("ls");\n', encoding="utf-8")
    chamadas = _contar_narrar(monkeypatch)
    _proibir_render(monkeypatch)

    for etapa in (reel_referencia.produzir, reel_referencia.montar, reel_referencia.previa, reel_referencia.renderizar):
        with pytest.raises(reel_referencia.ErroCodigoRecusado) as erro:
            etapa(raiz, pasta, cache_fontes=cache) if etapa is not reel_referencia.montar else etapa(raiz, pasta)
        assert {"tipo": "import_proibido", "arquivo": "src/Reel.tsx", "linha": 1,
                "detalhe": "módulo proibido: child_process"} in erro.value.achados
        assert "child_process" in str(erro.value)
    assert chamadas == []
    assert not (pasta / "midia" / "narracao.mp3").exists() and not (pasta / "midia" / "timeline.json").exists()
    assert list((raiz / "pecas").rglob("peca.json")) == []
    assert arquivos.ler_json(pasta / "referencia.json")["peca_id"] is None


def test_cenas_recusado_e_roteiro_fora_da_faixa_param_antes_de_narrar(ambiente, monkeypatch):
    raiz, cache = ambiente
    pasta = _exemplo(raiz)
    chamadas = _contar_narrar(monkeypatch)
    _proibir_render(monkeypatch)

    cenas = json.loads(json.dumps(CENAS_JSON))
    cenas["cenas"][2]["sons"][0][0] = "martelo"
    arquivos.gravar_json(pasta / "reel" / "cenas.json", cenas)
    with pytest.raises(sob_medida.ErroSobMedida, match='cena 3 \\(corte\\): som cita o evento "martelo"'):
        reel_referencia.produzir(raiz, pasta, cache_fontes=cache)

    arquivos.gravar_json(pasta / "reel" / "cenas.json", CENAS_JSON)
    (pasta / "roteiro.txt").write_text(" ".join(PARAGRAFOS[:3]) + "\n", encoding="utf-8")
    cenas_curtas = {**CENAS_JSON, "cenas": CENAS_JSON["cenas"][:3]}
    arquivos.gravar_json(pasta / "reel" / "cenas.json", cenas_curtas)
    with pytest.raises(reel_referencia.ErroReferencia, match="fora de 130-180"):
        reel_referencia.produzir(raiz, pasta, cache_fontes=cache)
    assert chamadas == []

    # montar sem narração: diz qual etapa falta
    arquivos.gravar_json(pasta / "reel" / "cenas.json", CENAS_JSON)
    (pasta / "roteiro.txt").write_text(ROTEIRO + "\n", encoding="utf-8")
    with pytest.raises(reel_referencia.ErroReferencia, match="narração"):
        reel_referencia.montar(raiz, pasta)


def test_previa_tem_no_maximo_tres_voltas(ambiente, monkeypatch):
    raiz, cache = ambiente
    pasta = _exemplo(raiz)
    _proibir_render(monkeypatch)
    for n in (1, 2, 3):
        (pasta / "previa" / f"{n:02d}").mkdir(parents=True)
    with pytest.raises(reel_referencia.ErroReferencia, match="no máximo 3 voltas de prévia"):
        reel_referencia.previa(raiz, pasta, cache_fontes=cache)
    assert reel_referencia.LIMITE_PREVIAS == 3  # origem: Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:146
    assert remotion.TEMPO_RENDER_S == 1800

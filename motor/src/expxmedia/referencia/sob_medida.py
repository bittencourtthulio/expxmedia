"""Pasta do reel sob medida e validação do `cenas.json` (D-18, D-19, D-36).

O reel por referência é **código novo por reel**: uma composição Remotion própria, escrita pelo modelo para
imitar a referência cena a cena, com a trilha e os efeitos sintetizados pelo kit (`scripts/audio.mjs`) e a
linha do tempo pela narração (`scripts/montar.mjs`). Os tipos fixos de cena da origem saíram genéricos e não
são portados (D-18). Este módulo cria a pasta do reel a partir do kit e confere o `cenas.json` antes da
montagem. origem: Instragram-Videos/.claude/rules/recriado.md:16-19 e
Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:84-109

Pasta do reel, relativa à raiz da instalação (M9): `referencias/<slug>/`

    referencia.json     marcador: slug, título, origem_url, pedido, analise, peca_id, criado_em, atualizado_em
    analise/            a análise da referência (referencia.analisar) e a leitura.md escrita pelo modelo
    roteiro.txt         a narração; as âncoras das cenas casam com ele, em ordem
    legenda.txt         a legenda do post
    midia/              narração, alinhamento, linha do tempo e trilha (preenchidos na produção)
    reel/cenas.json     trilha, troca, legenda, cauda e as cenas (id, ancora, ev, sons, campos livres)
    reel/package.json   as versões travadas do kit
    reel/src/Reel.tsx   a composição: tela fixa, uma Sequence por cena, legenda por blocos, selo, áudio
    reel/src/cenas.tsx  as cenas (CENAS e FUNDOS por id), desenhadas a partir da leitura

O `Reel.tsx` criado segue o padrão estrutural do reel sob medida aprovado
(Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:167-190: Sequence por cena com 12 quadros
de sobreposição, `ev(nome)` por fração da cena, legenda por blocos, selo dentro do bloco centrado na área
segura, trilha a 0,8) sem nada do visual dele. Diferente do exemplo, a linha do tempo e o áudio chegam por
props (nada de `staticFile` literal nem `timeline.json` importado) e fontes e selo vêm da Alma; cores
literais da paleta da referência são permitidas (D-36).

A validação do `cenas.json` (`validar_cenas`) recusa, citando a cena: trilha sem bpm ou acordes, instrumento
ou efeito desconhecido, âncora que não casa com o roteiro em ordem, som que cita evento inexistente, evento
fora de 0 a 1 e — "para que não tente usar algo que já foi usado" — **trilha com a mesma assinatura** (bpm,
acordes e nomes dos instrumentos) de outro reel da instalação. origem:
Instragram-Videos/remotion/scripts/montar-reel.mjs:50-60,79-91,118-126

Uso:

    from expxmedia.referencia import sob_medida
    r = sob_medida.criar(raiz, "meu-reel", titulo="...", origem_url="https://...")
    erros = sob_medida.validar_cenas(raiz, r["pasta"])
"""
from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from expxmedia.motion import remotion
from expxmedia.nucleo import arquivos, ids, tempo
from expxmedia.nucleo.raiz import relativo
from expxmedia.producao import reel as producao_reel

__all__ = [
    "ErroSobMedida",
    "PASTA_REFERENCIAS",
    "MARCADOR",
    "PASTA_REEL",
    "ROTEIRO",
    "LEGENDA",
    "MIDIA",
    "INSTRUMENTOS",
    "pasta_do_reel",
    "esqueleto_cenas",
    "criar",
    "preparar_projeto",
    "efeitos_disponiveis",
    "assinatura",
    "trilhas_da_instalacao",
    "validar_cenas",
    "conferir_cenas",
]

PASTA_REFERENCIAS = "referencias"
MARCADOR = "referencia.json"
PASTA_REEL = "reel"
ROTEIRO = "roteiro.txt"
LEGENDA = "legenda.txt"
MIDIA = "midia"
PASTA_ANALISE = "analise"
# Instrumentos que a música do kit toca; outro nome não toca nada, em silêncio.
# origem: Instragram-Videos/remotion/scripts/audio.mjs:54-96,221-243
INSTRUMENTOS = ("kick", "caixa", "palma", "chimbal", "pluck", "sino", "pad", "baixo")
AUDIO = remotion.KIT / "scripts" / "audio.mjs"
MENSAGEM_TRILHA = ("a trilha é a mesma do reel {reel} (bpm, acordes e instrumentos). "
                   "Cada reel tem a sua: mude andamento, harmonia ou timbre.")  # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:57

_RE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ErroSobMedida(ValueError):
    """Pasta do reel sob medida inválida ou cenas.json recusado; `erros` lista cada problema."""

    def __init__(self, mensagem: str, erros: list[str] | None = None) -> None:
        super().__init__(mensagem)
        self.erros = erros or [mensagem]


# ---------------------------------------------------------------- pasta


def pasta_do_reel(raiz: Path | str, pasta: Path | str) -> Path:
    """Pasta do reel: um slug (`referencias/<slug>`) ou um caminho dentro da raiz."""
    raiz = Path(raiz)
    texto = str(pasta)
    if _RE_SLUG.match(texto):
        return raiz / PASTA_REFERENCIAS / texto
    return raiz / relativo(raiz, pasta)


def esqueleto_cenas() -> dict[str, Any]:
    """O `cenas.json` a preencher. Trilha e cenas são do modelo, a partir da leitura da referência."""
    return {
        # bpm, acordes e instrumentos escolhidos pelo clima da referência (e diferentes dos outros reels);
        # arpejo, ganho, fade e semente com os padrões do kit.
        # origem: Instragram-Videos/remotion/scripts/audio.mjs:218 (arpejo), :246-247 (fade 1.6, ganho 0.55)
        # e Instragram-Videos/remotion/scripts/montar-reel.mjs:143 (semente 7)
        "trilha": {"bpm": None, "acordes": [], "instrumentos": {}, "arpejo": [0, 1, 2, 1, 2, 0, 1, 2],
                   "ganho": 0.55, "fade_s": 1.6, "semente": 7},
        # troca padrão: whoosh 3 quadros antes de cada cena a partir da 2ª e pop 5 quadros depois de toda cena
        # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:128
        "troca": [{"f": -3, "tipo": "whoosh", "desde": 1}, {"f": 5, "tipo": "pop", "desde": 0}],
        "legenda": {"palavras_por_bloco": 3},  # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:106
        "cauda_s": 1.4,  # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:94
        "apresentador": False,
        "cenas": [],
    }


def _versao_react() -> str:
    pacote = arquivos.ler_json(remotion.KIT / "package.json")
    return pacote["dependencies"]["react"]


_REEL_TSX = '''import React from "react";
import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from "remotion";
import {
  FPS,
  ProvedorAlma,
  REEL,
  SeloPerfil,
  centralizarNaArea,
  mola,
  pilhaFonte,
  rampa,
  urlDoArquivo,
  useAlma,
  type PropsAlma,
} from "@expxmedia/template";
import { CENAS, FUNDOS, type CenaT } from "./cenas";

// Reel sob medida: código próprio deste reel, escrito para imitar a referência cena a cena. Leia
// ../../analise/leitura.md (as 9 seções) e as folhas da referência antes de mexer aqui.
//
// Estrutura: tela fixa, uma Sequence por cena com sobreposição na troca, a legenda por blocos no estilo da
// referência, o selo de quem publica embaixo do conteúdo, tudo dentro do bloco centrado na área segura, e
// a narração com a trilha por baixo. Os valores abaixo são ponto de partida: troque pelo que a leitura mediu
// na referência (fundo, posição, tamanho, transição, cores literais da paleta dela). Fontes, selo e o que é
// de quem publica vêm da Alma (useAlma); a linha do tempo e o áudio chegam por props, gerados pelo motor.

type Palavra = { w: string; f0: number; f1: number };
export type Timeline = { fps: number; totalFrames: number; cenas: CenaT[]; blocos: Palavra[][] };

export type PropsReel = {
  alma: PropsAlma;
  timeline: Timeline;
  // caminhos relativos ao public dir do render; avatar só quando cenas.json diz "apresentador": true
  audio: { narracao: string | null; trilha: string | null; avatar: string | null };
};

// Quadros de sobreposição entre uma cena e a seguinte (a Sequence dura dur + TRANS, menos a última).
const TRANS = 12;
// A trilha fica abaixo da voz.
const VOLUME_TRILHA = 0.8;
// O bloco da legenda entra 2 quadros antes da primeira palavra.
const ENTRA_ANTES = 2;
// Onde o desenho começa e termina em 1080x1920; centralizarNaArea leva o bloco para o centro da área
// segura (220 a 1500) e encolhe se não couber. Ajuste ao seu desenho.
const BLOCO = { topo: 220, base: 1500 };
const LEGENDA = { topo: 1080, altura: 220, tamanho: 84 };
const Y_SELO = 1360;

// Uma cena: recebe o frame local, a duração e ev(nome), o frame local de um evento de cenas.json (o mesmo
// que dispara o som na trilha, então imagem e som batem). Evento que não está em cenas.json é erro.
const Cena: React.FC<{ c: CenaT; primeira: boolean }> = ({ c, primeira }) => {
  const f = useCurrentFrame();
  const Componente = CENAS[c.id];
  if (!Componente) throw new Error(`cena ${c.id}: falta o componente em CENAS (cenas.tsx)`);
  const ev = (nome: string) => {
    if (nome === "0") return 0;
    const fracao = c.ev[nome];
    if (fracao === undefined) throw new Error(`cena ${c.id}: evento "${nome}" não está em ev do cenas.json`);
    return Math.round(fracao * c.dur);
  };
  // troca de cena: a nova entra por cima da anterior durante TRANS quadros (troque pela da referência)
  const entrada = primeira ? 1 : rampa(f, 0, TRANS);
  return (
    <AbsoluteFill style={{ opacity: entrada, background: FUNDOS[c.id] }}>
      <Componente f={f} d={c.dur} ev={ev} cena={c} />
    </AbsoluteFill>
  );
};

// Legenda por blocos, palavra a palavra: a palavra dita acende. Fonte, tamanho, posição e cores no estilo
// da referência.
const Legenda: React.FC<{ f: number; blocos: Palavra[][] }> = ({ f, blocos }) => {
  const { cores, fontes } = useAlma();
  let atual = -1;
  blocos.forEach((b, i) => {
    if (b.length && f >= b[0].f0 - ENTRA_ANTES) atual = i;
  });
  if (atual < 0) return null;
  const b = blocos[atual];
  const s = mola(f, b[0].f0 - ENTRA_ANTES, 12, 200);
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: LEGENDA.topo, height: LEGENDA.altura, display: "flex",
      alignItems: "center", justifyContent: "center", flexWrap: "wrap", columnGap: 24, textAlign: "center",
      opacity: s, transform: `translateY(${(1 - s) * 30}px)` }}>
      {b.map((p, i) => (
        <span key={i} style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: LEGENDA.tamanho,
          lineHeight: 1.1, color: f >= p.f0 ? cores.destaque : cores.apoio }}>
          {p.w}
        </span>
      ))}
    </div>
  );
};

const Tela: React.FC<Omit<PropsReel, "alma">> = ({ timeline, audio }) => {
  const f = useCurrentFrame();
  const { cores } = useAlma();
  if (timeline.fps !== FPS) throw new Error(`linha do tempo a ${timeline.fps} fps; o kit roda a ${FPS}`);
  const n = timeline.cenas.length;
  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      <AbsoluteFill style={centralizarNaArea(BLOCO.topo, BLOCO.base)}>
        {timeline.cenas.map((c, i) => (
          <Sequence key={c.id} from={c.inicio} durationInFrames={c.dur + (i < n - 1 ? TRANS : 0)} name={c.id}>
            <Cena c={c} primeira={i === 0} />
          </Sequence>
        ))}
        <Legenda f={f} blocos={timeline.blocos} />
        <SeloPerfil f={f} y={Y_SELO} />
      </AbsoluteFill>
      {audio.narracao ? <Audio src={urlDoArquivo(audio.narracao)} /> : null}
      {audio.trilha ? <Audio src={urlDoArquivo(audio.trilha)} volume={VOLUME_TRILHA} /> : null}
    </AbsoluteFill>
  );
};

export const Reel: React.FC<PropsReel> = ({ alma, ...resto }) => (
  <ProvedorAlma alma={alma}>
    <Tela {...resto} />
  </ProvedorAlma>
);

// Metadados da composição; o motor acrescenta o id ao registrar o reel para um render.
export const composicao = {
  component: Reel,
  fps: FPS,
  width: REEL.largura,
  height: REEL.altura,
  durationInFrames: 1,
  defaultProps: {} as PropsReel,
  calculateMetadata: ({ props }: { props: PropsReel }) => ({ durationInFrames: props.timeline.totalFrames }),
};
'''

_CENAS_TSX = '''import React from "react";
import { AbsoluteFill } from "remotion";
import { mola, pilhaFonte, useAlma } from "@expxmedia/template";

// As cenas deste reel, uma por id do cenas.json, na ordem da referência. Cada uma desenha o quadro inteiro
// (1080x1920, dentro do bloco centrado) e recebe o frame local (f), a duração em quadros (d), ev(nome) — o
// frame local de um evento do cenas.json, o MESMO que dispara o som, então imagem e som batem — e a cena da
// linha do tempo, com os campos livres do cenas.json. Desenhe cada cena do zero a partir da leitura da SUA
// referência (composição, tipo de cena, jeito de animar); nada reaproveitado de outro reel.

export type CenaT = { id: string; ev: Record<string, number>; inicio: number; dur: number; [campo: string]: unknown };
export type PropsCena = { f: number; d: number; ev: (nome: string) => number; cena: CenaT };

// Rascunho para a primeira prévia: mostra o id da cena. Não é cena de entrega.
export const Rascunho: React.FC<PropsCena> = ({ f, cena }) => {
  const { cores, fontes } = useAlma();
  const s = mola(f, 0);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 72, color: cores.texto,
        transform: `scale(${0.9 + 0.1 * s})`, opacity: s }}>
        {cena.id}
      </div>
    </AbsoluteFill>
  );
};

// id da cena → componente. Toda cena do cenas.json precisa estar aqui.
export const CENAS: Record<string, React.FC<PropsCena>> = {};

// id da cena → fundo da cena, quando ela tem fundo próprio (cor literal da paleta da referência).
export const FUNDOS: Record<string, string> = {};
'''


def criar(
    raiz: Path | str,
    slug: str,
    *,
    titulo: str | None = None,
    origem_url: str | None = None,
    pedido: str | None = None,
) -> dict[str, Any]:
    """Cria `referencias/<slug>/` com o marcador, o `cenas.json` esqueleto e o código do kit.

    A pasta pode já existir (com a análise); o código e o marcador nunca são sobrescritos.
    """
    raiz = Path(raiz)
    if not isinstance(slug, str) or not _RE_SLUG.match(slug):
        sugestao = ids.slug(str(slug))
        raise ErroSobMedida(f"slug inválido: {slug!r} (minúsculas, números e hífen{f'; ex.: {sugestao}' if sugestao else ''})")
    pasta = raiz / PASTA_REFERENCIAS / slug
    reel_dir = pasta / PASTA_REEL
    existentes = [n for n in (MARCADOR, f"{PASTA_REEL}/cenas.json", f"{PASTA_REEL}/src/Reel.tsx") if (pasta / n).exists()]
    if existentes:
        raise ErroSobMedida(f"o reel sob medida {slug} já existe ({', '.join(existentes)}): nada foi sobrescrito")
    (reel_dir / "src").mkdir(parents=True, exist_ok=True)
    (pasta / MIDIA).mkdir(exist_ok=True)
    arquivos.gravar_json(reel_dir / "cenas.json", esqueleto_cenas())
    arquivos.gravar_json(reel_dir / "package.json", {
        "name": f"reel-{slug}",
        "private": True,
        "description": "Reel sob medida: código próprio, escrito para imitar a referência. Fontes, selo e o que é "
                       "de quem publica chegam da Alma por props; o módulo @expxmedia/template é entregue pelo motor.",
        "dependencies": {"react": _versao_react(), "remotion": remotion.VERSAO_KIT},
    })
    (reel_dir / "src" / "Reel.tsx").write_text(_REEL_TSX, encoding="utf-8")
    (reel_dir / "src" / "cenas.tsx").write_text(_CENAS_TSX, encoding="utf-8")
    agora = tempo.agora_iso(raiz)
    marcador = {
        "slug": slug,
        "titulo": titulo.strip() if isinstance(titulo, str) and titulo.strip() else None,
        "origem_url": origem_url or None,
        "pedido": pedido or None,
        "analise": f"{PASTA_ANALISE}/formato.json",
        "peca_id": None,
        "criado_em": agora,
        "atualizado_em": agora,
    }
    arquivos.gravar_json(pasta / MARCADOR, marcador)
    return {
        "slug": slug,
        "pasta": relativo(raiz, pasta),
        "cenas": relativo(raiz, reel_dir / "cenas.json"),
        "reel": relativo(raiz, reel_dir / "src" / "Reel.tsx"),
        "marcador": marcador,
    }


def preparar_projeto(pasta: Path | str, destino: Path | str, composicao: str) -> Path:
    """Projeto Remotion temporário que renderiza o reel sob medida como a composição `composicao`.

    O mesmo projeto do template de reel (`producao.reel.preparar_projeto`: pacotes do kit por link e o
    módulo `@expxmedia/template`), com o registro apontando para `Reel.tsx`.
    """
    reel_dir = Path(pasta) / PASTA_REEL
    for nome in ("package.json", "src/Reel.tsx"):
        if not (reel_dir / nome).is_file():
            raise ErroSobMedida(f"o reel sob medida não tem {PASTA_REEL}/{nome}")
    projeto = producao_reel.preparar_projeto(reel_dir, destino, composicao)
    (projeto / "src" / "composicoes" / composicao / "index.tsx").write_text(
        "// GERADO pelo motor: registra o reel sob medida como uma composição do render.\n"
        'import { composicao as base } from "./Reel";\n\n'
        f"export const composicao = {{ ...base, id: {json.dumps(composicao)} }};\n",
        encoding="utf-8")
    return projeto


# ---------------------------------------------------------------- trilha


@functools.lru_cache(maxsize=1)
def efeitos_disponiveis() -> tuple[str, ...]:
    """Os efeitos sonoros do kit, lidos do próprio `audio.mjs` (a fonte de verdade)."""
    node = shutil.which("node")
    if node is None:
        raise ErroSobMedida("node não encontrado no PATH (os efeitos da trilha vêm de scripts/audio.mjs)")
    codigo = (f"import {{ criarMix }} from {json.dumps(AUDIO.resolve().as_uri())};"
              "console.log(JSON.stringify(criarMix(0.01).EFEITOS));")
    r = subprocess.run([node, "--input-type=module", "-e", codigo], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise ErroSobMedida(f"não consegui ler os efeitos de {AUDIO.name}:\n{r.stderr[-800:]}")
    return tuple(json.loads(r.stdout))


def _numeros(valor: Any) -> Any:
    # 112 e 112.0 são o mesmo número no JSON.stringify do montar.mjs
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, list):
        return [_numeros(v) for v in valor]
    return valor


def assinatura(trilha: dict[str, Any]) -> str:
    """Só bpm, acordes e o conjunto de nomes dos instrumentos (volume, arpejo e semente não contam).
    origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:58"""
    return json.dumps({"bpm": _numeros(trilha.get("bpm")), "acordes": _numeros(trilha.get("acordes")),
                       "instrumentos": sorted(trilha.get("instrumentos") or {})}, sort_keys=True)


def _pastas_do_proprio(pasta: Path) -> tuple[Path, str | None]:
    try:
        peca_id = arquivos.ler_json(pasta / MARCADOR).get("peca_id")
    except (arquivos.ErroArquivo, AttributeError):
        peca_id = None
    return pasta.resolve(), peca_id if isinstance(peca_id, str) and peca_id else None


def trilhas_da_instalacao(raiz: Path | str, fora: Path | str | None = None) -> list[dict[str, Any]]:
    """As trilhas dos outros reels da instalação: `[{"reel", "trilha"}]` (o formato de `--assinaturas`).

    Varre os reels por referência (`referencias/*/reel/cenas.json`) e as peças de reel
    (`pecas/*/*/midia/cenas.json`); `fora` é a pasta do reel em questão, que não conta, nem a peça dele.
    """
    raiz = Path(raiz)
    propria, peca_id = _pastas_do_proprio(Path(fora)) if fora is not None else (None, None)
    candidatos = [(arq, arq.parent.parent) for arq in sorted((raiz / PASTA_REFERENCIAS).glob(f"*/{PASTA_REEL}/cenas.json"))]
    candidatos += [(arq, arq.parent.parent) for arq in sorted((raiz / "pecas").glob("*/*/midia/cenas.json"))]
    lista = []
    for arq, dono in candidatos:
        if propria is not None and dono.resolve() == propria:
            continue
        if peca_id is not None and (dono.name == peca_id or dono.name.startswith(f"{peca_id}-")):
            continue
        try:
            trilha = arquivos.ler_json(arq).get("trilha")
        except (arquivos.ErroArquivo, AttributeError):
            continue
        if isinstance(trilha, dict) and trilha.get("bpm") and trilha.get("acordes"):
            lista.append({"reel": dono.name, "trilha": trilha})
    return lista


# ---------------------------------------------------------------- validação


def _normalizar(palavra: str) -> str:
    # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:79 (minúsculas, NFD sem diacríticos, só [a-z0-9])
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", palavra.lower()) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", sem_acento)


def _numero(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validar_trilha(trilha: Any, erros: list[str]) -> bool:
    if not isinstance(trilha, dict):
        erros.append("trilha ausente: objeto com bpm, acordes e instrumentos")
        return False
    ok = True
    if not _numero(trilha.get("bpm")) or trilha["bpm"] <= 0:
        erros.append("trilha.bpm ausente: escolha o andamento pelo clima da referência")
        ok = False
    acordes = trilha.get("acordes")
    if not isinstance(acordes, list) or not acordes:
        erros.append("trilha.acordes ausente: lista de [raizHz, [notasHz...]]")
        ok = False
    elif not all(isinstance(a, list) and len(a) == 2 and _numero(a[0]) and isinstance(a[1], list) and a[1]
                 and all(_numero(n) for n in a[1]) for a in acordes):
        erros.append("trilha.acordes: cada acorde é [raizHz, [notasHz...]]")
        ok = False
    instrumentos = trilha.get("instrumentos")
    if not isinstance(instrumentos, dict) or not instrumentos:
        erros.append(f"trilha.instrumentos ausente: volumes por instrumento ({', '.join(INSTRUMENTOS)})")
        ok = False
    else:
        for nome, vol in instrumentos.items():
            if nome not in INSTRUMENTOS:
                erros.append(f"trilha: instrumento desconhecido: {nome} (existem: {', '.join(INSTRUMENTOS)})")
                ok = False
            elif not _numero(vol) or vol < 0:
                erros.append(f"trilha: volume do instrumento {nome} não é número positivo")
                ok = False
    return ok


def _validar_sons(rotulo: str, cena: dict[str, Any], efeitos: tuple[str, ...], erros: list[str]) -> None:
    ev = cena.get("ev") if isinstance(cena.get("ev"), dict) else {}
    sons = cena.get("sons", [])
    if not isinstance(sons, list):
        erros.append(f"{rotulo}: sons é uma lista de [evento, efeito, duração?, volume?]")
        return
    for som in sons:
        if not isinstance(som, list) or not 2 <= len(som) <= 4 or not isinstance(som[0], str) or not isinstance(som[1], str):
            erros.append(f"{rotulo}: som fora do formato [evento, efeito, duração?, volume?]: {som!r}")
            continue
        # evento: nome em ev, "0" (início da cena) ou soma "a+b". origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:118-126
        for parte in som[0].split("+"):
            if parte != "0" and parte not in ev:
                erros.append(f'{rotulo}: som cita o evento "{parte}", que não está em ev')
        if som[1] not in efeitos:
            erros.append(f"{rotulo}: efeito desconhecido: {som[1]} (existem: {', '.join(efeitos)})")
        if any(not (_numero(x) or x is None) for x in som[2:]):
            erros.append(f"{rotulo}: duração e volume do som são números")


def validar_cenas(raiz: Path | str, pasta: Path | str, *, efeitos: tuple[str, ...] | None = None) -> list[str]:
    """Os problemas do `cenas.json` do reel (lista vazia = aprovado), cada um citando a cena."""
    raiz = Path(raiz)
    pasta = pasta_do_reel(raiz, pasta)
    arq = pasta / PASTA_REEL / "cenas.json"
    try:
        spec = arquivos.ler_json(arq)
    except arquivos.ErroArquivo as erro:
        return [f"{PASTA_REEL}/cenas.json ilegível: {erro}"]
    if not isinstance(spec, dict):
        return [f"{PASTA_REEL}/cenas.json precisa ser um objeto"]
    efeitos = efeitos if efeitos is not None else efeitos_disponiveis()
    erros: list[str] = []

    if _validar_trilha(spec.get("trilha"), erros):
        minha = assinatura(spec["trilha"])
        for outro in trilhas_da_instalacao(raiz, fora=pasta):
            if assinatura(outro["trilha"]) == minha:
                erros.append(MENSAGEM_TRILHA.format(reel=outro["reel"]))
                break

    troca = spec.get("troca", [])
    if troca is not None and not isinstance(troca, list):
        erros.append("troca é uma lista de {f, tipo, desde?, vol?}")
    for n, t in enumerate(troca or [], 1):
        if not isinstance(t, dict) or not isinstance(t.get("f"), int) or isinstance(t.get("f"), bool):
            erros.append(f"troca {n}: precisa de f (quadros relativos ao início da cena) e tipo")
            continue
        if t.get("tipo") not in efeitos:
            erros.append(f"troca {n}: efeito desconhecido: {t.get('tipo')} (existem: {', '.join(efeitos)})")

    ppb = (spec.get("legenda") or {}).get("palavras_por_bloco") if isinstance(spec.get("legenda"), dict) else None
    if ppb is not None and (isinstance(ppb, bool) or not isinstance(ppb, int) or ppb < 1):
        erros.append("legenda.palavras_por_bloco é um inteiro positivo")
    if spec.get("cauda_s") is not None and (not _numero(spec["cauda_s"]) or spec["cauda_s"] < 0):
        erros.append("cauda_s é um número de segundos")

    cenas = spec.get("cenas")
    if not isinstance(cenas, list) or not cenas or not all(isinstance(c, dict) for c in cenas):
        erros.append("cenas vazia: uma cena por beat da referência, na ordem dela ({id, ancora, ev, sons})")
        return erros
    ids_vistos: list[str] = []
    for n, c in enumerate(cenas, 1):
        cid = c.get("id")
        rotulo = f"cena {n} ({cid})"
        if not isinstance(cid, str) or not cid.strip():
            erros.append(f"cena {n}: sem id")
        else:
            ids_vistos.append(cid)
        if not isinstance(c.get("ancora"), str) or not c["ancora"].strip():
            erros.append(f"{rotulo}: sem âncora (as primeiras palavras da narração em que a cena entra)")
        ev = c.get("ev", {})
        if not isinstance(ev, dict):
            erros.append(f"{rotulo}: ev é um objeto {{evento: fração da duração da cena}}")
        else:
            for nome, fracao in ev.items():
                if not _numero(fracao) or not 0 <= fracao <= 1:
                    erros.append(f'{rotulo}: evento "{nome}" = {fracao} fora de 0 a 1 (fração da duração da cena)')
        _validar_sons(rotulo, c, efeitos, erros)
    repetidos = sorted({i for i in ids_vistos if ids_vistos.count(i) > 1})
    if repetidos:
        erros.append(f"ids de cena repetidos: {', '.join(repetidos)}")

    roteiro = pasta / ROTEIRO
    if not roteiro.is_file():
        erros.append(f"falta {ROTEIRO}: as âncoras são conferidas contra o roteiro")
        return erros
    # âncora casa com o roteiro, em ordem: o mesmo casamento da montagem (o alinhamento está no espaço do
    # roteiro). origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:79-91
    palavras = [_normalizar(p) for p in roteiro.read_text(encoding="utf-8").split()]
    cursor = 0
    for n, c in enumerate(cenas, 1):
        if not isinstance(c.get("ancora"), str):
            continue
        alvo = [a for a in (_normalizar(p) for p in c["ancora"].split()) if a]
        if not alvo:
            continue
        for i in range(cursor, len(palavras)):
            if palavras[i:i + len(alvo)] == alvo:
                cursor = i + 1
                break
        else:
            erros.append(f'cena {n} ({c.get("id")}): âncora "{c["ancora"]}" não casou com o roteiro, em ordem')
    return erros


def conferir_cenas(raiz: Path | str, pasta: Path | str, *, efeitos: tuple[str, ...] | None = None) -> None:
    """`validar_cenas` que levanta ErroSobMedida com todos os problemas."""
    erros = validar_cenas(raiz, pasta, efeitos=efeitos)
    if erros:
        raise ErroSobMedida("cenas.json recusado: " + "; ".join(erros), erros)

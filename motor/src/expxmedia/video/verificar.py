"""Verificação de entrega de vídeo por perfil: o gate mecânico que reprova a peça fora do formato.

Porta de `Instragram-Videos/pipeline/verify.py` e das funções de gate de `Instragram-Videos/pipeline/lib.py`,
com os mesmos limiares. Os modos da origem (padrão, `--sem-cta`, `recriado.json`) viram perfis
nomeados (D-41, D-49):

- ``reel`` — reel narrado em Remotion: as 11 checagens, 30 a 70 s;
- ``reel_pagina`` — reel de página capturada: as 11 checagens, 50 a 70 s;
- ``corte`` — corte de vídeo longo: 50 a 185 s (aviso acima de 75 s), cauda de no máximo 0,80 s
  depois da última legenda (10b) no lugar da comparação com o card, e CTA proibido;
- ``sob_medida`` — como o modo recriado da origem: formato + alinhamento, roteiro e legenda do post
  presentes, narração dentro do vídeo e alinhamento igual ao roteiro; sem PNG de legenda (queimada no render);
- ``aula`` — 1920x1080 ou 1080x1920, 30 fps, h264/aac, -14 ±1 LUFS, pico ≤ -1 dBFS e SRT presente e
  sincronizado; sem faixa de duração.

As 11 checagens: dimensão, fps, duração, codecs, loudness, pico, área segura, legibilidade (≤ 35% dos
cartões abaixo de 0,7 s), sincronia (fim da narração dentro do vídeo e alinhamento igual ao roteiro),
cauda (último quadro igual ao card do CTA, erro médio ≤ 12/255) e CTA presente no roteiro.

Veracidade não é mecânica: nenhuma checagem aqui confere se o que se diz é verdade.

Saída: ``{aprovado, perfil, achados: [{checagem, detalhe, esperado, obtido}], avisos: [{checagem, detalhe}]}``.
Reprova, nunca só avisa: quem chama depende de ``aprovado`` para travar a entrega.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from expxmedia.video import ffmpeg

__all__ = ["Perfil", "Artefatos", "PERFIS", "verificar", "verificar_pasta", "artefatos_da_pasta",
           "duracoes_cartoes", "ultimo_cartao"]

FPS = 30  # origem: Instragram-Videos/pipeline/lib.py:9
SAFE_BOTTOM = 420  # faixa inferior reservada à interface; origem: Instragram-Videos/pipeline/lib.py:10
TOLERANCIA_LUFS = 1.0  # origem: Instragram-Videos/pipeline/verify.py:87
PICO_MAX = -1.0  # origem: Instragram-Videos/pipeline/verify.py:89
CAP_BLOCO_MIN_S = 0.7  # piso de leitura de um bloco na tela; origem: Instragram-Videos/pipeline/lib.py:44
CAP_CURTOS_MAX_FRAC = 0.35  # fração máxima de cartões curtos; origem: Instragram-Videos/pipeline/lib.py:90
SINCRONIA_FOLGA_S = 0.05  # origem: Instragram-Videos/pipeline/verify.py:128
CAUDA_ERRO_MAX = 12  # erro médio por pixel (de 255) contra o card; origem: Instragram-Videos/pipeline/verify.py:156
CAUDA_SEM_CTA_MAX_S = 0.8  # cauda depois da última legenda, sem card; origem: Instragram-Videos/pipeline/verify.py:141

VERTICAL = (1080, 1920)  # origem: Instragram-Videos/pipeline/lib.py:9
HORIZONTAL = (1920, 1080)  # D-41 (aula)

ONZE = ("dimensao", "fps", "duracao", "codecs", "loudness", "pico", "area_segura", "legibilidade",
        "sincronia", "cauda", "cta")


@dataclass(frozen=True)
class Perfil:
    nome: str
    dimensoes: tuple[tuple[int, int], ...]
    checagens: tuple[str, ...]
    duracao_min: float | None = None
    duracao_max: float | None = None
    duracao_aviso: float | None = None  # acima disso passa, com aviso
    cauda: str | None = None  # "card" (compara o último quadro) ou "legenda" (tempo depois da última legenda)
    cta: str | None = None  # "presente" ou "ausente"
    alinhamento_igual_roteiro: bool = True
    usa_offset_audio: bool = True


PERFIS: dict[str, Perfil] = {
    # reel narrado em Remotion; origem: Instragram-Videos/pipeline/lib.py:305-306 (30-70 s), D-49
    "reel": Perfil("reel", (VERTICAL,), ONZE, 30.0, 70.0, cauda="card", cta="presente"),
    # reel de página; origem: Instragram-Videos/pipeline/verify.py:74-75 (50-70 s)
    "reel_pagina": Perfil("reel_pagina", (VERTICAL,), ONZE, 50.0, 70.0, cauda="card", cta="presente"),
    # corte; origem: Instragram-Videos/pipeline/verify.py:74-78 e Instragram-Videos/pipeline/lib.py:138 (185 s)
    "corte": Perfil("corte", (VERTICAL,), ONZE, 50.0, 185.0, duracao_aviso=75.0, cauda="legenda", cta="ausente",
                    alinhamento_igual_roteiro=False),
    # modo recriado; origem: Instragram-Videos/pipeline/verify.py:68-105
    "sob_medida": Perfil("sob_medida", (VERTICAL,),
                         ("dimensao", "fps", "duracao", "codecs", "loudness", "pico", "arquivos", "sincronia"),
                         30.0, 70.0, usa_offset_audio=False),
    # aula (D-41): a origem não tem verificação de aula
    "aula": Perfil("aula", (HORIZONTAL, VERTICAL), ("dimensao", "fps", "codecs", "loudness", "pico", "srt")),
}


@dataclass
class Artefatos:
    """Arquivos que acompanham o vídeo. Ausente é None; a checagem que precisa dele reprova."""
    caps_txt: Path | None = None  # concat demuxer das legendas em PNG (file + duration)
    legendas: Path | None = None  # legendas.json: offset_audio e cta
    alinhamento: Path | None = None  # characters + character_end_times_seconds
    roteiro: Path | None = None
    legenda_post: Path | None = None  # texto do post (sob_medida)
    srt: Path | None = None
    extras: dict[str, Any] = field(default_factory=dict)


def _existe(p: Path) -> Path | None:
    return p if p.exists() else None


def artefatos_da_pasta(pasta: str | Path) -> Artefatos:
    """Artefatos pelos nomes padrão da pasta da peça."""
    pasta = Path(pasta)
    srts = sorted(pasta.glob("*.srt"))
    return Artefatos(
        caps_txt=_existe(pasta / "caps.txt"),
        legendas=_existe(pasta / "legendas.json"),
        alinhamento=_existe(pasta / "alinhamento.json") or _existe(pasta / "alignment.json"),
        roteiro=_existe(pasta / "roteiro.txt"),
        legenda_post=_existe(pasta / "legenda.txt"),
        srt=srts[0] if srts else None,
    )


# ------------------------------------------------------------------ caps.txt

def _itens_caps(caps_txt: Path) -> list[tuple[str, float]]:
    itens, nome = [], ""
    for linha in Path(caps_txt).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("file "):
            resto = linha.split(None, 1)[1]
            nome = resto.split("'")[1] if "'" in resto else resto
        elif linha.startswith("duration ") and nome:
            itens.append((nome, float(linha.split()[1])))
    return itens


def ultimo_cartao(caps_txt: str | Path) -> tuple[str | None, float, float]:
    """(arquivo, início, fim) do último cartão visível (não `blank`). origem: Instragram-Videos/pipeline/lib.py:195-216"""
    t, achado = 0.0, (None, 0.0, 0.0)
    for nome, d in _itens_caps(Path(caps_txt)):
        if Path(nome).stem != "blank":
            achado = (nome, round(t, 3), round(t + d, 3))
        t += d
    return achado


def duracoes_cartoes(caps_txt: str | Path, incluir_end: bool = False) -> list[float]:
    """Durações dos cartões visíveis; fora da conta `blank` (pausa) e `end` (card de duração fixa).
    origem: Instragram-Videos/pipeline/lib.py:219-243"""
    return [d for nome, d in _itens_caps(Path(caps_txt))
            if Path(nome).stem != "blank" and (incluir_end or Path(nome).stem != "end")]


# ------------------------------------------------------------------ SRT

_TEMPO_SRT = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})")


def _segundos(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _deixas_srt(srt: Path) -> list[tuple[float, float]]:
    deixas = []
    for m in _TEMPO_SRT.finditer(srt.read_text(encoding="utf-8")):
        g = m.groups()
        deixas.append((_segundos(*g[:4]), _segundos(*g[4:])))
    return deixas


# ------------------------------------------------------------------ verificação

class _Coletor:
    def __init__(self, perfil: Perfil):
        self.perfil = perfil
        self.achados: list[dict[str, Any]] = []
        self.avisos: list[dict[str, str]] = []

    def checa(self, cond: bool, checagem: str, detalhe: str, esperado: str, obtido: Any) -> None:
        if not cond:
            self.achados.append({"checagem": checagem, "detalhe": detalhe, "esperado": esperado, "obtido": obtido})

    def ausente(self, checagem: str, nome: str) -> None:
        self.checa(False, checagem, f"artefato ausente: {nome}", f"{nome} presente", None)

    def resultado(self) -> dict[str, Any]:
        return {"aprovado": not self.achados, "perfil": self.perfil.nome, "achados": self.achados,
                "avisos": self.avisos}


def _faixa(p: Perfil) -> str:
    return f"{p.duracao_min:g}-{p.duracao_max:g} s"


def _ler_json(p: Path) -> dict[str, Any]:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _ultimo_quadro(video: Path, destino_dir: Path) -> Path | None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-1", "-i", str(video), "-an",
                    "-fps_mode", "passthrough", str(destino_dir / "f_%03d.png")], capture_output=True, text=True)
    quadros = sorted(destino_dir.glob("f_*.png"))
    return quadros[-1] if quadros else None


def verificar(video: str | Path, perfil: str, artefatos: Artefatos | None = None) -> dict[str, Any]:
    """Verifica `video` no `perfil` com os `artefatos` que o acompanham. Não levanta por reprovação."""
    if perfil not in PERFIS:
        raise ValueError(f"perfil desconhecido: {perfil} (conhecidos: {', '.join(PERFIS)})")
    p = PERFIS[perfil]
    video = Path(video)
    if not video.exists():
        raise FileNotFoundError(f"vídeo não existe: {video.name}")
    art = artefatos or Artefatos()
    c = _Coletor(p)
    chk = set(p.checagens)
    s = ffmpeg.sondar(video)
    dur = s["duracao"] or 0.0

    # 1 dimensão — origem: Instragram-Videos/pipeline/verify.py:38-39
    if "dimensao" in chk:
        dims = (s["largura"], s["altura"])
        esperado = " ou ".join(f"{w}x{h}" for w, h in p.dimensoes)
        c.checa(dims in p.dimensoes, "dimensao", f"resolução {dims[0]}x{dims[1]}", esperado, f"{dims[0]}x{dims[1]}")

    # 2 fps — origem: Instragram-Videos/pipeline/verify.py:41-42
    if "fps" in chk:
        c.checa(s["fps"] == f"{FPS}/1", "fps", f"framerate {s['fps']}", f"{FPS}/1", s["fps"])

    # 3 duração — origem: Instragram-Videos/pipeline/verify.py:68-78
    if "duracao" in chk:
        c.checa(p.duracao_min <= dur <= p.duracao_max, "duracao",
                f"duração {dur:.1f} s fora da faixa do perfil {p.nome}", _faixa(p), round(dur, 2))
        if p.duracao_aviso is not None and dur > p.duracao_aviso and dur <= p.duracao_max:
            c.avisos.append({"checagem": "duracao",
                             "detalhe": f"{p.nome} longo: {dur:.0f} s, acima de {p.duracao_aviso:g} s; só passa disso "
                                        f"quando a ideia não cabe"})

    # 4 codecs — origem: Instragram-Videos/pipeline/verify.py:80-81
    if "codecs" in chk:
        c.checa("h264" in s["codecs"] and "aac" in s["codecs"], "codecs", f"codecs {s['codecs']}",
                "h264 + aac", s["codecs"])

    # 5 e 6 loudness e pico — origem: Instragram-Videos/pipeline/verify.py:83-90
    if "loudness" in chk or "pico" in chk:
        lufs, pico = ffmpeg.medir(video)
        if "loudness" in chk:
            c.checa(lufs is not None and abs(lufs - ffmpeg.ALVO_LUFS) <= TOLERANCIA_LUFS, "loudness",
                    f"loudness {lufs} LUFS", f"{ffmpeg.ALVO_LUFS:g} ±{TOLERANCIA_LUFS:g} LUFS", lufs)
        if "pico" in chk:
            c.checa(pico is not None and pico <= PICO_MAX, "pico", f"pico {pico} dBFS",
                    f"≤ {PICO_MAX:.1f} dBFS", pico)

    caps_txt = art.caps_txt if art.caps_txt and Path(art.caps_txt).exists() else None

    # 7 área segura — origem: Instragram-Videos/pipeline/verify.py:107-116
    if "area_segura" in chk:
        if caps_txt is None:
            c.ausente("area_segura", "caps.txt")
        else:
            invasoras = []
            for nome in dict.fromkeys(n for n, _ in _itens_caps(caps_txt)):
                if Path(nome).stem == "blank":
                    continue
                with Image.open(caps_txt.parent / nome) as img:
                    alfa = img.convert("RGBA").getchannel("A")
                    w, h = alfa.size
                    if alfa.crop((0, h - SAFE_BOTTOM, w, h)).getbbox():
                        invasoras.append(Path(nome).name)
            c.checa(not invasoras, "area_segura",
                    f"safe area inferior invadida por {len(invasoras)} legenda(s): {invasoras[:3]}",
                    f"nenhum pixel visível nos {SAFE_BOTTOM} px inferiores", invasoras)

    # 8 legibilidade — origem: Instragram-Videos/pipeline/lib.py:259-277
    if "legibilidade" in chk:
        if caps_txt is None:
            c.ausente("legibilidade", "caps.txt")
        else:
            durs = duracoes_cartoes(caps_txt)
            esperado = f"≤ {CAP_CURTOS_MAX_FRAC:.0%} dos cartões abaixo de {CAP_BLOCO_MIN_S:g} s"
            if not durs:
                c.checa(False, "legibilidade", "caps.txt não tem nenhum cartão de legenda", esperado, None)
            else:
                curtos = [d for d in durs if d < CAP_BLOCO_MIN_S]
                frac = len(curtos) / len(durs)
                c.checa(frac <= CAP_CURTOS_MAX_FRAC, "legibilidade",
                        f"legibilidade da legenda: {len(curtos)} de {len(durs)} cartões ({frac:.0%}) abaixo de "
                        f"{CAP_BLOCO_MIN_S:g} s na tela (mediana {statistics.median(durs):.2f} s, "
                        f"mínimo {min(durs):.2f} s)", esperado, round(frac, 4))

    # 11-bis arquivos do sob medida — origem: Instragram-Videos/pipeline/verify.py:92-94
    if "arquivos" in chk:
        faltam = [n for n, a in (("alinhamento", art.alinhamento), ("roteiro", art.roteiro),
                                 ("legenda do post", art.legenda_post)) if not (a and Path(a).exists())]
        c.checa(not faltam, "arquivos", f"faltam: {', '.join(faltam)}",
                "alinhamento, roteiro e legenda do post presentes", faltam)

    # 9 sincronia — origem: Instragram-Videos/pipeline/verify.py:96-99 e 125-128
    legendas = _ler_json(art.legendas) if art.legendas and Path(art.legendas).exists() else None
    if "sincronia" in chk:
        esperado = f"fim da narração ≤ duração + {SINCRONIA_FOLGA_S:g} s" + (
            " e alinhamento igual ao roteiro" if p.alinhamento_igual_roteiro else "")
        if not (art.alinhamento and Path(art.alinhamento).exists()):
            if "arquivos" not in chk:
                c.ausente("sincronia", "alinhamento")
        elif p.usa_offset_audio and legendas is None:
            c.ausente("sincronia", "legendas.json")
        else:
            al = _ler_json(art.alinhamento)
            offset = float(legendas["offset_audio"]) if p.usa_offset_audio else 0.0
            fins = al.get("character_end_times_seconds") or [0.0]
            fim = max(fins) + offset
            c.checa(fim <= dur + SINCRONIA_FOLGA_S, "sincronia",
                    f"narração termina em {fim:.2f} s, depois dos {dur:.2f} s do vídeo", esperado, round(fim, 3))
            if p.alinhamento_igual_roteiro:
                if not (art.roteiro and Path(art.roteiro).exists()):
                    if "arquivos" not in chk:
                        c.ausente("sincronia", "roteiro")
                else:
                    texto = "".join(al.get("characters") or [])
                    roteiro = Path(art.roteiro).read_text(encoding="utf-8")
                    c.checa(texto.strip() == roteiro.strip(), "sincronia",
                            "o alinhamento não descreve o roteiro caractere a caractere", esperado, texto)

    # 10 cauda — origem: Instragram-Videos/pipeline/verify.py:130-158 (card) e 136-141 (10b, sem CTA)
    if "cauda" in chk:
        if caps_txt is None:
            c.ausente("cauda", "caps.txt")
        else:
            nome, ini, fim = ultimo_cartao(caps_txt)
            if p.cauda == "legenda":
                esperado = f"≤ {CAUDA_SEM_CTA_MAX_S:.2f} s depois da última legenda"
                if not nome:
                    c.checa(False, "cauda", "caps.txt não tem nenhum cartão de legenda", esperado, None)
                else:
                    sobra = dur - fim
                    c.checa(sobra <= CAUDA_SEM_CTA_MAX_S, "cauda",
                            f"cauda de {sobra:.2f} s depois da última legenda", esperado, round(sobra, 3))
            else:
                esperado = f"erro médio ≤ {CAUDA_ERRO_MAX}/255"
                if not nome:
                    c.checa(False, "cauda", "caps.txt não tem nenhum cartão de legenda", esperado, None)
                else:
                    with tempfile.TemporaryDirectory() as tmp:
                        quadro = _ultimo_quadro(video, Path(tmp))
                        if quadro is None:
                            c.checa(False, "cauda", "não foi possível extrair o último quadro do vídeo", esperado, None)
                        else:
                            cartao = Image.open(caps_txt.parent / nome).convert("RGBA")
                            ultimo = Image.open(quadro).convert("RGB")
                            if ultimo.size != cartao.size:
                                c.checa(False, "cauda",
                                        f"último quadro {ultimo.size[0]}x{ultimo.size[1]} não tem o tamanho do "
                                        f"cartão {cartao.size[0]}x{cartao.size[1]}", esperado, None)
                            else:
                                opaco = cartao.getchannel("A").point(lambda v: 255 if v == 255 else 0)
                                dif = ImageChops.difference(ultimo, cartao.convert("RGB")).convert("L")
                                erro = ImageStat.Stat(dif, mask=opaco).mean[0]
                                c.checa(erro <= CAUDA_ERRO_MAX, "cauda",
                                        f"último quadro não é o card do CTA ({Path(nome).name}, {ini:.2f}-{fim:.2f} s; "
                                        f"erro médio {erro:.1f}/255)", esperado, round(erro, 2))

    # 11 CTA — origem: Instragram-Videos/pipeline/verify.py:160-166
    if "cta" in chk:
        if legendas is None:
            c.ausente("cta", "legendas.json")
        elif p.cta == "ausente":
            cta = legendas.get("cta")
            c.checa(cta is None, "cta", f"vídeo sem CTA, mas legendas.json traz '{cta}'",
                    "sem CTA (cta null em legendas.json)", cta)
        else:
            cta = legendas.get("cta")
            roteiro = (Path(art.roteiro).read_text(encoding="utf-8")
                       if art.roteiro and Path(art.roteiro).exists() else "")
            c.checa(bool(cta) and cta in roteiro, "cta", f"CTA '{cta}' ausente da narração",
                    "CTA de legendas.json presente no roteiro", cta)

    # SRT da aula (D-41): presente, em ordem, sem sobreposição e dentro da duração
    if "srt" in chk:
        esperado = "SRT presente, em ordem e dentro da duração do vídeo"
        if not (art.srt and Path(art.srt).exists()):
            c.checa(False, "srt", "artefato ausente: SRT", esperado, None)
        else:
            deixas = _deixas_srt(Path(art.srt))
            problemas = []
            if not deixas:
                problemas.append("nenhuma legenda com tempo válido")
            anterior = 0.0
            for i, (ini, fim) in enumerate(deixas, 1):
                if fim <= ini:
                    problemas.append(f"legenda {i} termina antes de começar")
                if ini < anterior - 0.001:
                    problemas.append(f"legenda {i} começa antes do fim da anterior")
                anterior = max(anterior, fim)
            if deixas and deixas[-1][1] > dur + SINCRONIA_FOLGA_S:
                problemas.append(f"última legenda termina em {deixas[-1][1]:.2f} s, depois dos {dur:.2f} s do vídeo")
            c.checa(not problemas, "srt", "; ".join(problemas), esperado,
                    round(deixas[-1][1], 3) if deixas else None)

    return c.resultado()


def verificar_pasta(pasta: str | Path, perfil: str, video: str | Path | None = None) -> dict[str, Any]:
    """Atalho: artefatos pelos nomes padrão da pasta; vídeo explícito ou o único .mp4 da pasta."""
    pasta = Path(pasta)
    if video is None:
        mp4s = sorted(pasta.glob("*.mp4"))
        if len(mp4s) != 1:
            raise FileNotFoundError(f"esperado exatamente um .mp4 em {pasta.name}, achados {len(mp4s)}")
        video = mp4s[0]
    return verificar(video, perfil, artefatos_da_pasta(pasta))

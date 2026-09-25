"""Edição da gravação de tela por cues: cada trecho gravado cabe no tempo da sua fala (D-32).

Porta de `editar_demo.py` (versão mais evoluída) **sem nada da máquina de origem**: nada de
geometria de monitor, perfil de editor, teclado ou caminho fixo. A automação da gravação fica fora
(D-32); a entrada é a gravação pronta (um ou mais mp4) e as janelas por cue.
origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py

Janela (uma por cue com tela, na ordem da fala):

    {"cue": "s2", "arquivo": "gravacao/tela.mp4",           # relativo à raiz (M9)
     "inicio": 12.3 | {"marca": "abrir", "desloc": -1.0},   # segundos da gravação ou marca
     "fim":    {"marca": "tickets"},
     "rotulo": "editor · projeto",                          # barra da janela na composição
     "camera": [{"t": 0, "cx": 700}],                       # centro da câmera do 9:16 (px da gravação)
     "crop":  {"x": 0, "y": 0, "w": 1920, "h": 1080},       # enquadramento 16:9 (px da saída 1920x1080)
     "crop9": null}                                         # enquadramento do 9:16; null = crop

O fim da fala de cada janela é o cue da janela seguinte; o da última é `cue_final` (padrão: o cue
seguinte no tempo, ou `duration`). Regra só-acelera/congela (origem: editar_demo.py:53-60):
`rate = max(1, gravado / fala)`; gravação mais curta roda em 1x e **congela o último quadro** até
completar a fala. Nunca desacelera: câmera lenta aparece (base/gravacao-de-tela.md, risco 2).

Saída: `demo.mp4` (sem áudio, começa no primeiro cue com tela, soma exata das falas) e `demo.json`
no formato da origem (`inicio`, `segmentos[{cue, de, ate, rate, janela, camera, crop, crop9}]`,
`camera`), mais `duracao`. O enquadramento 9:16 é dado (`crop9` + `camera`), aplicado pela composição;
`camera_x` e `recorte` são o porte da mesma conta, para quem precisar dela em Python.
origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:78-103

Diferenças deliberadas em relação à origem:

- o fim de um trecho é limitado à duração real do arquivo (na origem, um fim além do arquivo
  deixava o trecho curto e o demo menor que a fala);
- o `tpad` de clone entra sempre, com 2 quadros de folga além do congelamento, e o `trim=duration`
  corta no tempo exato: o arredondamento de quadros do `fps` nunca encurta o trecho.

Uso:

    from expxmedia.aula import editar_tela
    marcas = editar_tela.ler_marcas("gravacao/marks-rel.json")
    editar_tela.editar(raiz, "pecas/.../midia/cues.json", janelas, "pecas/.../midia/demo.mp4",
                       "pecas/.../midia/demo.json", marcas=marcas)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroEditarTela",
    "FPS",
    "LARGURA",
    "ALTURA",
    "TRANSICAO_CAMERA_S",
    "SELO_ACELERADO",
    "velocidade",
    "ler_marcas",
    "ponto_por_caracteres",
    "camera_x",
    "recorte",
    "editar",
]

FPS = 30  # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:46
LARGURA, ALTURA = 1920, 1080  # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:57
CRF = "18"  # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:68
PRESET = "medium"  # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:68
LIMIAR_CONGELAR_S = 0.01  # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:58
FOLGA_QUADROS = 2  # quadros além do congelamento, cortados pelo trim=duration (valor do motor)
TRANSICAO_CAMERA_S = 0.3  # ±0,3 s em torno de cada ponto; origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:83
SELO_ACELERADO = 1.5  # a composição mostra "N× acelerado" a partir daqui; origem: Aula.tsx:108
CAUDA_ERRO = 800


class ErroEditarTela(ValueError):
    """Entrada que não dá um demo confiável, ou ffmpeg que falhou."""


def velocidade(gravado_s: float, fala_s: float) -> tuple[float, float]:
    """(rate, congelar_s) de um trecho: só acelera; o que faltar congela o último quadro.

    origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:54-55
    """
    rate = max(1.0, gravado_s / fala_s)
    return rate, max(0.0, fala_s - gravado_s / rate)


def ler_marcas(caminho: Path | str, t0: float | None = None) -> dict[str, float]:
    """Marcas de tempo -> {rótulo: segundos desde o início da gravação}.

    Aceita `marks-rel.json` (`{"t0", "marks": [{"label", "s"}]}`, origem: editar_demo.py:13-14) e
    `marks.jsonl` (uma linha `{"label", "t": epoch}` por passo, origem: gravacao/demo.py:72-75); o
    segundo precisa de `t0`, o epoch do primeiro quadro da gravação.
    """
    caminho = Path(caminho)
    if caminho.suffix == ".jsonl":
        if t0 is None:
            raise ErroEditarTela(f"{caminho.name} tem epoch; informe t0 (o instante do início da gravação)")
        linhas, _ = arquivos.ler_jsonl(caminho)
        return {m["label"]: round(float(m["t"]) - t0, 3) for m in linhas}
    dados = arquivos.ler_json(caminho)
    return {m["label"]: float(m["s"]) for m in dados["marks"]}


def ponto_por_caracteres(inicio: float, fim: float, texto: str, trecho: str) -> float:
    """Instante em que `trecho` começa a aparecer numa digitação de `texto` entre `inicio` e `fim`.

    Proporcional aos caracteres: só vale para texto colado em ritmo constante
    (origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:18-21).
    """
    texto = texto.rstrip("\n")
    posicao = texto.find(trecho)
    if posicao < 0:
        raise ErroEditarTela(f"o trecho {trecho!r} não está no texto digitado")
    return inicio + (fim - inicio) * posicao / len(texto)


def camera_x(camera: list[dict[str, float]], t: float) -> float:
    """Centro horizontal da câmera do 9:16 no tempo `t` do demo (origem: Aula.tsx:78-86)."""
    cx = float(camera[0]["cx"])
    for k in camera[1:]:
        a, b = k["t"] - TRANSICAO_CAMERA_S, k["t"] + TRANSICAO_CAMERA_S
        if t <= a:
            continue
        if t >= b:
            cx = float(k["cx"])
        else:
            cx = cx + (float(k["cx"]) - cx) * (t - a) / (b - a)
    return cx


def recorte(seg: dict[str, Any], cx: float, largura: float, altura: float, *, vertical: bool,
            origem: tuple[int, int] = (LARGURA, ALTURA)) -> dict[str, float]:
    """Posição e escala do demo dentro da área `largura`x`altura` (origem: Aula.tsx:94-103).

    No 9:16 escala pela altura de `crop9` e a câmera anda na horizontal, presa dentro dele; no 16:9
    escala `crop` para a largura da área.
    """
    crop = seg["crop9"] if vertical else seg["crop"]
    if vertical:
        escala = altura / crop["h"]
        meia = largura / escala / 2
        centro = min(max(cx, crop["x"] + meia), crop["x"] + crop["w"] - meia) * escala
        left = largura / 2 - centro
    else:
        escala = largura / crop["w"]
        left = -crop["x"] * escala
    return {"left": left, "top": -crop["y"] * escala, "largura": origem[0] * escala,
            "altura": origem[1] * escala, "escala": escala}


# ------------------------------------------------------------------ edição

def _tempo(valor: Any, marcas: dict[str, float], campo: str, cue: str) -> float:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, dict) and "marca" in valor:
        if valor["marca"] not in marcas:
            raise ErroEditarTela(f"janela {cue}: a marca {valor['marca']!r} de {campo} não existe")
        return marcas[valor["marca"]] + float(valor.get("desloc") or 0.0)
    raise ErroEditarTela(f"janela {cue}: {campo} precisa ser segundos ou {{'marca': rótulo}}")


def _duracao(caminho: Path) -> float:
    from expxmedia.video import ffmpeg

    try:
        d = ffmpeg.sondar(caminho)["duracao"]
    except ffmpeg.ErroFfmpeg as erro:
        raise ErroEditarTela(str(erro)) from None
    if not d:
        raise ErroEditarTela(f"ffprobe não leu a duração de {caminho.name}")
    return float(d)


def editar(
    raiz: Path | str,
    cues: dict[str, Any] | Path | str,
    janelas: list[dict[str, Any]],
    destino_mp4: Path | str,
    destino_json: Path | str | None = None,
    *,
    marcas: dict[str, float] | None = None,
    cue_final: str | None = None,
    so_json: bool = False,
) -> dict[str, Any]:
    """Monta `demo.mp4` e `demo.json`; devolve o conteúdo do `demo.json`.

    `cues` é o `cues.json` (dict ou caminho relativo à raiz). `so_json` regrava só o JSON
    (origem: editar_demo.py:66, `SO_JSON=1`).
    """
    raiz = Path(raiz)
    if not isinstance(cues, dict):
        cues = arquivos.ler_json(raiz / instalacao.relativo(raiz, cues))
    tempos: dict[str, float] = cues.get("cues") or {}
    marcas = marcas or {}
    if not janelas:
        raise ErroEditarTela("nenhuma janela de tela")
    for j in janelas:
        if j.get("cue") not in tempos:
            raise ErroEditarTela(f"a janela aponta para o cue {j.get('cue')!r}, que não está no cues.json")

    # fim da fala de cada janela: o cue da seguinte; o da última, cue_final
    if cue_final is None:
        ultimo = tempos[janelas[-1]["cue"]]
        depois = sorted((t, n) for n, t in tempos.items() if t > ultimo)
        fim_final = depois[0][0] if depois else float(cues.get("duration") or 0.0)
    elif cue_final in tempos:
        fim_final = tempos[cue_final]
    else:
        raise ErroEditarTela(f"cue_final {cue_final!r} não está no cues.json")
    limites = [tempos[j["cue"]] for j in janelas] + [fim_final]
    if any(b <= a for a, b in zip(limites, limites[1:])):
        raise ErroEditarTela("as janelas precisam seguir a ordem dos cues, cada uma com fala de duração positiva")

    arquivos_rel = sorted({str(j["arquivo"]) for j in janelas})
    caminhos = [raiz / instalacao.relativo(raiz, a) for a in arquivos_rel]
    for c in caminhos:
        if not c.is_file():
            raise ErroEditarTela(f"a gravação {instalacao.relativo(raiz, c)} não existe")
    duracoes = [_duracao(c) for c in caminhos]

    filtros, segs, t = [], [], 0.0
    for i, j in enumerate(janelas):
        cue = j["cue"]
        alvo = limites[i + 1] - limites[i]
        k = arquivos_rel.index(str(j["arquivo"]))
        a = max(0.0, _tempo(j.get("inicio"), marcas, "inicio", cue))
        b = min(duracoes[k], _tempo(j.get("fim"), marcas, "fim", cue))
        if b <= a:
            raise ErroEditarTela(f"janela {cue}: o trecho gravado está vazio ({a:.3f} a {b:.3f} s)")
        rate, hold = velocidade(b - a, alvo)
        congelar = (hold if hold > LIMIAR_CONGELAR_S else 0.0) + FOLGA_QUADROS / FPS
        # origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:57-60
        f = (f"[{k}:v]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{rate:.4f},fps={FPS},"
             f"scale={LARGURA}:{ALTURA},setsar=1,tpad=stop_mode=clone:stop_duration={congelar:.3f},"
             f"trim=duration={alvo:.3f},setpts=PTS-STARTPTS[v{i}]")
        filtros.append(f)
        # origem: editar_demo.py:62 — pontos da câmera no tempo da gravação -> tempo do demo
        camera = [
            {"t": round(t + max(0.0, float(p.get("t") or 0.0) - a) / rate, 3), "cx": p["cx"]}
            for p in (j.get("camera") or [])
        ]
        crop = j.get("crop") or {"x": 0, "y": 0, "w": LARGURA, "h": ALTURA}
        segs.append({
            "cue": cue, "de": round(t, 3), "ate": round(t + alvo, 3), "rate": round(rate, 2),
            "janela": j.get("rotulo") or "", "camera": camera, "crop": crop,
            "crop9": j.get("crop9") or crop,
        })
        t += alvo
    filtros.append("".join(f"[v{i}]" for i in range(len(janelas)))
                   + f"concat=n={len(janelas)}:v=1:a=0,format=yuv420p[out]")

    saida = raiz / instalacao.relativo(raiz, destino_mp4)
    if not so_json:
        saida.parent.mkdir(parents=True, exist_ok=True)
        parcial = saida.with_name(saida.name + ".parcial.mp4")
        entradas = [x for c in caminhos for x in ("-i", str(c))]
        r = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
             "-map", "[out]", "-an", "-c:v", "libx264", "-crf", CRF, "-preset", PRESET, str(parcial)],
            capture_output=True, text=True,
        )
        if r.returncode:
            parcial.unlink(missing_ok=True)
            raise ErroEditarTela(f"ffmpeg não montou o demo:\n{r.stderr[-CAUDA_ERRO:]}")
        parcial.replace(saida)

    demo = {
        "inicio": limites[0],
        "segmentos": segs,
        "camera": [p for s in segs for p in s["camera"]],
        "duracao": round(t, 3),
    }
    destino_json = destino_json or saida.with_suffix(".json")
    arquivos.gravar_json(raiz / instalacao.relativo(raiz, destino_json), demo)
    return json.loads(json.dumps(demo))

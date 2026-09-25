"""Compilação de aulas: trechos de várias aulas produzidas num MP4 só, com um SRT único deslocado.

Porta da compilação de episódios da origem (origem: cursos-ia/radar-ia-jev-completo/README.md:6-23). Nada é regravado;
cada parte é o trecho [ini, fim) de uma aula já produzida (`fim` null = até o fim), com os cortes escolhidos
no meio das pausas para tirar ganchos como "no próximo episódio". A regra de corte é a mesma nos quadros do
vídeo e no SRT (origem: cursos-ia/radar-ia-jev-completo/src/JevCompleto.tsx:34-50 e gerar_srt.py:11-19):

- `from` acumulado em quadros; `trim = round(ini x FPS)`; `frames = round((fim - ini) x FPS)`;
- legenda entra na parte se `start < fim` e `end > ini`, cortada nas bordas da parte e deslocada por
  `from / FPS - ini`.

Diferença deliberada: a origem recompunha o episódio longo no Remotion a partir das cenas copiadas de cada
episódio (e precisou de `--timeout=120000`). Aqui cada parte já é um MP4 aprovado; o motor corta os mesmos
quadros com o ffmpeg e junta, normaliza a mistura e verifica no perfil `aula`, sem render novo.

A compilação é uma peça `aula` nova, com `compoe` apontando as aulas usadas, na ordem.

Uso:

    from expxmedia.aula import compilar
    r = compilar.compilar(raiz, [{"peca_id": "P-...", "ini": 0, "fim": 66.7, "nome": "parte 1"},
                                 {"peca_id": "P-...", "ini": 2.47, "fim": None, "nome": "parte 2"}],
                          titulo="Curso completo", formato="16:9")
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from expxmedia.aula import cues as aula_cues
from expxmedia.legendar import srt
from expxmedia.nucleo import arquivos, rastro
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.video import ffmpeg, verificar

__all__ = [
    "ErroCompilar",
    "FPS",
    "legendas_compiladas",
    "ler_srt",
    "ler_partes",
    "compilar",
]

FPS = 30  # origem: cursos-ia/radar-ia-jev-completo/gerar_srt.py:10
PERFIL = "aula"
CRF, PRESET = "18", "medium"  # mesma codificação da edição da tela; origem: cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:67-68
AUDIO_BITRATE = "192k"
CAUDA_ERRO = 1500
_RE_TEMPO = re.compile(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)")


class ErroCompilar(ValueError):
    """Partes fora do formato, aula inexistente ou sem o formato pedido. `campo` diz onde."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


# ---------------------------------------------------------------- regra de corte


def legendas_compiladas(partes: list[dict[str, Any]], fps: int = FPS) -> tuple[list[dict[str, Any]], int]:
    """([{start, end, lines}] na linha do tempo longa, total de quadros).

    Cada parte: `{"ini", "fim", "legendas"}` com `fim` já resolvido.
    origem: cursos-ia/radar-ia-jev-completo/gerar_srt.py:11-19
    """
    em, caps = 0, []
    for p in partes:
        ini, fim = float(p["ini"]), float(p["fim"])
        for c in p["legendas"]:
            if c["start"] < fim and c["end"] > ini:
                desloc = em / fps - ini
                caps.append({"start": round(max(c["start"], ini) + desloc, 3), "end": round(min(c["end"], fim) + desloc, 3),
                             "lines": list(c["lines"])})
        em += round((fim - ini) * fps)
    return caps, em


def ler_srt(caminho: Path | str) -> list[dict[str, Any]]:
    """[{start, end, lines}] de um SRT (o formato que `legendar.srt` grava)."""
    blocos = re.split(r"\n\s*\n", Path(caminho).read_text(encoding="utf-8-sig").strip())
    saida = []
    for bloco in blocos:
        linhas = bloco.splitlines()
        tempo = next((i for i, l in enumerate(linhas) if _RE_TEMPO.search(l)), None)
        if tempo is None:
            continue
        g = [int(x) for x in _RE_TEMPO.search(linhas[tempo]).groups()]
        saida.append({"start": g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                      "end": g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                      "lines": [l for l in linhas[tempo + 1:] if l.strip()]})
    return saida


# ---------------------------------------------------------------- partes


def _numero(valor: Any, campo: str, n: int, nulo: bool = False) -> float | None:
    if valor is None and nulo:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
        raise ErroCompilar("partes", f"a parte {n}: {campo} é um número de segundos ≥ 0" + (" ou null" if nulo else ""))
    return float(valor)


def ler_partes(raiz: Path | str, partes: Any, formato: str) -> list[dict[str, Any]]:
    """Confere as partes e resolve cada uma: vídeo do formato, legendas, `fim` e os quadros do corte."""
    raiz = Path(raiz)
    if formato not in modelo.TIPOS["aula"]:
        raise ErroCompilar("formato", f"formato {formato!r} (aula sai em {', '.join(modelo.TIPOS['aula'])})")
    if not isinstance(partes, list) or len(partes) < 2:
        raise ErroCompilar("partes", "lista com pelo menos duas partes {\"peca_id\", \"ini\", \"fim\", \"nome\"}")
    nome_video = f"saida/aula-{formato.replace(':', 'x')}.mp4"
    saida = []
    for n, p in enumerate(partes, 1):
        if not isinstance(p, dict) or not isinstance(p.get("peca_id"), str):
            raise ErroCompilar("partes", f"a parte {n} não tem peca_id")
        fora = sorted(set(p) - {"peca_id", "ini", "fim", "nome"})
        if fora:
            raise ErroCompilar("partes", f"a parte {n} tem a chave desconhecida '{fora[0]}'")
        try:
            peca = modelo.carregar(raiz, p["peca_id"])
        except modelo.ErroPeca as erro:
            raise ErroCompilar("partes", f"a parte {n}: {erro}") from None
        if peca["tipo"] != "aula":
            raise ErroCompilar("partes", f"a parte {n}: {p['peca_id']} é {peca['tipo']}, não aula")
        pasta = modelo.pasta(raiz, p["peca_id"])
        final = next((a["caminho"] for a in peca["arquivos"] if a["papel"] == "final" and a["formato"] == formato), None)
        if final is None or not (pasta / final).is_file():
            raise ErroCompilar("partes", f"a parte {n}: a aula {p['peca_id']} não tem o final em {formato} ({nome_video})")
        cues = aula_cues.ler(pasta / "midia")
        legendas = arquivos.ler_json(pasta / "midia" / "legendas.json", padrao=None)
        if not isinstance(cues, dict) or not isinstance(legendas, list):
            raise ErroCompilar("partes", f"a parte {n}: a aula {p['peca_id']} não tem cues.json e legendas.json em midia/")
        ini = _numero(p.get("ini", 0), "ini", n)
        fim = _numero(p.get("fim"), "fim", n, nulo=True)
        fim = float(cues["duration"]) if fim is None else fim  # origem: cursos-ia/radar-ia-jev-completo/gerar_srt.py:14
        if fim <= ini or fim > float(cues["duration"]) + 1.0 / FPS:
            raise ErroCompilar("partes", f"a parte {n}: trecho [{ini}, {fim}) fora da aula de {cues['duration']} s")
        saida.append({"peca_id": p["peca_id"], "nome": p.get("nome"), "video": pasta / final, "ini": ini, "fim": fim,
                      "legendas": legendas, "trim": round(ini * FPS), "frames": round((fim - ini) * FPS)})
    return saida


def _juntar(partes: list[dict[str, Any]], destino: Path) -> None:
    """Corta os mesmos quadros de cada parte (trim, frames) e junta vídeo e áudio num MP4 só."""
    entradas, filtros, rotulos = [], [], []
    for i, p in enumerate(partes):
        entradas += ["-i", str(p["video"])]
        a, b = p["trim"], p["trim"] + p["frames"]
        filtros.append(f"[{i}:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,fps={FPS}[v{i}]")
        filtros.append(f"[{i}:a]atrim=start={a / FPS:.6f}:end={b / FPS:.6f},asetpts=PTS-STARTPTS[a{i}]")
        rotulos.append(f"[v{i}][a{i}]")
    filtros.append("".join(rotulos) + f"concat=n={len(partes)}:v=1:a=1[v][a]")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", ";".join(filtros),
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", CRF, "-preset", PRESET,
                        "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", AUDIO_BITRATE, str(destino)],
                       capture_output=True, text=True)
    if r.returncode:
        raise ffmpeg.ErroFfmpeg(f"ffmpeg não juntou as partes:\n{r.stderr[-CAUDA_ERRO:]}")


# ---------------------------------------------------------------- compilação


def compilar(
    raiz: Path | str,
    partes: Any,
    *,
    titulo: str,
    formato: str = "16:9",
    serie: str | None = None,
    pack: str = "nucleo",
    slug: str | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Compila as `partes` numa peça `aula` nova: `saida/aula-<formato>.mp4` e `.srt`."""
    raiz = Path(raiz)
    resolvidas = ler_partes(raiz, partes, formato)
    caps, total = legendas_compiladas(resolvidas)
    dims = {(ffmpeg.sondar(p["video"])["largura"], ffmpeg.sondar(p["video"])["altura"]) for p in resolvidas}
    if len(dims) != 1:
        raise ErroCompilar("partes", f"as partes têm tamanhos diferentes: {sorted(dims)}")

    peca = modelo.criar(raiz, tipo="aula", titulo=titulo, formatos=[formato], pack=pack, slug=slug, status="roteiro",
                        serie=serie, origem=origem, agente=agente)
    peca_id = peca["peca_id"]
    pasta = modelo.pasta(raiz, peca_id)
    (pasta / "saida").mkdir(exist_ok=True)
    (pasta / "midia").mkdir(exist_ok=True)
    video = pasta / "saida" / f"aula-{formato.replace(':', 'x')}.mp4"
    arq_srt = pasta / "saida" / f"aula-{formato.replace(':', 'x')}.srt"
    arq_partes = pasta / "midia" / "partes.json"
    inicio = time.monotonic()
    trabalho = Path(tempfile.mkdtemp(prefix=f"{peca_id}-compilar-"))
    try:
        arquivos.gravar_json(arq_partes, [{"peca_id": p["peca_id"], "ini": p["ini"], "fim": p["fim"], "nome": p["nome"],
                                          "de_quadro": p["trim"], "quadros": p["frames"]} for p in resolvidas])
        srt.gravar_srt(caps, arq_srt)
        bruto = trabalho / "bruto.mp4"
        _juntar(resolvidas, bruto)
        ffmpeg.normalizar_audio(bruto, video)
        resultado = verificar.verificar(video, PERFIL, verificar.Artefatos(srt=arq_srt))
        if not resultado["aprovado"]:
            raise ErroCompilar("partes", "a compilação reprovou no perfil aula: "
                               + "; ".join(a["detalhe"] for a in resultado["achados"]))
    except Exception as erro:  # noqa: BLE001 — falha vira evento, e sobe
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, detalhe=f"compilar: {type(erro).__name__}: {erro}"[:500],
                         segundos=round(time.monotonic() - inicio, 3))
        raise
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    segundos = round(time.monotonic() - inicio, 3)
    for caminho, papel, fmt in ((video, "final", formato), (arq_srt, "srt", formato), (arq_partes, "roteiro", None)):
        modelo.registrar_arquivo(raiz, peca_id, caminho, papel=papel, formato=fmt)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["compoe"] = list(dict.fromkeys(p["peca_id"] for p in resolvidas))

    modelo._atualizar(raiz, peca_id, aplicar)
    modelo.registrar_producao(raiz, peca_id, capacidades=["editar_video", "legendar"],
                              provedores={"editar_video": "ffmpeg", "legendar": "local"}, segundos=segundos)
    duracao = round(total / FPS, 3)
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade="editar_video", provedor="ffmpeg",
                     detalhe=f"compilação de {len(resolvidas)} partes, {str(round(duracao, 1)).replace('.', ',')} s, "
                             f"aprovada no perfil {PERFIL}",
                     arquivos=[video, arq_srt, arq_partes], segundos=segundos)
    final = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final["status"],
        "pasta": relativo(raiz, pasta),
        "video": relativo(raiz, video),
        "srt": relativo(raiz, arq_srt),
        "duracao": duracao,
        "quadros": total,
        "legendas": len(caps),
        "compoe": final["compoe"],
        "partes": [{"peca_id": p["peca_id"], "nome": p["nome"], "ini": p["ini"], "fim": p["fim"]} for p in resolvidas],
        "verificacao": resultado,
        "segundos": segundos,
    }

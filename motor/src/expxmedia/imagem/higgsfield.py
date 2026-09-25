"""Higgsfield pelo CLI: `video_ia` (texto/imagem → vídeo curto) e `rosto_ia` (porta-voz em cena nova).

Regras (D-27, base/cli-higgsfield.md, base/abertura-higgsfield.md):

- Antes de tudo, `ambiente.verificar` confere a capacidade (CLI no PATH e login feito, com
  `higgsfield account status`); `rosto_ia` é conferida **para o porta-voz**, que precisa ter
  `rosto_ia.id` preenchido na Alma. Desligada, levanta `ErroCapacidade` e o CLI não é chamado.
- **`model get <modelo> --json` antes de cada `generate create`**: os parâmetros mudam no servidor
  sem versão do CLI. Parâmetro pedido que o esquema não declara é recusado antes de gerar
  (`parametro_fora_do_esquema`), valor fora do `enum` também (`valor_fora_do_esquema`), e
  obrigatório ausente idem. Os padrões do motor entram só se o esquema do modelo os aceita.
- O CLI roda sem shell; a saída **nunca** é impressa nem gravada: traz URL assinada, que é
  credencial de leitura (origem: Instragram-Videos/pipeline/abertura.py:102-124). Erro do CLI sai
  numa linha, com URLs trocadas por `<url-omitida>`. Do job guarda-se só o id.
- `generate_audio` vem ligado por padrão nos modelos de vídeo: o motor manda `false` quando o
  esquema tem o parâmetro e quem chamou não decidiu (clipe com áudio mexe no loudness da peça).
- `cota`: fábrica opcional de gerenciador de contexto por provedor (`cota.Cota(raiz).consumir`).

Uso:

    from expxmedia.imagem import higgsfield
    higgsfield.gerar_video(raiz, "prompt em inglês", "pecas/.../abertura_bruta.mp4",
                           start_image="pecas/.../quadro.png")
    higgsfield.gerar_rosto(raiz, "ana-souza", "standing behind the counter", "pecas/.../rosto.png")
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import requests
from PIL import Image, UnidentifiedImageError

from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroHiggsfield",
    "esquema",
    "validar_parametros",
    "gerar_video",
    "gerar_rosto",
    "MODELO_VIDEO",
    "MODELO_ROSTO",
    "PREAMBULO_ROSTO",
]

EXECUTAVEL = "higgsfield"
PROVEDOR = "higgsfield"

# Vídeo: o que a abertura da origem mediu e usa (tipo "objeto").
MODELO_VIDEO = "seedance_2_0"  # origem: Instragram-Videos/aberturas.json:20
PADROES_VIDEO: dict[str, Any] = {
    "mode": "std",  # origem: Instragram-Videos/aberturas.json:22
    "duration": 4,  # origem: Instragram-Videos/aberturas.json:24 (o modelo não gera abaixo de 4 s)
    "aspect_ratio": "9:16",  # origem: Instragram-Videos/aberturas.json:25
    "resolution": "720p",  # origem: Instragram-Videos/aberturas.json:26
}
ESPERA_VIDEO = "20m"  # origem: Instragram-Videos/pipeline/abertura.py:214
TIMEOUT_VIDEO = 1800  # s; origem: Instragram-Videos/pipeline/abertura.py:106

# Rosto: Soul 2.0 com o id do porta-voz (antes, o Soul treinado do dono da origem).
MODELO_ROSTO = "text2image_soul_v2"  # origem: Instagram-Carrosseis/galeria/soul.py:22
PADROES_ROSTO: dict[str, Any] = {
    "aspect_ratio": "3:4",  # origem: Instagram-Carrosseis/galeria/soul.py:23
    "quality": "2k",  # origem: Instagram-Carrosseis/galeria/soul.py:25
}
ESPERA_ROSTO = "10m"  # origem: Instagram-Carrosseis/galeria/soul.py:26
TIMEOUT_ROSTO = 900  # s; origem: Instagram-Carrosseis/galeria/soul.py:60
PREAMBULO_ROSTO = (  # origem: Instagram-Carrosseis/galeria/soul.py:129-130
    "photorealistic studio portrait photograph of the character, "
    "sharp focus, 85mm lens, natural skin texture, clean composition. "
)
PROMPT_MAXIMO = 900  # caracteres; origem: Instagram-Carrosseis/galeria/soul.py:138

TIMEOUT_ESQUEMA = 60  # s
TIMEOUT_DOWNLOAD = 300  # s; origem: Instragram-Videos/pipeline/abertura.py:227
VARREDURA_MAXIMA = 5000  # nós; origem: Instragram-Videos/pipeline/abertura.py:134
ERRO_MAXIMO = 700  # caracteres; origem: Instragram-Videos/pipeline/abertura.py:124
SUFIXOS_VIDEO = (".mp4", ".webm", ".mov")
SUFIXOS_IMAGEM = (".jpg", ".jpeg", ".png", ".webp")

# flags do CLI que não são parâmetro do modelo
_FLAGS_DO_CLI = ("wait", "json", "wait_timeout", "wait_interval")

Cota = Callable[[str], AbstractContextManager[Any]]


class ErroHiggsfield(RuntimeError):
    """Falha do CLI ou parâmetro recusado, com `codigo` estável. Nunca traz URL assinada."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


# ---------- CLI ----------

def _cli(executavel: str, *args: str, timeout: float) -> Any:
    try:
        r = subprocess.run([executavel, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ErroHiggsfield("tempo_esgotado", f"`{EXECUTAVEL} {args[0]}` passou de {timeout:.0f} s") from None
    except OSError as erro:
        raise ErroHiggsfield("cli_ausente", f"não foi possível rodar {EXECUTAVEL}: {type(erro).__name__}") from None
    saida = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        if "Not authenticated" in saida or "Session expired" in saida:
            raise ErroHiggsfield("sem_login", f"o CLI {EXECUTAVEL} não está autenticado: rode `{EXECUTAVEL} auth login`.")
        motivo = " ".join(l.strip() for l in saida.strip().splitlines() if l.strip())
        motivo = re.sub(r"https?://\S+", "<url-omitida>", motivo)[:ERRO_MAXIMO]
        raise ErroHiggsfield("cli_falhou", f"`{EXECUTAVEL} {' '.join(args[:2])}` falhou (código {r.returncode}): {motivo or 'sem mensagem'}")
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise ErroHiggsfield("resposta_invalida", f"`{EXECUTAVEL} {' '.join(args[:2])}` não devolveu JSON") from None


def _executavel() -> str:
    caminho = shutil.which(EXECUTAVEL)
    if caminho is None:
        raise ErroCapacidade(f"o CLI {EXECUTAVEL} não está no PATH")
    return caminho


def esquema(modelo: str, *, executavel: str | None = None, timeout: float = TIMEOUT_ESQUEMA) -> dict[str, Any]:
    """Esquema do modelo, direto do servidor: `higgsfield model get <modelo> --json`."""
    dados = _cli(executavel or _executavel(), "model", "get", modelo, "--json", timeout=timeout)
    if not isinstance(dados, dict) or not isinstance(dados.get("params"), list):
        raise ErroHiggsfield("resposta_invalida", f"`{EXECUTAVEL} model get {modelo}` sem a lista de params")
    return dados


def _nome(chave: str) -> str:
    return str(chave).strip().lstrip("-").replace("-", "_")


def validar_parametros(esquema_modelo: Mapping[str, Any], parametros: Mapping[str, Any]) -> dict[str, Any]:
    """Parâmetros com nome normalizado (`aspect-ratio` → `aspect_ratio`), conferidos contra o esquema.

    Recusa nome que o esquema não declara, valor fora do `enum` e obrigatório ausente.
    """
    declarados = {p["name"]: p for p in esquema_modelo.get("params") or [] if isinstance(p, dict) and "name" in p}
    normais = {_nome(k): v for k, v in parametros.items()}
    fora = sorted(n for n in normais if n not in declarados)
    if fora:
        raise ErroHiggsfield(
            "parametro_fora_do_esquema",
            f"{esquema_modelo.get('job_type', 'o modelo')} não declara {', '.join(fora)} "
            f"(aceita: {', '.join(sorted(declarados))})",
        )
    invalidos = [
        f"{n}={v}" for n, v in normais.items()
        if declarados[n].get("enum") and _texto(v) not in [str(e) for e in declarados[n]["enum"]]
    ]
    if invalidos:
        raise ErroHiggsfield("valor_fora_do_esquema", f"valores fora do esquema: {', '.join(invalidos)}")
    faltam = sorted(n for n, p in declarados.items() if p.get("required") and normais.get(n) in (None, ""))
    if faltam:
        raise ErroHiggsfield("parametro_obrigatorio", f"faltam parâmetros obrigatórios: {', '.join(faltam)}")
    return normais


def _texto(valor: Any) -> str:
    return str(valor).lower() if isinstance(valor, bool) else str(valor)


def _padroes_aceitos(esquema_modelo: Mapping[str, Any], padroes: Mapping[str, Any]) -> dict[str, Any]:
    """Os padrões do motor que o esquema deste modelo declara, com valor aceito pelo `enum`."""
    declarados = {p["name"]: p for p in esquema_modelo.get("params") or [] if isinstance(p, dict) and "name" in p}
    aceitos = {}
    for nome, valor in padroes.items():
        p = declarados.get(nome)
        if p is None:
            continue
        if p.get("enum") and _texto(valor) not in [str(e) for e in p["enum"]]:
            continue
        aceitos[nome] = valor
    return aceitos


def _argumentos(parametros: Mapping[str, Any]) -> list[str]:
    args: list[str] = []
    for nome, valor in parametros.items():
        if valor is None or nome in _FLAGS_DO_CLI:
            continue
        args += [f"--{nome.replace('_', '-')}", _texto(valor)]
    return args


def _achar_url(resposta: Any, sufixos: tuple[str, ...]) -> str | None:
    """A saída do CLI muda de forma entre versões: a primeira URL com sufixo de mídia.

    origem: Instragram-Videos/pipeline/abertura.py:131-148 (varredura limitada a 5000 nós).
    """
    pilha, vistos = [resposta], 0
    while pilha and vistos < VARREDURA_MAXIMA:
        vistos += 1
        atual = pilha.pop()
        if isinstance(atual, str) and atual.startswith(("http://", "https://")):
            if any(s in atual.lower().split("?")[0] for s in sufixos):
                return atual
        elif isinstance(atual, dict):
            pilha.extend(atual.values())
        elif isinstance(atual, list):
            pilha.extend(atual)
    return None


def _baixar(url: str) -> bytes:
    try:
        r = requests.get(url, timeout=TIMEOUT_DOWNLOAD)
        r.raise_for_status()
    except requests.RequestException as erro:
        raise ErroHiggsfield("download_falhou", f"não deu para baixar o resultado: {type(erro).__name__}") from None
    return r.content


def _gravar(destino: Path, dados: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    temporario.write_bytes(dados)
    temporario.replace(destino)


def _verificar(raiz: Path, capacidade: str, porta_voz: str | None = None) -> None:
    consulta = Verificador(raiz).verificar(capacidade, porta_voz)
    if not consulta["habilitada"] or consulta["provedor"] != PROVEDOR:
        raise ErroCapacidade(
            f"{capacidade} não está habilitada pelo {PROVEDOR}. {consulta['como_habilitar'] or ''}".strip()
        )


def _gerar(
    modelo: str,
    pedidos: Mapping[str, Any],
    padroes: Mapping[str, Any],
    espera: str,
    timeout: float,
    sufixos: tuple[str, ...],
    cota: Cota | None,
) -> tuple[bytes, str | None, dict[str, Any]]:
    exe = _executavel()
    esquema_modelo = esquema(modelo, executavel=exe)  # sempre antes do generate (D-27)
    parametros = {**_padroes_aceitos(esquema_modelo, padroes), **validar_parametros(esquema_modelo, pedidos)}
    parametros = validar_parametros(esquema_modelo, parametros)
    args = ["generate", "create", modelo, *_argumentos(parametros), "--wait", "--wait-timeout", espera, "--json"]
    guarda = cota(PROVEDOR) if cota is not None else contextlib.nullcontext()
    with guarda:
        resposta = _cli(exe, *args, timeout=timeout)
        url = _achar_url(resposta, sufixos)
        if not url:
            raise ErroHiggsfield("sem_resultado", f"o job de {modelo} terminou sem URL de resultado")
        corpo = resposta[0] if isinstance(resposta, list) and resposta else resposta
        job = corpo.get("id") if isinstance(corpo, dict) else None
        dados = _baixar(url)
    return dados, job, parametros


def _sem_midia(parametros: Mapping[str, Any]) -> dict[str, Any]:
    """Parâmetros para registrar na peça: caminhos de mídia viram só o nome do arquivo."""
    return {k: (Path(v).name if k in ("start_image", "end_image") else v) for k, v in parametros.items() if k != "prompt"}


# ---------- capacidades ----------

def gerar_video(
    raiz: Path | str,
    prompt: str,
    saida: str | Path,
    *,
    modelo: str = MODELO_VIDEO,
    parametros: Mapping[str, Any] | None = None,
    start_image: str | Path | None = None,
    end_image: str | Path | None = None,
    cota: Cota | None = None,
) -> dict[str, Any]:
    """`video_ia`: gera o clipe e grava em `saida` (relativo à raiz). Prompt em inglês.

    `start_image`/`end_image`: imagens da instalação (caminho relativo) enviadas por upload do CLI.
    """
    raiz = Path(raiz)
    if not (prompt or "").strip():
        raise ValueError("prompt vazio")
    destino = instalacao.absoluto(raiz, saida)
    _verificar(raiz, "video_ia")
    pedidos: dict[str, Any] = {**(parametros or {}), "prompt": prompt.strip()}
    for nome, valor in (("start_image", start_image), ("end_image", end_image)):
        if valor is not None:
            pedidos[nome] = str(instalacao.absoluto(raiz, valor))
    # padrão que o esquema do modelo escolhido não aceita é descartado (ex.: mode std no seedance_2_5)
    padroes = {**PADROES_VIDEO, "generate_audio": False}
    dados, job, usados = _gerar(modelo, pedidos, padroes, ESPERA_VIDEO, TIMEOUT_VIDEO, SUFIXOS_VIDEO, cota)
    _gravar(destino, dados)
    return {
        "caminho": instalacao.relativo(raiz, destino),
        "provedor": PROVEDOR,
        "capacidade": "video_ia",
        "modelo": modelo,
        "job": job,
        "parametros": _sem_midia(usados),
    }


def gerar_rosto(
    raiz: Path | str,
    porta_voz: str,
    prompt: str,
    saida: str | Path,
    *,
    modelo: str = MODELO_ROSTO,
    parametros: Mapping[str, Any] | None = None,
    preambulo: str = PREAMBULO_ROSTO,
    cota: Cota | None = None,
) -> dict[str, Any]:
    """`rosto_ia`: o porta-voz numa cena nova, pelo id `rosto_ia.id` dele na Alma. Grava PNG em `saida`.

    A semelhança vem do id treinado, nunca da descrição: o prompt fala da situação, curto e em
    inglês, e não descreve a aparência da pessoa.
    """
    raiz = Path(raiz)
    if not (prompt or "").strip():
        raise ValueError("prompt vazio")
    destino = instalacao.absoluto(raiz, saida)
    _verificar(raiz, "rosto_ia", porta_voz)
    rosto_id = _rosto_id(raiz, porta_voz)
    texto = (preambulo + " ".join(prompt.split()))[:PROMPT_MAXIMO]
    pedidos = {**(parametros or {}), "prompt": texto, "custom_reference_id": rosto_id}
    dados, job, usados = _gerar(modelo, pedidos, PADROES_ROSTO, ESPERA_ROSTO, TIMEOUT_ROSTO, SUFIXOS_IMAGEM, cota)
    try:
        with Image.open(io.BytesIO(dados)) as img:
            img.load()
            convertida = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ErroHiggsfield("imagem_invalida", "o resultado do rosto não abriu como imagem") from None
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    convertida.save(temporario, "PNG")
    temporario.replace(destino)
    return {
        "caminho": instalacao.relativo(raiz, destino),
        "provedor": PROVEDOR,
        "capacidade": "rosto_ia",
        "modelo": modelo,
        "porta_voz": porta_voz,
        "job": job,
        "parametros": _sem_midia(usados),
    }


def _rosto_id(raiz: Path, porta_voz: str) -> str:
    alma = arquivos.ler_json(raiz / "alma" / "alma.json")
    for registro in alma.get("porta_vozes") or []:
        if isinstance(registro, dict) and registro.get("id") == porta_voz:
            valor = (registro.get("rosto_ia") or {}).get("id")
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
    raise ErroCapacidade(f"rosto_ia: o porta-voz {porta_voz} não tem rosto_ia.id na Alma")

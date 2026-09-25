"""Adaptador da Graph API da Meta: provedor `meta_graph` de `publicar` e `agendar` (Instagram).

Nenhuma origem publica pela Graph; o padrão de cliente vem de `ExpxMeta/meta/client.py` (token
na query do GET e no corpo do POST, `repr` mascarado, erro 190 sem retentativa) e o fluxo, da
documentação oficial resumida em base/publicar-meta-graph.md:

1. **antes de qualquer chamada**, valida: só JPEG entra (PNG é convertido por
   `video.ffmpeg.png_para_jpeg`), proporção de imagem de 4:5 a 1.91:1 (post 9:16 é recusado com
   achado `proporcao`), carrossel de 2 a 10 itens, legenda até 2200 caracteres e 30 hashtags;
2. consulta `content_publishing_limit` e recusa, sem criar contêiner, quando o uso das últimas
   24 h chegou a 50 (D-44: o menor entre 50 e a cota informada; a documentação diverge entre 50 e
   100);
3. expõe a mídia pelo túnel (`publicar.tunel`) e **mantém o túnel aberto até publicar**: a Graph
   baixa durante o processamento do contêiner;
4. cria os contêineres (filhos com `is_carousel_item`, `image_url` ou `media_type=VIDEO` +
   `video_url`; pai `CAROUSEL` com `children`; reel `REELS` + `video_url`), consulta
   `status_code` até `FINISHED` (1 vez por minuto, no máximo 5 minutos — guia Content Publishing)
   e só então chama `media_publish`. `ERROR`/`EXPIRED` param antes de publicar;
5. nenhum POST é retentado (D-29): `media_publish` com 5xx fica `incerto` e a peça volta para a
   pessoa conferir. Depois, lê o `permalink` da mídia (falha aqui não desfaz a publicação).

`agendar` por este provedor não chama nada: a publicação fica `agendada` na peça e o agendador
local publica no horário (CONTRATO-capacidades, "O agendador local"). Facebook (Página) não é
suportado por este adaptador.

O token nunca aparece em `repr`, erro ou payload devolvido (M14): erro 190 cita o **nome**
`META_GRAPH_TOKEN`.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from expxmedia.publicar import base
from expxmedia.publicar import tunel as _tunel
from expxmedia.video import ffmpeg

__all__ = ["MetaGraph", "PROVEDOR", "VERSAO_API", "LIMITE_24H"]

PROVEDOR = "meta_graph"
ENV_TOKEN, ENV_IG = "META_GRAPH_TOKEN", "META_IG_USER_ID"
VERSAO_API = "v23.0"  # origem: Instragram-Videos/pipeline/insights.py:37 (v21.0 do ExpxMeta expira antes, 2027-01-21)
URL_BASE = f"https://graph.facebook.com/{VERSAO_API}"  # origem: ExpxMeta/meta/client.py:36
TIMEOUT = 30  # s; origem: ExpxMeta/meta/client.py:70
LIMITE_24H = 50  # D-44; referência content_publishing_limit (quota_total 50)
ITENS_MIN, ITENS_MAX = 2, 10  # referência IG User Media; erro 100/2207028
PROPORCAO_MIN, PROPORCAO_MAX = 4 / 5, 1.91  # referência IG User Media; erro 36003/2207009
LEGENDA_MAX = 2200  # referência IG User Media
HASHTAGS_MAX = 30  # referência IG User Media
IMAGEM_MAX_BYTES = 8 * 1024 * 1024  # 8 MiB; referência IG User Media; erro 36000/2207004
INTERVALO_STATUS = 60  # s; guia Content Publishing: "once per minute"
CONSULTAS_STATUS = 6  # imediata + 1 por minuto por 5 minutos ("for no more than 5 minutes")
_TOLERANCIA = 1e-9
_CODIGOS_TOKEN = {190}  # origem: ExpxMeta/meta/client.py:100
_LIMITE_DIARIO = (9, 2207042)  # referência Error Codes


class MetaGraph:
    """Adaptador do provedor `meta_graph` para `publicar.base`."""

    provedor = PROVEDOR

    def __init__(self, token: str, ig_user_id: str, *, url_base: str = URL_BASE,
                 abrir_tunel: Callable[[list[Path]], Any] | None = None,
                 intervalo_status: float = INTERVALO_STATUS, consultas_status: int = CONSULTAS_STATUS,
                 pausar: Callable[[float], None] = time.sleep, timeout: float = TIMEOUT) -> None:
        self._token = token
        self.ig_user_id = ig_user_id
        self.url_base = url_base.rstrip("/")
        self._abrir_tunel = abrir_tunel or _tunel.abrir
        self._intervalo = intervalo_status
        self._consultas = consultas_status
        self._pausar = pausar
        self._timeout = timeout

    @classmethod
    def da_instalacao(cls, raiz: Path | str, env: Mapping[str, str], **opcoes: Any) -> "MetaGraph":
        faltam = [n for n in (ENV_TOKEN, ENV_IG) if not (env.get(n) or "").strip()]
        if faltam:
            raise base.ErroPublicacao("sem_credenciais", f"faltam no .env: {', '.join(faltam)}")
        return cls(env[ENV_TOKEN].strip(), env[ENV_IG].strip(), **opcoes)

    def __repr__(self) -> str:
        return f"MetaGraph(url_base={self.url_base!r}, ig_user_id={self.ig_user_id!r}, token='***')"

    # ------------------------------------------------------------ validação (sem rede)

    def validar(self, pedido: base.Pedido) -> list[dict[str, str]]:
        achados: list[dict[str, str]] = []

        def achar(codigo: str, mensagem: str) -> None:
            achados.append({"codigo": codigo, "mensagem": mensagem})

        fora = [c for c in pedido.canais if c != "instagram"]
        if fora:
            achar("canal", f"o adaptador da Graph publica só no instagram, não em {', '.join(fora)}")
        if pedido.automacao is not None:
            achar("automacao", "automação de DM não existe pela Graph; use o expxflow")
        itens = base.midias(pedido)
        if not itens:
            achar("midia", "a peça não tem mídia para publicar (slides ou arquivo final)")
        if len(itens) > 1 and not ITENS_MIN <= len(itens) <= ITENS_MAX:
            achar("itens", f"carrossel com {len(itens)} itens; a Graph aceita de {ITENS_MIN} a {ITENS_MAX}")
        for item in itens:
            caminho = item["caminho"]
            if not caminho.is_file():
                achar("arquivo", f"arquivo da peça não encontrado: {caminho.name}")
                continue
            if item["midia"] != "imagem":
                continue
            try:
                with Image.open(caminho) as img:
                    largura, altura = img.size
            except OSError:
                achar("tipo", f"{caminho.name} não é uma imagem legível")
                continue
            proporcao = largura / altura
            if not PROPORCAO_MIN - _TOLERANCIA <= proporcao <= PROPORCAO_MAX + _TOLERANCIA:
                achar("proporcao", f"{caminho.name} tem {largura}x{altura} (proporção {proporcao:.3f}); a Graph "
                                   "aceita imagem de 4:5 (0,8) a 1.91:1")
        texto = base.legenda(pedido)
        if len(texto) > LEGENDA_MAX:
            achar("legenda", f"legenda com {len(texto)} caracteres; o máximo é {LEGENDA_MAX}")
        if base.contar_hashtags(texto) > HASHTAGS_MAX:
            achar("legenda", f"legenda com mais de {HASHTAGS_MAX} hashtags")
        return achados

    # ------------------------------------------------------------ envio

    def enviar(self, pedido: base.Pedido) -> base.Resultado:
        itens = base.midias(pedido)
        texto = base.legenda(pedido)
        plano = {"provedor": PROVEDOR, "tipo": _tipo(pedido, itens), "itens": [i["caminho"].name for i in itens],
                 "legenda": texto}
        if pedido.agendada_para:
            # a Graph não agenda: o agendador local publica no horário
            return base.Resultado(
                canais={"instagram": base.ResultadoCanal(estado="agendada")}, payload=plano,
                detalhe="agendada para o agendador local",
            )
        if pedido.dry_run:
            return base.Resultado(payload=plano, detalhe="dry-run: nada enviado")

        self._conferir_limite()
        pasta = Path(tempfile.mkdtemp(prefix="expxmedia-graph-"))
        try:
            expostos = [self._preparar(item, pasta) for item in itens]
            aberto = self._abrir_tunel([e["caminho"] for e in expostos])
            try:
                urls = [aberto.url_de(e["caminho"]) for e in expostos]
                conteiner = self._criar(plano["tipo"], expostos, urls, texto)
                id_midia = self._publicar(conteiner)
            finally:
                aberto.fechar()
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
        permalink = self._permalink(id_midia)
        return base.Resultado(
            canais={"instagram": base.ResultadoCanal(estado="publicada", id_externo=id_midia, url=permalink)},
            payload=plano, detalhe=f"media_publish {id_midia}",
        )

    def _preparar(self, item: dict[str, Any], pasta: Path) -> dict[str, Any]:
        """Imagem vira JPEG sRGB (a Graph só aceita JPEG); vídeo segue como está."""
        caminho = item["caminho"]
        if item["midia"] != "imagem":
            return {"caminho": caminho, "midia": item["midia"]}
        destino = pasta / f"{len(list(pasta.iterdir())):02d}-{caminho.stem}.jpg"
        ffmpeg.png_para_jpeg(caminho, destino)
        if destino.stat().st_size > IMAGEM_MAX_BYTES:
            raise base.ErroEnvio("imagem_grande", f"{caminho.name} passa de 8 MiB em JPEG; a Graph recusa")
        return {"caminho": destino, "midia": "imagem"}

    def _conferir_limite(self) -> None:
        corpo = self._get(f"{self.ig_user_id}/content_publishing_limit", {"fields": "quota_usage,config"})
        dados = (corpo.get("data") or [{}])[0] if isinstance(corpo, dict) else {}
        uso = dados.get("quota_usage")
        total = (dados.get("config") or {}).get("quota_total")
        teto = min(LIMITE_24H, int(total)) if isinstance(total, (int, float)) and total > 0 else LIMITE_24H
        if not isinstance(uso, (int, float)):
            raise base.ErroEnvio("limite_desconhecido", "content_publishing_limit não informou quota_usage; "
                                                        "nada foi publicado")
        if uso >= teto:
            raise base.ErroEnvio("limite_24h", f"a conta já publicou {int(uso)} vezes nas últimas 24 h (limite "
                                               f"{teto}); nada foi criado. Tente depois que a janela andar.")

    def _criar(self, tipo: str, expostos: list[dict[str, Any]], urls: list[str], texto: str) -> str:
        caminho = f"{self.ig_user_id}/media"
        if tipo == "carrossel":
            filhos = []
            for exposto, url in zip(expostos, urls):
                corpo: dict[str, Any] = {"is_carousel_item": True}
                if exposto["midia"] == "imagem":
                    corpo["image_url"] = url
                else:
                    corpo.update(media_type="VIDEO", video_url=url)
                filhos.append(self._post(caminho, corpo))
            for filho in filhos:
                self._esperar(filho)
            pai = self._post(caminho, {"media_type": "CAROUSEL", "children": ",".join(filhos), "caption": texto})
            self._esperar(pai)
            return pai
        if tipo == "reel":
            conteiner = self._post(caminho, {"media_type": "REELS", "video_url": urls[0], "caption": texto,
                                             "share_to_feed": True})
        else:
            conteiner = self._post(caminho, {"image_url": urls[0], "caption": texto})
        self._esperar(conteiner)
        return conteiner

    def _esperar(self, conteiner: str) -> None:
        for consulta in range(self._consultas):
            corpo = self._get(conteiner, {"fields": "status_code,status"})
            status = str(corpo.get("status_code", "")).upper() if isinstance(corpo, dict) else ""
            if status in ("FINISHED", "PUBLISHED"):
                return
            if status in ("ERROR", "EXPIRED"):
                raise base.ErroEnvio(f"conteiner_{status.lower()}",
                                     f"o contêiner {conteiner} ficou {status}: {corpo.get('status') or 'sem detalhe'}; "
                                     "nada foi publicado")
            if consulta < self._consultas - 1:
                self._pausar(self._intervalo)
        raise base.ErroEnvio("conteiner_nao_pronto", f"o contêiner {conteiner} não ficou FINISHED no tempo da consulta; "
                                                      "nada foi publicado")

    def _publicar(self, conteiner: str) -> str:
        corpo = self._post(f"{self.ig_user_id}/media_publish", {"creation_id": conteiner}, incerto_sem_id=True)
        return corpo

    def _permalink(self, id_midia: str) -> str | None:
        try:
            corpo = self._get(id_midia, {"fields": "permalink"})
        except base.ErroEnvio:
            return None
        return corpo.get("permalink") if isinstance(corpo, dict) else None

    # ------------------------------------------------------------ HTTP

    def _post(self, caminho: str, corpo: dict[str, Any], *, incerto_sem_id: bool = False) -> str:
        """POST único (D-29); devolve o `id` da resposta."""
        try:
            resposta = base.post_json(f"{self.url_base}/{caminho}", {**corpo, "access_token": self._token},
                                      timeout=self._timeout)
        except base.ErroEnvio as erro:
            raise _traduzir(erro) from None
        ident = resposta.get("id") if isinstance(resposta, dict) else None
        if not ident:
            raise base.ErroEnvio("resposta_sem_id", f"a Graph não devolveu id em {caminho.rsplit('/', 1)[-1]}",
                                 incerto=incerto_sem_id)
        return str(ident)

    def _get(self, caminho: str, parametros: dict[str, Any]) -> Any:
        try:
            resposta = requests.get(f"{self.url_base}/{caminho}", params={**parametros, "access_token": self._token},
                                    timeout=self._timeout)
        except requests.RequestException as erro:  # a mensagem traria a URL com o token: não repassar
            raise base.ErroEnvio("sem_resposta", f"a Graph não respondeu ({type(erro).__name__})") from None
        try:
            corpo = resposta.json()
        except ValueError:
            corpo = {}
        if 200 <= resposta.status_code < 300:
            return corpo
        raise _traduzir(base.ErroEnvio(f"http_{resposta.status_code}",
                                       f"a Graph respondeu HTTP {resposta.status_code}: {_mensagem(corpo)}",
                                       status_http=resposta.status_code, corpo=corpo))


def _tipo(pedido: base.Pedido, itens: list[dict[str, Any]]) -> str:
    if len(itens) > 1:
        return "carrossel"
    if pedido.peca["tipo"] == "reel" or (itens and itens[0]["midia"] == "video"):
        return "reel"
    return "imagem"


def _mensagem(corpo: Any) -> str:
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    if isinstance(erro, dict):
        return str(erro.get("message") or "sem mensagem")[:base.CAUDA_ERRO]
    return "sem corpo de erro"


def _traduzir(erro: base.ErroEnvio) -> base.ErroEnvio:
    """Códigos da Graph: 190/OAuthException → token; 9/2207042 → limite diário (sem retentar)."""
    info = (erro.corpo or {}).get("error") if isinstance(erro.corpo, dict) else None
    if not isinstance(info, dict):
        return erro
    codigo, sub, tipo = info.get("code"), info.get("error_subcode"), info.get("type")
    if codigo in _CODIGOS_TOKEN or tipo == "OAuthException":
        return base.ErroEnvio("token", f"a Graph recusou {ENV_TOKEN} (código {codigo}); gere um token de longa "
                                       f"duração e atualize o .env. O valor não se imprime.",
                              status_http=erro.status_http, incerto=False, corpo=erro.corpo)
    if (codigo, sub) == _LIMITE_DIARIO:
        return base.ErroEnvio("limite_24h", "limite diário de publicação da conta atingido (9/2207042); tente "
                                            "no dia seguinte", status_http=erro.status_http, incerto=False,
                              corpo=erro.corpo)
    return erro

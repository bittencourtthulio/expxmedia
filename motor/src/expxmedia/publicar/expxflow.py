"""Adaptador do Expx Flow: provedor `expxflow` de `publicar`, `agendar` e `automacao_dm`.

Porta de `Instagram-Carrosseis/publicar/publicar.py` (upload, carrossel, post único, dry-run,
Idempotency-Key, automação) e `Instragram-Videos/pipeline/publish.py` + `expxflow.py` (reel pelo
`post-api` com a mídia exposta pelo túnel). Referência da API: base/publicar-expxflow.md.

- Credenciais e endereço só do `.env` da instalação: `EXPXFLOW_API_KEY` (cabeçalho `X-API-Key`),
  `EXPXFLOW_CLIENT_ID` e `EXPXFLOW_BASE_URL`. **Não há URL padrão no código** (D-50): sem a
  variável, o provedor não está satisfeito e a verificação diz como habilitar.
- Imagem sobe pelo `POST /media-upload-api` (multipart `file`); vídeo não sobe (a rota devolve
  415 para `video/mp4`) e vai por URL pública temporária do túnel, aberto só durante a chamada
  de criação: o Expx Flow baixa e rehospeda na hora.
- 2 ou mais mídias → `POST /carousel-api` com `slides[]`; cada filho é `{"image_url"}` ou, para
  slide de vídeo, `{"video_url"}` (D-06: o adaptador envia assumindo aceite; se o servidor
  recusar, a peça registra `publicacao_falhou` com o motivo — PENDENTE-02).
- 1 mídia → `POST /post-api` com `image_url` e `content_type` `image` | `video` | `reel`.
- `scheduled_at` (≥ 3 min no futuro, folga da origem sobre os 2 min da API) ou `publish_now`.
- Automação de DM: bloco `automation` na mesma chamada, ou `vincular_automacao` num post já
  agendado (`POST /instagram-automation-api`).
- 207: criado, mas o agendamento falhou. Se a resposta traz o estado por plataforma, cada canal
  recebe o seu; sem esse detalhe, todos ficam `falhou` com o id do post (que existe no provedor).
- Dry-run monta e valida o corpo com URLs de marcação e não chama nenhuma rota, nem abre túnel.
- Nenhum POST é retentado (D-29); a chave nunca sai em payload devolvido, erro ou repr (M14).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from expxmedia.publicar import base
from expxmedia.publicar import tunel as _tunel

__all__ = ["ExpxFlow", "PROVEDOR", "ROTAS"]

PROVEDOR = "expxflow"
ENV_CHAVE, ENV_CLIENTE, ENV_BASE = "EXPXFLOW_API_KEY", "EXPXFLOW_CLIENT_ID", "EXPXFLOW_BASE_URL"
ROTAS = {
    "upload": "/media-upload-api",
    "carrossel": "/carousel-api",
    "post": "/post-api",
    "automacao": "/instagram-automation-api",
}
PLATAFORMAS = ("instagram", "facebook")  # origem: Instagram-Carrosseis/contratos/carrossel.schema.json:9
SLIDES_MIN, SLIDES_MAX = 2, 20  # origem: Instagram-Carrosseis/contratos/carrossel.schema.json:14-15
ANTECEDENCIA = timedelta(minutes=3)  # origem: Instagram-Carrosseis/publicar/publicar.py:105
TIMEOUT_UPLOAD = 120  # s; origem: Instagram-Carrosseis/publicar/publicar.py:141
TIMEOUT_CRIACAO = 180  # s; origem: Instagram-Carrosseis/publicar/publicar.py:296
TIMEOUT_AUTOMACAO = 120  # s; origem: Instagram-Carrosseis/publicar/publicar.py:330
URL_DRY_RUN = "https://dry-run.invalid/"  # origem: Instagram-Carrosseis/publicar/publicar.py:137
LINK_LABEL_MAX = 20  # origem: Instagram-Carrosseis/contratos/automacao.schema.json:17
MATCH_MODES = ("any", "all", "exact")  # origem: Instagram-Carrosseis/contratos/automacao.schema.json:18
REPLY_MODES = ("fixo", "ia")  # base/publicar-expxflow.md:32 (llms.txt dos vídeos:223)
# Campos do bloco automation; a doc mais nova acrescenta os três public_reply_* finais
# (origem: Instragram-Videos/pipeline/publish.py:151-154).
CAMPOS_AUTOMACAO = (
    "keywords", "mensagem", "link", "link_label", "match_mode", "public_reply_enabled", "public_reply_text",
    "public_reply_mode", "public_reply_prompt", "public_reply_fallback_text",
)
TIPOS_IMAGEM = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                ".gif": "image/gif"}  # origem: base/publicar-expxflow.md:23 (llms (4).txt:139-149)
_OK_PLATAFORMA = {"ok", "success", "scheduled", "agendado", "agendada", "published", "publicado", "publicada"}


class ExpxFlow:
    """Adaptador do provedor `expxflow` para `publicar.base`."""

    provedor = PROVEDOR

    def __init__(self, chave: str, cliente: str, url_base: str, *,
                 abrir_tunel: Callable[[list[Path]], Any] | None = None,
                 agora: Callable[[], datetime] | None = None) -> None:
        if not url_base or not url_base.strip():
            raise base.ErroPublicacao("sem_base_url", f"{ENV_BASE} vazio no .env: o endereço da API do Expx Flow é obrigatório")
        self._chave = chave
        self.cliente = cliente
        self.url_base = url_base.strip().rstrip("/")
        self._abrir_tunel = abrir_tunel or _tunel.abrir
        self._agora = agora or (lambda: datetime.now(timezone.utc))

    @classmethod
    def da_instalacao(cls, raiz: Path | str, env: Mapping[str, str], **opcoes: Any) -> "ExpxFlow":
        faltam = [n for n in (ENV_CHAVE, ENV_CLIENTE, ENV_BASE) if not (env.get(n) or "").strip()]
        if faltam:
            raise base.ErroPublicacao("sem_credenciais", f"faltam no .env: {', '.join(faltam)}")
        return cls(env[ENV_CHAVE].strip(), env[ENV_CLIENTE].strip(), env[ENV_BASE], **opcoes)

    def __repr__(self) -> str:
        return f"ExpxFlow(url_base={self.url_base!r}, chave='***')"

    # ------------------------------------------------------------ validação

    def validar(self, pedido: base.Pedido) -> list[dict[str, str]]:
        achados: list[dict[str, str]] = []

        def achar(codigo: str, mensagem: str) -> None:
            achados.append({"codigo": codigo, "mensagem": mensagem})

        fora = [c for c in pedido.canais if c not in PLATAFORMAS]
        if fora:
            achar("canal", f"o Expx Flow publica em {' e '.join(PLATAFORMAS)}, não em {', '.join(fora)}")
        itens = base.midias(pedido)
        if not itens:
            achar("midia", "a peça não tem mídia para publicar (slides ou arquivo final)")
        for item in itens:
            if not item["caminho"].is_file():
                achar("arquivo", f"arquivo da peça não encontrado: {item['caminho'].name}")
            elif item["midia"] == "imagem" and item["caminho"].suffix.lower() not in TIPOS_IMAGEM:
                achar("tipo", f"{item['caminho'].name}: o upload aceita PNG, JPEG, WebP e GIF")
        if len(itens) > 1 and not SLIDES_MIN <= len(itens) <= SLIDES_MAX:
            achar("itens", f"carrossel com {len(itens)} slides; o Expx Flow aceita de {SLIDES_MIN} a {SLIDES_MAX}")
        if not base.separar_hashtags(base.legenda(pedido))[0]:
            achar("legenda", "legenda vazia; o Expx Flow exige caption")
        if pedido.agendada_para:
            quando = datetime.fromisoformat(pedido.agendada_para)
            if quando <= self._agora() + ANTECEDENCIA:
                achar("antecedencia", f"{pedido.agendada_para} está a menos de 3 minutos; a API exige ao menos 2 "
                                      "minutos no futuro")
        if pedido.automacao is not None:
            for mensagem in _validar_automacao(pedido.automacao):
                achar("automacao", mensagem)
            if "instagram" not in pedido.canais:
                achar("automacao", "a automação de DM exige instagram nos canais")
        return achados

    # ------------------------------------------------------------ envio

    def enviar(self, pedido: base.Pedido) -> base.Resultado:
        itens = base.midias(pedido)
        texto, hashtags = base.separar_hashtags(base.legenda(pedido))
        videos = [i["caminho"] for i in itens if i["midia"] == "video"]

        if pedido.dry_run:
            urls = {i["caminho"]: URL_DRY_RUN + i["caminho"].name for i in itens}
            rota, corpo = self._montar(pedido, itens, urls, texto, hashtags)
            return base.Resultado(payload=self._exibir(rota, corpo, pedido), detalhe="dry-run: nada enviado")

        urls: dict[Path, str] = {}
        for item in itens:
            if item["midia"] == "imagem":
                urls[item["caminho"]] = self._hospedar(item["caminho"])
        aberto = self._abrir_tunel(videos) if videos else None
        try:
            if aberto is not None:
                for video in videos:
                    urls[video] = aberto.url_de(video)
            rota, corpo = self._montar(pedido, itens, urls, texto, hashtags)
            status, resposta = base.post_json_com_status(self.url_base + rota, corpo,
                                                         cabecalhos=self._cabecalhos(pedido), timeout=TIMEOUT_CRIACAO)
        finally:
            if aberto is not None:
                aberto.fechar()
        return self._resultado(pedido, rota, corpo, resposta, status)

    def _hospedar(self, arquivo: Path) -> str:
        try:
            corpo = base.post_multipart(self.url_base + ROTAS["upload"], arquivo, TIPOS_IMAGEM[arquivo.suffix.lower()],
                                        cabecalhos={"X-API-Key": self._chave}, timeout=TIMEOUT_UPLOAD)
        except base.ErroEnvio as erro:
            # upload não cria publicação: a falha aqui é definitiva para este envio
            raise base.ErroEnvio(erro.codigo, f"falha ao hospedar {arquivo.name}: {erro}",
                                 status_http=erro.status_http, incerto=False) from None
        url = ((corpo or {}).get("data") or {}).get("image_url") if isinstance(corpo, dict) else None
        if not url:
            raise base.ErroEnvio("upload_sem_url", f"o upload de {arquivo.name} não devolveu data.image_url")
        return url

    def _cabecalhos(self, pedido: base.Pedido) -> dict[str, str]:
        return {"X-API-Key": self._chave, "Idempotency-Key": pedido.chave_idempotencia}

    def _montar(self, pedido: base.Pedido, itens: list[dict[str, Any]], urls: Mapping[Path, str],
                texto: str, hashtags: str) -> tuple[str, dict[str, Any]]:
        """(rota, corpo). Mesma ordem de campos da origem (publicar.py:252-272)."""
        corpo: dict[str, Any] = {"caption": texto, "hashtags": hashtags, "platforms": list(pedido.canais)}
        if len(itens) == 1:
            item = itens[0]
            rota = ROTAS["post"]
            corpo["image_url"] = urls[item["caminho"]]  # o post-api chama de image_url também o vídeo
            if item["midia"] == "imagem":
                corpo["content_type"] = "image"
            else:
                corpo["content_type"] = "reel" if pedido.peca["tipo"] == "reel" else "video"
        else:
            rota = ROTAS["carrossel"]
            corpo["title"] = pedido.peca["titulo"]
            corpo["slides"] = [
                {"video_url": urls[i["caminho"]]} if i["midia"] == "video" else {"image_url": urls[i["caminho"]]}
                for i in itens
            ]
        if pedido.agendada_para:
            corpo["scheduled_at"] = pedido.agendada_para
        else:
            corpo["publish_now"] = True
        corpo["client_id"] = self.cliente
        if pedido.automacao is not None:
            corpo["automation"] = {k: pedido.automacao[k] for k in CAMPOS_AUTOMACAO if pedido.automacao.get(k) is not None}
        return rota, corpo

    def _exibir(self, rota: str, corpo: dict[str, Any], pedido: base.Pedido) -> dict[str, Any]:
        return {"rota": rota, "corpo": corpo, "idempotency_key": pedido.chave_idempotencia}

    def _resultado(self, pedido: base.Pedido, rota: str, corpo: dict[str, Any], resposta: Any,
                   status: int) -> base.Resultado:
        dados = (resposta.get("data") if isinstance(resposta, dict) else None) or {}
        id_post = _texto(dados.get("scheduled_post_id"))
        estado_ok = "publicada" if dados.get("published_now") else "agendada" if pedido.agendada_para else "publicada"
        dm = None
        aviso = None
        if pedido.automacao is not None:
            palavra = str(pedido.automacao["keywords"][0])
            dm = {"palavra": palavra, "id_externo": _texto(dados.get("trigger_id"))}
            if dados.get("automation_status") == "falhou" or dados.get("automation_error"):
                aviso = f"automação de DM falhou: {dados.get('automation_error') or 'sem detalhe'}"
        canais: dict[str, base.ResultadoCanal] = {}
        if status == 207:
            detalhe = _por_plataforma(dados)
            for canal in pedido.canais:
                info = detalhe.get(canal)
                if info is not None and info[0]:
                    canais[canal] = base.ResultadoCanal(estado=estado_ok, id_externo=id_post,
                                                        automacao_dm=dm if canal == "instagram" else None, erro=aviso)
                else:
                    motivo = (info[1] if info else None) or "sem detalhe por plataforma"
                    canais[canal] = base.ResultadoCanal(
                        estado="falhou", id_externo=id_post,
                        erro=f"criado no Expx Flow, mas o agendamento falhou (HTTP 207): {motivo}; confira no editor",
                    )
        else:
            for canal in pedido.canais:
                canais[canal] = base.ResultadoCanal(estado=estado_ok, id_externo=id_post,
                                                    automacao_dm=dm if canal == "instagram" else None, erro=aviso)
        return base.Resultado(canais=canais, payload=self._exibir(rota, corpo, pedido),
                              detalhe=f"HTTP {status} em {rota}")

    # ------------------------------------------------------------ automação avulsa

    def vincular_automacao(self, scheduled_post_id: str, automacao: dict[str, Any]) -> str | None:
        """Vincula automação de DM a um post já agendado; devolve o `trigger_id`. Uma tentativa só.

        origem: Instagram-Carrosseis/publicar/publicar.py:324-334
        """
        erros = _validar_automacao(automacao)
        if erros:
            raise base.ErroValidacao([{"codigo": "automacao", "mensagem": e} for e in erros])
        corpo = {"acao": "vincular_automacao", "scheduled_post_id": scheduled_post_id,
                 "automacao": {k: automacao[k] for k in CAMPOS_AUTOMACAO if automacao.get(k) is not None}}
        resposta = base.post_json(self.url_base + ROTAS["automacao"], corpo, cabecalhos={"X-API-Key": self._chave},
                                  timeout=TIMEOUT_AUTOMACAO)
        dados = (resposta.get("data") if isinstance(resposta, dict) else None) or {}
        return _texto(dados.get("trigger_id"))


def _texto(valor: Any) -> str | None:
    return None if valor is None else str(valor)


def _validar_automacao(a: Mapping[str, Any]) -> list[str]:
    """Regras do bloco automation (origem: Instagram-Carrosseis/contratos/automacao.schema.json e
    Instragram-Videos/pipeline/publish.py:83-100)."""
    erros: list[str] = []
    if not isinstance(a, Mapping):
        return ["automação precisa ser um objeto"]
    extras = sorted(set(a) - set(CAMPOS_AUTOMACAO))
    if extras:
        erros.append(f"campos desconhecidos na automação: {', '.join(extras)}")
    palavras = a.get("keywords")
    if not isinstance(palavras, list) or not palavras or not all(isinstance(p, str) and p.strip() for p in palavras):
        erros.append("automação sem keywords")
    elif len(set(palavras)) != len(palavras):
        erros.append("keywords repetidas na automação")
    if not (isinstance(a.get("mensagem"), str) and a["mensagem"].strip()):
        erros.append("automação sem mensagem")
    link = a.get("link")
    if link is not None and not str(link).startswith(("http://", "https://")):
        erros.append("link da automação precisa começar com http ou https")
    rotulo = a.get("link_label")
    if rotulo is not None and not 1 <= len(str(rotulo)) <= LINK_LABEL_MAX:
        erros.append(f"link_label tem {len(str(rotulo))} caracteres (máximo {LINK_LABEL_MAX})")
    if a.get("match_mode") is not None and a["match_mode"] not in MATCH_MODES:
        erros.append(f"match_mode é {', '.join(MATCH_MODES)}")
    modo = a.get("public_reply_mode")
    if modo is not None and modo not in REPLY_MODES:
        erros.append(f"public_reply_mode é {' ou '.join(REPLY_MODES)}")
    if a.get("public_reply_enabled"):
        if modo == "ia":
            if not a.get("public_reply_prompt"):
                erros.append("public_reply_mode 'ia' exige public_reply_prompt")
        elif not a.get("public_reply_text"):
            erros.append("resposta pública ligada exige public_reply_text")
    return erros


def _por_plataforma(dados: Mapping[str, Any]) -> dict[str, tuple[bool, str | None]]:
    """Estado por plataforma numa resposta 207, quando o servidor o informa.

    A documentação só diz "carrossel criado, mas o agendamento falhou" (base/publicar-expxflow.md:85);
    aceitamos `platforms`/`platform_results`/`results` como mapa ou lista de objetos com `platform`.
    """
    bruto = next((dados[c] for c in ("platforms", "platform_results", "results") if c in dados), None)
    pares: list[tuple[Any, Any]] = []
    if isinstance(bruto, Mapping):
        pares = list(bruto.items())
    elif isinstance(bruto, list):
        pares = [(x.get("platform"), x) for x in bruto if isinstance(x, Mapping)]
    saida: dict[str, tuple[bool, str | None]] = {}
    for nome, info in pares:
        if not isinstance(nome, str):
            continue
        if isinstance(info, Mapping):
            if "success" in info:
                ok = bool(info["success"])
            else:
                ok = str(info.get("status", "")).lower() in _OK_PLATAFORMA
            erro = info.get("error") or info.get("erro")
        else:
            ok, erro = bool(info), None
        saida[nome] = (ok, None if erro is None else str(erro))
    return saida

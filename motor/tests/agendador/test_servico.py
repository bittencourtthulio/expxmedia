"""T-08.05: serviço do agendador local (D-08, D-30; CONTRATO-capacidades, "O agendador local").

Adaptador falso injetado e relógio controlado: nada de rede, nada de Graph.
"""
from datetime import datetime, timedelta, timezone

import pytest

from expxmedia.agendador import servico
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.peca import modelo
from expxmedia.publicar import base


class AdaptadorFalso:
    """Faz o papel do MetaGraph: registra cada envio e devolve o resultado configurado."""

    provedor = "meta_graph"

    def __init__(self, *, erro=None, achados=None, estado="publicada"):
        self.envios = []
        self.validacoes = 0
        self._erro = erro
        self._achados = achados or []
        self._estado = estado

    def validar(self, pedido):
        self.validacoes += 1
        return list(self._achados)

    def enviar(self, pedido):
        self.envios.append(pedido)
        if self._erro is not None:
            raise self._erro
        return base.Resultado(
            canais={"instagram": base.ResultadoCanal(estado=self._estado, id_externo="midia_42",
                                                     url="https://permalink.invalid/p/42")},
            payload={"itens": 1}, detalhe="falso",
        )


def _agora(raiz):
    # relógio controlado: um instante fixo no fuso da Alma, sem segundos quebrados
    return tempo.agora(raiz).replace(microsecond=0)


def _peca_agendada(raiz, horario, *, provedor="meta_graph", canal="instagram", estado="agendada"):
    peca = modelo.criar(raiz, tipo="post_unico", titulo="Peça agendada", formatos=["4:5"], status="roteiro")
    peca_id = peca["peca_id"]
    modelo.registrar_producao(raiz, peca_id, capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=1)
    modelo.mudar_status(raiz, peca_id, "produzida")
    modelo.mudar_status(raiz, peca_id, "aprovada")
    modelo.registrar_publicacao(raiz, peca_id, {
        "canal": canal, "provedor": provedor, "estado": estado, "agendada_para": horario.isoformat(timespec="seconds"),
    })
    modelo.mudar_status(raiz, peca_id, "agendada")
    return peca_id


def _pub(raiz, peca_id, canal="instagram"):
    return next(p for p in modelo.carregar(raiz, peca_id)["publicacoes"] if p["canal"] == canal)


def _eventos(raiz, agora):
    eventos, _ = rastro.ler(raiz, agora.strftime("%Y-%m"))
    return [e for e in eventos if e["evento"].startswith("publicacao_")]


def _rodar(raiz, agora, adaptador):
    return servico.rodar(raiz, agora=agora, adaptador=adaptador)


# --- integração -------------------------------------------------------------------------

def test_peca_agendada_para_5_minutos_atras_publica_pelo_adaptador_e_grava_publicada(instalacao):
    agora = _agora(instalacao)
    horario = agora - timedelta(minutes=5)
    peca_id = _peca_agendada(instalacao, horario)
    adaptador = AdaptadorFalso()

    saida = _rodar(instalacao, agora, adaptador)

    assert len(adaptador.envios) == 1
    pedido = adaptador.envios[0]
    assert pedido.peca["peca_id"] == peca_id and pedido.canais == ["instagram"]
    # o adaptador publica de verdade só com agendada_para None (com horário, ele só agenda)
    assert pedido.agendada_para is None and pedido.dry_run is False
    pub = _pub(instalacao, peca_id)
    assert pub["estado"] == "publicada"
    assert pub["provedor"] == "meta_graph"
    assert pub["id_externo"] == "midia_42" and pub["url"] == "https://permalink.invalid/p/42"
    assert pub["agendada_para"] == horario.isoformat(timespec="seconds")  # o horário original fica
    assert pub["publicada_em"] is not None and pub["erro"] is None
    assert modelo.carregar(instalacao, peca_id)["status"] == "publicada"
    assert saida["publicadas"] == [{"peca_id": peca_id, "canal": "instagram"}]
    assert saida["atrasadas"] == [] and saida["falhas"] == []
    eventos = _eventos(instalacao, agora)
    assert [(e["evento"], e["origem"], e["resultado"]) for e in eventos] == [
        ("publicacao_concluida", "rotina", "ok")]
    assert eventos[0]["peca_id"] == peca_id and eventos[0]["provedor"] == "meta_graph"


def test_intencao_e_gravada_antes_do_envio(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=1))
    visto = {}

    class Espiao(AdaptadorFalso):
        def enviar(self, pedido):
            visto["pub"] = _pub(instalacao, peca_id)
            return super().enviar(pedido)

    _rodar(instalacao, agora, Espiao())

    assert visto["pub"]["estado"] == "falhou"
    assert visto["pub"]["erro"].startswith(base.MARCA_INCERTO)


# --- funcional --------------------------------------------------------------------------

def test_peca_agendada_para_20_minutos_atras_vira_falhou_por_atraso_sem_chamar_o_adaptador(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=20))
    adaptador = AdaptadorFalso()

    saida = _rodar(instalacao, agora, adaptador)

    assert adaptador.envios == [] and adaptador.validacoes == 0
    pub = _pub(instalacao, peca_id)
    assert pub["estado"] == "falhou"
    assert pub["erro"].startswith("atraso")
    assert "20 min" in pub["erro"]
    assert pub["publicada_em"] is None and pub["id_externo"] is None
    # a peça não é publicada: volta para a pessoa decidir
    assert modelo.carregar(instalacao, peca_id)["status"] == "agendada"
    assert saida["atrasadas"] == [{"peca_id": peca_id, "canal": "instagram"}]
    assert saida["publicadas"] == []
    eventos = _eventos(instalacao, agora)
    assert [(e["evento"], e["origem"], e["resultado"]) for e in eventos] == [("publicacao_falhou", "rotina", "falha")]
    assert "atraso" in eventos[0]["detalhe"]


def test_janela_de_tolerancia_e_de_15_minutos_exatos(instalacao):
    assert servico.TOLERANCIA_ATRASO == timedelta(minutes=15)
    agora = _agora(instalacao)
    no_limite = _peca_agendada(instalacao, agora - timedelta(minutes=15))
    passou = _peca_agendada(instalacao, agora - timedelta(minutes=15, seconds=1))
    adaptador = AdaptadorFalso()

    _rodar(instalacao, agora, adaptador)

    assert [p.peca["peca_id"] for p in adaptador.envios] == [no_limite]
    assert _pub(instalacao, no_limite)["estado"] == "publicada"
    assert _pub(instalacao, passou)["estado"] == "falhou"


def test_14_minutos_de_atraso_ainda_publica(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=14))
    adaptador = AdaptadorFalso()
    _rodar(instalacao, agora, adaptador)
    assert len(adaptador.envios) == 1 and _pub(instalacao, peca_id)["estado"] == "publicada"


def test_horario_futuro_fica_intocado_e_nem_cria_o_adaptador(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora + timedelta(minutes=1))
    antes = modelo.carregar(instalacao, peca_id)
    fabricadas = []

    saida = servico.rodar(instalacao, agora=agora, fabricar=lambda raiz: fabricadas.append(raiz))

    assert fabricadas == []  # sem nada devido, nenhuma credencial é necessária
    assert modelo.carregar(instalacao, peca_id) == antes
    assert saida["pendentes"] == 1 and saida["publicadas"] == []


def test_horario_em_outro_fuso_e_comparado_pelo_instante(instalacao):
    agora = _agora(instalacao)
    horario = (agora - timedelta(minutes=5)).astimezone(timezone(timedelta(hours=9)))
    peca_id = _peca_agendada(instalacao, horario)
    adaptador = AdaptadorFalso()
    _rodar(instalacao, agora, adaptador)
    assert _pub(instalacao, peca_id)["estado"] == "publicada"


def test_so_publicacoes_agendadas_via_meta_graph_entram(instalacao):
    agora = _agora(instalacao)
    pelo_servidor = _peca_agendada(instalacao, agora - timedelta(minutes=2), provedor="expxflow")
    adaptador = AdaptadorFalso()

    saida = _rodar(instalacao, agora, adaptador)

    assert adaptador.envios == []
    assert _pub(instalacao, pelo_servidor)["estado"] == "agendada"  # o expxflow agenda no servidor
    assert saida["publicadas"] == [] and saida["pendentes"] == 0


def test_segunda_rodada_nao_publica_de_novo(instalacao):
    agora = _agora(instalacao)
    _peca_agendada(instalacao, agora - timedelta(minutes=3))
    adaptador = AdaptadorFalso()
    _rodar(instalacao, agora, adaptador)
    _rodar(instalacao, agora + timedelta(minutes=1), adaptador)
    assert len(adaptador.envios) == 1


def test_erro_incerto_do_provedor_grava_falhou_e_nao_retenta_na_rodada_seguinte(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=2))
    adaptador = AdaptadorFalso(erro=base.ErroEnvio("http_503", "o provedor respondeu HTTP 503", incerto=True))

    saida = _rodar(instalacao, agora, adaptador)
    _rodar(instalacao, agora + timedelta(minutes=1), adaptador)

    assert len(adaptador.envios) == 1  # D-29: nunca retenta
    pub = _pub(instalacao, peca_id)
    assert pub["estado"] == "falhou" and pub["erro"].startswith(base.MARCA_INCERTO)
    assert "503" in pub["erro"]
    assert modelo.carregar(instalacao, peca_id)["status"] == "agendada"
    assert saida["falhas"] == [{"peca_id": peca_id, "canal": "instagram"}]
    assert [e["evento"] for e in _eventos(instalacao, agora)] == ["publicacao_falhou"]


def test_achado_de_validacao_vira_falhou_sem_enviar(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=2))
    adaptador = AdaptadorFalso(achados=[{"codigo": "proporcao", "mensagem": "imagem 9:16 não cabe"}])

    _rodar(instalacao, agora, adaptador)

    assert adaptador.envios == []
    pub = _pub(instalacao, peca_id)
    assert pub["estado"] == "falhou" and "9:16" in pub["erro"]
    assert not pub["erro"].startswith(base.MARCA_INCERTO)


def test_sem_credenciais_vira_falhou_com_o_nome_da_variavel(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=2))

    servico.rodar(instalacao, agora=agora)  # adaptador real da instalação, .env vazio

    pub = _pub(instalacao, peca_id)
    assert pub["estado"] == "falhou" and "META_GRAPH_TOKEN" in pub["erro"]


def test_trava_de_instancia_unica(instalacao):
    agora = _agora(instalacao)
    _peca_agendada(instalacao, agora - timedelta(minutes=2))
    adaptador = AdaptadorFalso()

    with arquivos.trava(servico.caminho_trava(instalacao)):
        saida = _rodar(instalacao, agora, adaptador)

    assert saida["travado"] is True
    assert adaptador.envios == []
    # solta a trava, a rodada seguinte publica
    assert _rodar(instalacao, agora, adaptador)["travado"] is False
    assert len(adaptador.envios) == 1


def test_peca_json_quebrado_nao_derruba_a_rodada(instalacao):
    agora = _agora(instalacao)
    boa = _peca_agendada(instalacao, agora - timedelta(minutes=2))
    quebrada = instalacao / "pecas" / "2026-01" / "P-20260101-ABCD-quebrada"
    quebrada.mkdir(parents=True)
    (quebrada / "peca.json").write_text("{nao é json", encoding="utf-8")
    adaptador = AdaptadorFalso()

    saida = _rodar(instalacao, agora, adaptador)

    assert _pub(instalacao, boa)["estado"] == "publicada"
    assert saida["ilegiveis"] == ["pecas/2026-01/P-20260101-ABCD-quebrada/peca.json"]


def test_peca_descartada_e_ignorada(instalacao):
    agora = _agora(instalacao)
    peca_id = _peca_agendada(instalacao, agora - timedelta(minutes=2))
    modelo.mudar_status(instalacao, peca_id, "descartada", motivo="desisti")
    adaptador = AdaptadorFalso()
    _rodar(instalacao, agora, adaptador)
    assert adaptador.envios == [] and _pub(instalacao, peca_id)["estado"] == "agendada"


def test_agora_sem_fuso_e_recusado(instalacao):
    with pytest.raises(ValueError):
        servico.rodar(instalacao, agora=datetime(2026, 9, 25, 12, 0), adaptador=AdaptadorFalso())

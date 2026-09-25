"""Momentos do vídeo longo: pré-filtra os trechos candidatos a virar o corte. NÃO escolhe — ranqueia.

Porta de `Instragram-Videos/pipeline/momentos.py`. A escolha do trecho é julgamento (isso prende alguém nos
três primeiros segundos? isso fecha uma ideia?); o que se automatiza é o mecânico: onde a frase começa,
onde fecha, se o trecho cabe na janela, se abre dependendo de contexto que ficou para trás, se a faixa já
virou vídeo. Por isso a nota é **desempate, não veredito**: `escolher` devolve o primeiro do ranking para
quem não tem leitor, mas quem tem deve ler o texto dos candidatos.

As listas de palavras (anáfora, muleta, hesitação, categoria vaga, referência para fora do reel, gancho,
número) e os pesos são **dado por idioma**, não código: `recursos/momentos/<idioma>.json`, escolhido pelo
idioma da Alma (`empresa.idioma`). O padrão em português tem os valores da origem, medidos numa conta; uma
instalação que recalibrar passa a própria configuração (`config=`).

Algoritmo (os números estão na configuração):

- início de frase: a primeira palavra, e toda palavra depois de pontuação de fim (`. ? !`) ou de uma pausa
  ≥ 0,6 s (o respiro entre ideias);
- para cada início, o trecho vai até o ÚLTIMO fim de frase que ainda cabe na janela (52 a 72 s): mais
  conteúdo no mesmo tempo;
- pontos: anáfora na primeira palavra −3; muleta na primeira −2; referência para fora do reel nas 12
  primeiras palavras −3; falsa largada (primeira palavra de mais de 3 letras repetida nas 5 primeiras) −1;
  gancho na abertura +2; número nas 12 primeiras +3 (senão no trecho +1); hesitação nas 12 primeiras −1,5;
  categoria vaga nas 12 primeiras −1,5; densidade `+2·(1 − min(silêncio/0,25, 1))`, com nota acima de 20%
  de silêncio; faixa já usada `−5·fração`; trecho a menos de 4 s do piso −0,5;
- ordena pela nota e tira os que se sobrepõem (o mesmo trecho com outra borda), até `n`.

Saída de `candidatos`: ``{gerados, candidatos: [{inicio, fim, duracao, palavras, pontos, silencio_frac,
ja_usado_frac, notas, texto}]}`` — o `candidatos.json` da origem.

Uso:

    from expxmedia.corte import momentos
    cfg = momentos.config_da_alma(alma)
    r = momentos.candidatos(transcricao, faixas_ja_usadas=[[120.0, 180.0]], config=cfg)
    trecho = r["candidatos"][0]
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

__all__ = ["ErroMomentos", "PASTA_CONFIG", "carregar_config", "config_da_alma", "candidatos", "escolher",
           "inicios_de_frase"]

PASTA_CONFIG = Path(__file__).resolve().parents[1] / "recursos" / "momentos"
VERSAO = 1
_LISTAS = ("anafora", "muleta", "hesitacao", "vago", "fora_do_reel", "gancho", "numero")
_PESOS = ("anafora", "muleta", "fora_do_reel", "falsa_largada", "gancho", "numero_abertura", "numero_trecho",
          "hesitacao", "vago", "densidade", "ja_usado", "curto")


class ErroMomentos(ValueError):
    """Configuração ausente, transcrição sem palavras ou nenhum trecho que feche em fim de frase."""


def _codigo(idioma: str | None) -> str | None:
    if not isinstance(idioma, str) or not idioma.strip():
        return None
    return idioma.strip().replace("_", "-").split("-")[0].lower()


def carregar_config(idioma: str) -> dict[str, Any]:
    """Configuração do idioma (`pt-BR` → `recursos/momentos/pt.json`)."""
    codigo = _codigo(idioma)
    if codigo is None:
        raise ErroMomentos("idioma não informado: passe o idioma da Alma (empresa.idioma)")
    arquivo = PASTA_CONFIG / f"{codigo}.json"
    if not arquivo.is_file():
        existentes = sorted(p.stem for p in PASTA_CONFIG.glob("*.json"))
        raise ErroMomentos(f"não há configuração de momentos para o idioma {codigo!r} "
                           f"(existem: {', '.join(existentes) or 'nenhuma'}); passe config= calibrada")
    config = json.loads(arquivo.read_text(encoding="utf-8"))
    _validar(config)
    return config


def config_da_alma(alma: Any) -> dict[str, Any]:
    """Configuração pelo idioma da Alma (`empresa.idioma`)."""
    dados = alma.dados if hasattr(alma, "dados") else alma
    return carregar_config(((dados or {}).get("empresa") or {}).get("idioma"))


def _validar(config: dict[str, Any]) -> None:
    versao = config.get("expxmedia_momentos")
    if versao is None or versao > VERSAO:
        raise ErroMomentos(f"configuração de momentos com versão {versao!r} (suportada: {VERSAO})")
    faltam = [f"listas.{n}" for n in _LISTAS if n not in (config.get("listas") or {})]
    faltam += [f"pesos.{n}" for n in _PESOS if n not in (config.get("pesos") or {})]
    if faltam:
        raise ErroMomentos(f"configuração de momentos incompleta: faltam {', '.join(faltam)}")


def inicios_de_frase(palavras: list[dict[str, Any]], config: dict[str, Any]) -> list[int]:
    """Índices das palavras que abrem frase: a primeira, depois de fim de frase ou de pausa longa.
    origem: Instragram-Videos/pipeline/momentos.py:114-120"""
    fim = tuple(config["fim_frase"])
    inicios = [0]
    for i in range(len(palavras) - 1):
        pausa = palavras[i + 1]["t0"] - palavras[i]["t1"]
        if palavras[i]["w"].endswith(fim) or pausa >= config["pausa_frase_s"]:
            inicios.append(i + 1)
    return inicios


def candidatos(
    transcricao: dict[str, Any],
    *,
    config: dict[str, Any],
    faixas_ja_usadas: Iterable[Iterable[float]] = (),
    n: int | None = None,
    minimo: float | None = None,
    maximo: float | None = None,
) -> dict[str, Any]:
    """Ranqueia os trechos que fecham em fim de frase dentro da janela. Ver o módulo."""
    _validar(config)
    P = transcricao.get("palavras") or []
    if not P:
        # origem: Instragram-Videos/pipeline/momentos.py:89-90
        raise ErroMomentos("transcrição sem palavras")
    n = config["candidatos_n"] if n is None else n
    minimo = config["janela_min_s"] if minimo is None else minimo
    maximo = config["janela_max_s"] if maximo is None else maximo
    usadas = [tuple(f) for f in faixas_ja_usadas]
    fim_frase = tuple(config["fim_frase"])
    re_ = {nome: re.compile(config["listas"][nome], re.I) for nome in _LISTAS}
    pesos = config["pesos"]
    n3s = config["palavras_3s"]

    cands = []
    for i in inicios_de_frase(P, config):
        melhor = None
        for j in range(i + 1, len(P)):
            dur = P[j]["t1"] - P[i]["t0"]
            if dur < minimo:
                continue
            if dur > maximo:
                break
            if not P[j]["w"].endswith(fim_frase):
                continue
            melhor = j  # o último fim de frase que ainda cabe: mais conteúdo no mesmo tempo
        if melhor is None:
            continue
        j = melhor
        t0, t1 = P[i]["t0"], P[j]["t1"]
        dur = t1 - t0
        palavras = P[i:j + 1]
        texto = " ".join(p["w"] for p in palavras)

        # densidade: silêncio dentro do trecho é tempo de reel sem nada dito
        silencio = sum(max(0.0, palavras[k + 1]["t0"] - palavras[k]["t1"]) for k in range(len(palavras) - 1))
        coberto = sum(0 if b <= t0 or a_ >= t1 else (min(t1, b) - max(t0, a_)) for a_, b in usadas)

        # origem: Instragram-Videos/pipeline/momentos.py:147-183 (a ordem das somas é a da origem)
        pontos, notas = 0.0, []
        if re_["anafora"].match(texto):
            pontos += pesos["anafora"]
            notas.append(f"abre com anáfora ('{texto.split()[0]}') — depende do que veio antes")
        if re_["muleta"].match(texto):
            pontos += pesos["muleta"]
            notas.append(f"abre com muleta ('{texto.split()[0]}') — mova a borda para a palavra seguinte")
        fora = re_["fora_do_reel"].search(" ".join(texto.split()[:n3s]))
        if fora:
            pontos += pesos["fora_do_reel"]
            notas.append(f"os 3 primeiros segundos apontam para fora do reel ('{fora.group(0)}')")
        # falsa largada: começa, para e recomeça
        limpas = [re.sub(r"\W", "", w).lower() for w in texto.split()[:config["falsa_largada_palavras"]]]
        if len(limpas[0]) > config["falsa_largada_letras_min"] and limpas[0] in limpas[1:]:
            pontos += pesos["falsa_largada"]
            notas.append(f"possível falsa largada ('{limpas[0]}' repetida) — confira o áudio e mova a borda")
        if re_["gancho"].match(texto):
            pontos += pesos["gancho"]
            notas.append("abre com pergunta ou promessa")
        abertura = " ".join(texto.split()[:n3s])
        if re_["numero"].search(abertura):
            pontos += pesos["numero_abertura"]
            notas.append("abre com número concreto — o sinal mais forte medido")
        elif re_["numero"].search(texto):
            pontos += pesos["numero_trecho"]
            notas.append("tem número concreto, mas fora dos 3 primeiros segundos")
        hes = re_["hesitacao"].search(abertura)
        if hes:
            pontos += pesos["hesitacao"]
            notas.append(f"muleta dentro dos 3 segundos ('{hes.group(0)}') — mova a borda")
        vago = re_["vago"].search(abertura)
        if vago:
            pontos += pesos["vago"]
            notas.append(f"abre em categoria abstrata ('{vago.group(0)}') — "
                         "procure o ponto em que ele nomeia a coisa")
        frac_sil = silencio / dur
        pontos += pesos["densidade"] * (1 - min(frac_sil / config["silencio_referencia"], 1.0))
        if frac_sil > config["silencio_nota"]:
            notas.append(f"{frac_sil:.0%} do trecho é silêncio")
        if coberto > 0:
            pontos += pesos["ja_usado"] * (coberto / dur)
            notas.append(f"{coberto/dur:.0%} já usado em outro corte")
        if dur < minimo + config["curto_folga_s"]:
            pontos += pesos["curto"]
        cands.append({"inicio": round(t0, 2), "fim": round(t1, 2), "duracao": round(dur, 2),
                      "palavras": len(palavras), "pontos": round(pontos, 2),
                      "silencio_frac": round(frac_sil, 3), "ja_usado_frac": round(coberto / dur, 3),
                      "notas": notas, "texto": texto})

    if not cands:
        # origem: Instragram-Videos/pipeline/momentos.py:189-192
        raise ErroMomentos(f"nenhum trecho de {minimo:.0f}-{maximo:.0f}s fecha em fim de frase: ou a transcrição "
                           "saiu sem pontuação, ou o vídeo não tem bloco contínuo desse tamanho")

    cands.sort(key=lambda c: -c["pontos"])
    escolhidos: list[dict[str, Any]] = []
    for c in cands:
        # dois candidatos que se sobrepõem são o mesmo trecho com outra borda
        if any(not (c["fim"] <= e["inicio"] or c["inicio"] >= e["fim"]) for e in escolhidos):
            continue
        escolhidos.append(c)
        if len(escolhidos) >= n:
            break
    return {"gerados": len(cands), "candidatos": escolhidos}


def escolher(transcricao: dict[str, Any], *, config: dict[str, Any],
             faixas_ja_usadas: Iterable[Iterable[float]] = (), **kw: Any) -> dict[str, Any]:
    """O primeiro do ranking (desempate mecânico, para quem não tem leitor)."""
    return candidatos(transcricao, config=config, faixas_ja_usadas=faixas_ja_usadas, **kw)["candidatos"][0]

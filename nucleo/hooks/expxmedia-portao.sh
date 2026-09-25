#!/usr/bin/env bash
# expxmedia-portao.sh — o portão de primeiro uso do ExpxMedia (CONTRATO-alma, "O portão").
#
# UserPromptSubmit: roda antes da primeira ação do modelo, e o que ele escreve no stdout
# entra no contexto daquele turno.
#
# Por que existe: instrução em skill é esquecida. Uma instrução imperativa injetada ANTES da
# primeira ação garante que o portão seja conferido mesmo quando o modelo parte direto para
# produzir. É a primeira das duas camadas do contrato; a segunda é o primeiro passo de toda skill.
#
# A ordem é fixa, a mesma de `expxmedia.alma.carregar.portao`:
#   1. alma/alma.json ausente, ilegível ou com "confirmada_em" nulo  -> /expxmedia:alma
#   2. .env ausente na raiz da instalação (vazio vale)                -> /expxmedia:ambiente
#   3. portão aberto                                                   -> não injeta nada
#
# Regras deste arquivo:
#   1. Rápido: só arquivo local, sem rede.
#   2. Falha aberta: qualquer erro sai 0 e não injeta nada. Nunca bloqueia o prompt.
#   3. Uma instrução só, a do primeiro degrau do portão que falta.

set -u

EVENTO="$(cat 2>/dev/null || true)"

# Onde começa a busca pela raiz: a pasta do projeto do Claude, senão o cwd do evento,
# senão a pasta atual.
INICIO="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$INICIO" ] && [ -n "$EVENTO" ] && command -v python3 >/dev/null 2>&1; then
  INICIO="$(printf '%s' "$EVENTO" | python3 -c '
import json, sys
try:
    dados = json.load(sys.stdin)
    cwd = dados.get("cwd") if isinstance(dados, dict) else None
    print(cwd if isinstance(cwd, str) else "")
except Exception:
    print("")
' 2>/dev/null || true)"
fi
[ -z "$INICIO" ] && INICIO="$PWD"
[ -d "$INICIO" ] || exit 0

# A raiz da instalação é a primeira pasta, subindo, que tem alma/. Sem nenhuma, é o início.
RAIZ=""
PASTA="$(cd "$INICIO" 2>/dev/null && pwd -P)" || exit 0
while :; do
  if [ -d "$PASTA/alma" ]; then RAIZ="$PASTA"; break; fi
  [ "$PASTA" = "/" ] && break
  PASTA="$(dirname "$PASTA")"
done
[ -z "$RAIZ" ] && RAIZ="$(cd "$INICIO" 2>/dev/null && pwd -P)"
[ -z "$RAIZ" ] && exit 0

ALMA="$RAIZ/alma/alma.json"

# A Alma está confirmada? confirmada_em é texto não vazio num JSON legível.
alma_confirmada() {
  [ -f "$ALMA" ] || return 1
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$ALMA" <<'PY' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8-sig") as f:
        dados = json.load(f)
    valor = dados.get("confirmada_em") if isinstance(dados, dict) else None
    sys.exit(0 if isinstance(valor, str) and valor.strip() else 1)
except Exception:
    sys.exit(1)
PY
    return $?
  fi
  grep -Eq '"confirmada_em"[[:space:]]*:[[:space:]]*"[^"[:space:]]' "$ALMA" 2>/dev/null
}

TEXTO=""
if ! alma_confirmada; then
  TEXTO="[ExpxMedia] Portão de primeiro uso: esta instalação ainda não tem a Alma confirmada (alma/alma.json ausente, ilegível ou com confirmada_em nulo).

ANTES de qualquer outra ação: rode /expxmedia:alma. Nenhuma skill produz, publica ou planeja peça sem Alma confirmada, porque toda a marca (nome, voz, cores, público, CTA) vem dela. Se o pedido atual já é criar ou revisar a Alma, siga com ele; qualquer outro pedido de produção fica para depois do \"confirmo tudo\"."
elif [ ! -f "$RAIZ/.env" ]; then
  TEXTO="[ExpxMedia] Portão de primeiro uso: a Alma está confirmada, mas a instalação não tem o arquivo .env.

ANTES de qualquer outra ação: rode /expxmedia:ambiente. Ele cria o .env (pode ficar vazio: sem chave nenhuma já saem post, carrossel e apresentação) e explica o que cada chave libera. A chave é colada no arquivo, nunca na conversa."
fi

[ -z "$TEXTO" ] && exit 0

if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$TEXTO" | python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": sys.stdin.read()}}, ensure_ascii=False))
' 2>/dev/null && exit 0
fi
if command -v jq >/dev/null 2>&1; then
  jq -n --arg t "$TEXTO" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$t}}' 2>/dev/null && exit 0
fi
ESC="$(printf '%s' "$TEXTO" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n",$0}')"
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$ESC"
exit 0

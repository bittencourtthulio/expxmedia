#!/usr/bin/env bash
# expxmedia-segredo.sh — guarda de segredos do núcleo do ExpxMedia (regra M14, CONTRATO-pack).
#
# PreToolUse em Read, Edit, MultiEdit, Write, NotebookEdit, Bash, Grep e Glob. Bloqueia (sai 2,
# com o motivo no stderr, que o Claude Code devolve ao modelo) toda leitura, escrita ou comando
# que toque:
#   - o .env da instalação e variantes (.env.local, .env.producao...), menos os exemplos sem
#     valor (.env.example, .env.sample, .env.template, .env.exemplo);
#   - arquivos de token (token.json, youtube_tokens.pickle...) e client_secret*;
#   - no Bash, a expansão de variável de segredo ($ELEVENLABS_API_KEY, ${META_GRAPH_TOKEN}) e o
#     despejo do ambiente inteiro (printenv, env ou export -p sozinhos).
#
# Hook de segurança nasce em bloqueio e falha FECHADO (CONTRATO-pack, regra 4 de agentes e hooks):
# payload ilegível, sem python3 ou erro interno também saem 2. A chave vai para o .env pela mão da
# pessoa (/expxmedia:ambiente), nunca pela conversa.

set -u

EVENTO="$(cat 2>/dev/null || true)"

negar() {
  printf 'expxmedia-segredo: bloqueado. %s Segredo fica só no .env e não passa pela conversa (M14). Para configurar chaves, use /expxmedia:ambiente: a pessoa cola a chave no arquivo.\n' "$1" >&2
  exit 2
}

[ -z "$EVENTO" ] && negar "Evento vazio: sem saber a ferramenta, a guarda não libera."
command -v python3 >/dev/null 2>&1 || negar "python3 ausente: sem ele a guarda não lê o evento."

MOTIVO="$(printf '%s' "$EVENTO" | python3 -c '
import json, os, re, sys

EXEMPLOS = {"example", "sample", "template", "exemplo"}


def motivo_arquivo(caminho):
    """Motivo para bloquear o caminho, ou None."""
    if not isinstance(caminho, str) or not caminho:
        return None
    nome = os.path.basename(caminho.rstrip("/")).lower()
    if nome == ".env" or (nome.startswith(".env.") and nome[5:] not in EXEMPLOS):
        return f"{nome} guarda as chaves da instalação."
    if "client_secret" in nome:
        return f"{nome} é credencial OAuth (client_secret)."
    base, ext = os.path.splitext(nome)
    if re.search(r"tokens?", base) and ext in {".json", ".txt", ".pickle", ".pkl", ""}:
        return f"{nome} guarda token de acesso."
    return None


# .env como palavra de caminho: não casa .envrc nem process.env; casa .env, ./.env, x/.env.local.
RE_ENV = re.compile(r"(?<![\w.-])\.env(?:\.([\w-]+))?(?![\w-])", re.IGNORECASE)
RE_CLIENT = re.compile(r"client_secret", re.IGNORECASE)
RE_TOKEN = re.compile(r"(?<![\w.-])[\w.-]*tokens?[\w-]*\.(?:json|txt|pickle|pkl)\b", re.IGNORECASE)
RE_VAR = re.compile(r"\$\{?[A-Za-z_]*(?:API_KEY|APIKEY|TOKEN|SECRET|PASSWORD|SENHA)[A-Za-z0-9_]*")
RE_DESPEJO = re.compile(r"(?:^|[;&|(]\s*)(?:printenv|env|export\s+-p|set)\s*(?:$|[;&|)])")


def motivo_comando(comando):
    if not isinstance(comando, str):
        return "comando ilegível."
    for achado in RE_ENV.finditer(comando):
        sufixo = (achado.group(1) or "").lower()
        if sufixo not in EXEMPLOS:
            return f"o comando toca {achado.group(0)}, que guarda as chaves da instalação."
    if RE_CLIENT.search(comando):
        return "o comando toca um client_secret (credencial OAuth)."
    achado = RE_TOKEN.search(comando)
    if achado:
        return f"o comando toca {achado.group(0)}, que guarda token de acesso."
    achado = RE_VAR.search(comando)
    if achado:
        return f"o comando expande {achado.group(0)}, uma variável de segredo."
    if RE_DESPEJO.search(comando.strip()):
        return "o comando despeja o ambiente inteiro, com as chaves junto."
    return None


try:
    evento = json.loads(sys.stdin.read())
    ferramenta = evento["tool_name"]
    entrada = evento["tool_input"]
    if not isinstance(ferramenta, str) or not isinstance(entrada, dict):
        raise ValueError
except Exception:
    print("Evento ilegível: sem saber a ferramenta, a guarda não libera.")
    sys.exit(0)

if ferramenta == "Bash":
    motivo = motivo_comando(entrada.get("command"))
else:
    motivo = None
    for chave in ("file_path", "notebook_path", "path"):
        motivo = motivo or motivo_arquivo(entrada.get(chave))
    if ferramenta in ("Glob", "Grep") and motivo is None:
        padrao = entrada.get("pattern") if ferramenta == "Glob" else entrada.get("glob")
        motivo = motivo_arquivo(padrao)
print(motivo or "")
' 2>/dev/null)" || negar "Erro interno da guarda."

[ -n "$MOTIVO" ] && negar "$MOTIVO"
exit 0

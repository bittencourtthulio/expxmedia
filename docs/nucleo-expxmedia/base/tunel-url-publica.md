# URL pública temporária por túnel (apoio de `publicar` e `agendar`)

Os dois provedores de publicação baixam a mídia de uma URL pública: o Expx Flow no `post-api`
(rehospeda e esquece a origem) e a Graph API da Meta (baixa durante o processamento do contêiner).
O projeto de vídeos resolve isso com `Instragram-Videos/pipeline/tunel.py`: expõe **um** arquivo
por um Quick Tunnel do Cloudflare pelo tempo de um bloco `with`. O `CONTRATO-capacidades.md:81-82`
prevê o mesmo mecanismo no agendador local.

## Contrato de entrada

- `url_publica_temporaria(arquivo: Path, verbose: bool = True)` — gerenciador de contexto
  (`tunel.py:24-25`).
- Pré-requisito: binário `cloudflared` no `PATH`; sem ele, `sys.exit` com instrução de instalação
  por Homebrew ou de passar `--media-url` (`tunel.py:26-28`).
- Não exige conta Cloudflare: Quick Tunnel é gratuito e sem conta (TryCloudflare, oficial).
- Comando executado: `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:<porta livre>`
  (`tunel.py:43-45`).
- Alternativa de origem: `--media-url` pula o túnel quando a mídia já está hospedada
  (`Instragram-Videos/pipeline/publish.py:23,173-178`).

## Contrato de saída

- Rende `https://<sub>.trycloudflare.com/<token aleatório><sufixo>` (`tunel.py:33,68-74`).
- Isolamento: cópia do arquivo num diretório temporário só com ela, sob nome aleatório de 16 bytes
  (`tunel.py:30-34`); servidor HTTP local só em `127.0.0.1` (`tunel.py:37-39`).
- Ao sair do bloco: encerra o `cloudflared` (espera até 10 s), para o servidor e apaga a cópia
  (`tunel.py:100-107`).
- Nada é gravado em estado; nenhum evento é emitido.

## Limites e cotas

| Limite | Valor | Fonte |
|---|---|---|
| Tempo para o túnel subir | 60 s (`TEMPO_LIMITE`) | `tunel.py:15,60-72` |
| Verificação externa | 6 tentativas × 3 s, GET com `Range: bytes=0-0`; falha vira **aviso**, não aborto | `tunel.py:82-97` |
| Requisições simultâneas no Quick Tunnel | 200 em andamento | TryCloudflare (oficial) |
| SSE | não suportado | TryCloudflare |
| SLA / disponibilidade | nenhum: "intended for testing and development only" | TryCloudflare |
| Tamanho máximo de arquivo pelo túnel | NÃO DOCUMENTADO | TryCloudflare |
| Por quanto tempo a URL precisa existir — Expx Flow | "só precisa estar acessível no momento da chamada" | `Instragram-Videos/docs/expx-flow/llms.txt:1117` |
| Por quanto tempo a URL precisa existir — Graph API | até o contêiner processar: mídia pública "at publishing attempt time"; status consultado 1×/min por até 5 min | guia Content Publishing da Meta |

## Erros conhecidos e tratamento

- `cloudflared` ausente → `sys.exit` (`tunel.py:26-28`).
- Túnel não sobe em 60 s ou processo morre → `RuntimeError("o túnel do Cloudflare não subiu a tempo")` (`tunel.py:65-72`).
- **Pipe cheio trava o túnel**: o stdout do `cloudflared` é drenado numa thread o tempo todo, "se o pipe encher, o processo trava e o túnel para de responder no meio da transferência" (`tunel.py:47-54`).
- DNS local com NXDOMAIN em cache para o subdomínio novo: a verificação local falha e o código segue, porque quem baixa é o servidor remoto (`tunel.py:78-81,95-97`).
- Do lado remoto: Expx Flow devolve 422 se não conseguir baixar (`llms.txt:381`, documentado para carrossel); Graph API devolve `9004/2207052` (URI inalcançável) ou `-2/2207003` (download demorou) (ref. Error Codes da Meta).

## Riscos para a nossa implementação

1. **Quick Tunnel não tem SLA** e é declarado só para teste; o agendador local depender dele em produção é risco aceito pelo contrato, não resolvido. Alternativa oficial: túnel nomeado com conta Cloudflare (fora do escopo desta ingestão).
2. **Graph API processa depois da chamada**: o túnel precisa ficar aberto até `status_code = FINISHED`, não só durante o `POST /media`. O `tunel.py` fecha ao sair do bloco; o adaptador `meta_graph` precisa manter o bloco aberto durante a espera. Para carrossel, são até 10 arquivos: um túnel por arquivo (padrão atual) ou um diretório com vários: NÃO DOCUMENTADO na origem.
3. **Dependência de SO**: a mensagem de instalação cita só Homebrew (`tunel.py:27`); instalar `cloudflared` em Windows/Linux fica para o `doctor`/`ambiente`. `cloudflared` também não está no catálogo de "Satisfeito por" do contrato (`CONTRATO-capacidades.md:58-64`): precisa entrar como binário exigido de `agendar` via `meta_graph`.
4. Expor arquivo local na internet: mitigado por nome aleatório e diretório isolado; o endereço fica válido enquanto o bloco dura.
5. Para o Expx Flow com imagem, o túnel é desnecessário (há `media-upload-api`); só vídeo precisa (`Instragram-Videos/.claude/rules/publicacao.md:39-46`).

## Fonte

- `Instragram-Videos/pipeline/tunel.py:1-107`
- `Instragram-Videos/pipeline/publish.py:126-178`
- `Instragram-Videos/.claude/rules/publicacao.md:39-46`
- `Instragram-Videos/docs/expx-flow/llms.txt:1007,1117`
- TryCloudflare (Quick Tunnels) — https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/ (acesso 2026-09-24)
- Meta Content Publishing — https://developers.facebook.com/docs/instagram-platform/content-publishing (acesso 2026-09-24)
- Meta Error Codes — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes (acesso 2026-09-24)

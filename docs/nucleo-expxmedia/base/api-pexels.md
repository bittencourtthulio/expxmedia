# Pexels

## Contrato de entrada

Provedor `pexels` da capacidade `banco_imagens` (busca de foto **e vídeo** de banco, para b-roll).

- **Autenticação:** header `Authorization: <PEXELS_API_KEY>`, **sem** prefixo `Bearer` — https://www.pexels.com/api/documentation/
- **Base URLs:** fotos `https://api.pexels.com/v1/`; vídeos `https://api.pexels.com/v1/videos/` — mesma URL.

**Busca de fotos:** `GET https://api.pexels.com/v1/search` — https://www.pexels.com/api/documentation/
- `query` (obrigatório).
- `orientation`: `landscape` | `portrait` | `square`.
- `size` (tamanho mínimo): `large` (24 MP) | `medium` (12 MP) | `small` (4 MP).
- `color`: `red`, `orange`, `yellow`, `green`, `turquoise`, `blue`, `violet`, `pink`, `brown`, `black`, `gray`, `white` ou hex.
- `locale` (código de idioma; a doc lista os suportados).
- `page` (padrão 1), `per_page` (padrão 15, **máx. 80**).

**Busca de vídeos:** `GET https://api.pexels.com/v1/videos/search` — https://www.pexels.com/api/documentation/
- `query` (obrigatório), `orientation` (`landscape|portrait|square`), `size` (`large` = 4K, `medium` = Full HD, `small` = HD), `locale`, `page` (padrão 1), `per_page` (padrão 15, máx. 80).
- Filtros adicionais: `min_width`, `min_height`, `min_duration`, `max_duration` (em segundos, pelo nome; a unidade NÃO está explícita no trecho lido).

## Contrato de saída

Envelope da busca: `total_results`, `page`, `per_page`, `next_page` e `prev_page` (presentes só quando existem), mais `photos[]` ou `videos[]` — https://www.pexels.com/api/documentation/

**Photo:** `id`, `width`, `height`, `url` (página no Pexels), `photographer`, `photographer_url`, `photographer_id`, `avg_color`, `alt`, `src` — https://www.pexels.com/api/documentation/

`src` (URLs prontas):

| chave | tamanho |
|---|---|
| `original` | resolução total (width × height) |
| `large2x` | 940×650, DPR 2 |
| `large` | 940×650, DPR 1 |
| `medium` | altura escalada para 350 px |
| `small` | altura escalada para 130 px |
| `portrait` | 800×1200, recortada |
| `landscape` | 1200×627, recortada |
| `tiny` | 280×200, recortada |

**Video:** `id`, `width`, `height`, `url`, `image` (screenshot), `duration` (segundos), `user` (videomaker), `video_files[]`, `video_pictures[]` — https://www.pexels.com/api/documentation/
- `video_files[]`: `id`, `quality`, `file_type`, `width`, `height`, `fps`, `link` (URL do arquivo).
- `video_pictures[]`: `id`, `picture` (URL), `nr` (índice).
- Quais valores `quality` pode ter (ex. `hd`, `sd`, `uhd`) e se toda resolução existe para todo vídeo: NÃO DOCUMENTADO de forma exaustiva.

## Limites e cotas

- **Padrão: 200 requisições/hora e 20.000/mês** — https://www.pexels.com/api/documentation/
- Headers de controle em respostas 2xx: `X-Ratelimit-Limit`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset` (timestamp UNIX). **Ausentes em respostas não-2xx** — https://www.pexels.com/api/documentation/
- Limite pode ser removido de graça: "If you meet our API terms, you can get unlimited requests for free", condicionado a mostrar atribuição adequada — https://www.pexels.com/api/documentation/ e https://help.pexels.com/hc/en-us/categories/900001326143-API

**Licença do conteúdo** — https://www.pexels.com/license/
- Permitido: uso gratuito, inclusive comercial; **atribuição não é obrigatória** ("not necessary but always appreciated"); modificar à vontade; usar em sites, apps, marketing, impressos e redes sociais.
- Proibido: mostrar pessoas identificáveis de forma ofensiva ou negativa; **vender cópias não modificadas** (pôster, impressão, produto físico); sugerir endosso de pessoas ou marcas da imagem; **redistribuir ou vender em outras plataformas de banco de imagem ou de wallpaper**; usar como marca registrada, nome comercial ou marca de serviço.
- Termos gerais: a licença concede direito "irrevocable, worldwide, perpetual… non-exclusive and royalty-free right to download, use, copy, modify or adapt the Content for commercial or non-commercial purposes"; proíbe cópia em massa/sistemática sem permissão e compilar conteúdo para "replicate a similar or competing service" — https://www.pexels.com/terms-of-service/
- Proibido distribuir o conteúdo "on a Standalone basis" e usar a API para coletar em escala para treinar ou avaliar modelos de ML/IA sem permissão — https://help.pexels.com/hc/en-us/articles/22114560160409-Terms-Policy-Update-2024 (lido via resumo de busca; a página retorna 403 a acesso automatizado).

**Regras da API (diretrizes)** — https://www.pexels.com/api/documentation/
- "Whenever you are doing an API request make sure to show a prominent link to Pexels" (ex.: "Photos provided by Pexels").
- Creditar o fotógrafo sempre que possível ("Photo by [nome] on Pexels", com link).
- Não replicar a funcionalidade central do Pexels nem usar como app de wallpaper; o abuso leva ao encerramento do acesso.

## Erros conhecidos e tratamento

- **429**: limite estourado. Como os headers `X-Ratelimit-*` não vêm em respostas não-2xx, o tempo de espera deve ser calculado a partir do último `X-Ratelimit-Reset` de uma resposta 2xx — https://www.pexels.com/api/documentation/
- Demais códigos (401 chave inválida, 404, 5xx) e corpo do erro: NÃO DOCUMENTADO na documentação da API.
- Tratamento recomendado a partir do que existe: ler `X-Ratelimit-Remaining` a cada resposta e parar antes de zerar; 5xx com backoff.

## Riscos para a nossa implementação

1. **Redistribuição:** a licença permite usar a mídia **dentro** de uma peça (reel, post, apresentação), inclusive comercialmente e modificada. **Não permite redistribuir os arquivos soltos** ("standalone") nem colocá-los em outra plataforma de banco de imagens. Consequências:
   - O ExpxMedia **não pode empacotar mídia do Pexels** no produto distribuído, nem em templates da `galeria_compartilhada` publicados no GitHub. Templates devem guardar **a consulta ou o ID do Pexels**, e o download acontece na máquina de quem usa, com a chave dela.
   - Cache local por instalação para uso nas peças é compatível com a licença. Cache compartilhado entre instalações pode ser lido como "bulk copying" ou banco concorrente (termos) — evitar.
2. **Atribuição:** a licença não exige crédito na peça final, mas as **diretrizes da API exigem link visível para o Pexels onde a busca é exibida** (ex.: na tela/lista de resultados que o motor mostrar). Recomenda-se gravar `photographer`/`user` e `url` nos metadados da peça.
3. **200 req/h** é baixo para um reel com vários b-rolls e buscas de refinamento: o motor precisa contar requisições, usar `per_page` alto (até 80) e cache de resultados por consulta.
4. **Pessoas identificáveis e marcas:** usar b-roll com pessoas em contexto negativo, ou dando a entender endosso, viola a licença. É uma decisão editorial que o motor não consegue checar sozinho.
5. `src` de foto só tem tamanhos fixos ou `original`; para 1080×1920 exato é preciso baixar `original` (ou `portrait`, 800×1200, abaixo de 1080p) e recortar localmente.
6. Vídeo: escolher em `video_files[]` pelo `width`/`height`/`fps`, porque `quality` não é enumerado na doc.
7. A página de termos específica da API (`https://www.pexels.com/api/terms/`) respondeu 403 ao acesso automatizado; texto integral não conferido.

## Fonte

Acesso em 2026-09-24:

- https://www.pexels.com/api/documentation/
- https://www.pexels.com/license/
- https://www.pexels.com/terms-of-service/
- https://help.pexels.com/hc/en-us/categories/900001326143-API (via busca)
- https://help.pexels.com/hc/en-us/articles/22114560160409-Terms-Policy-Update-2024 (via busca)
- https://www.pexels.com/api/terms/ (tentado, HTTP 403)

// Monta a linha do tempo e a trilha de uma peça de motion feita sob medida (D-19). Porta generalizada de
// Instragram-Videos/remotion/scripts/montar-reel.mjs: os caminhos chegam por argumento e nada é escrito fora
// de --saida (a origem reescrevia src/reels/registro.ts e public/ do próprio projeto; aqui o registro das
// composições é do scripts/registrar.mjs e a mídia vai para a pasta de saída, que vira o public dir do render).
//
//   node scripts/montar.mjs --reel <pasta com cenas.json> --narracao <mp3> --alinhamento <json> --saida <pasta>
//                           [--assinaturas <json>] [--avatar <mp4>] [--leitura <md>]
//   node scripts/montar.mjs --assinatura --reel <pasta com cenas.json>     # imprime a assinatura da trilha
//
// Grava em --saida:
//   timeline.json   frames de cada cena, eventos, blocos de legenda palavra a palavra
//   narracao.mp3    cópia da narração
//   trilha.wav      música + efeitos sintetizados em scripts/audio.mjs
//   avatar.mp4      só quando cenas.json diz "apresentador": true (exige --avatar)
//
// --assinaturas: lista JSON das trilhas de outras peças, [{ "reel": id, "trilha": {...} } | { "reel": id,
// "assinatura": "<saída de --assinatura>" }]. Trilha com a mesma assinatura (bpm, acordes e nomes dos
// instrumentos) é recusada: cada peça tem a sua. Quem guarda a lista é o motor, não este script.
//
// cenas.json (origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:11-22):
// {
//   "trilha": { "bpm": 100, "acordes": [[110, [440, 523.25, 659.25]], ...], "instrumentos": {"kick": 0.35, ...},
//               "arpejo": [0,1,2,...], "ganho": 0.55, "fade_s": 1.6, "semente": 7 },
//   "troca": [{ "f": -3, "tipo": "whoosh", "desde": 1 }, ...],       // som em toda troca de cena (frames relativos)
//   "legenda": { "palavras_por_bloco": 3 },
//   "cauda_s": 1.4,
//   "apresentador": true,       // a referência tem gente falando: exige --avatar
//   "cenas": [{ "id": "abertura", "ancora": "primeiras palavras", "ev": {"entra": 0.2}, "sons": [["entra", "pop"], ["0", "passos", 0.5]], ...livre }]
// }
// `ev` são frações da duração da cena; um som referencia um evento ("entra"), "0" ou uma soma ("i0+viagem"), e o
// terceiro item, quando existe, é a duração como fração da cena. A cena recebe os mesmos eventos, então som e
// imagem batem mesmo se a narração mudar.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { criarMix } from "./audio.mjs";

const AQUI = path.dirname(fileURLToPath(import.meta.url));

const falha = (m, codigo = 1) => {
  console.error(`ERRO: ${m}`);
  process.exit(codigo);
};

// O fps é o da constante única do kit (D-17): lido de src/kit/constantes.ts, nunca repetido aqui.
const lerFps = () => {
  const arq = path.resolve(AQUI, "..", "src", "kit", "constantes.ts");
  const m = /export const FPS = (\d+);/.exec(fs.readFileSync(arq, "utf8"));
  if (!m) falha(`não achei "export const FPS = <n>;" em ${arq}`);
  return Number(m[1]);
};

// ---------- argumentos ----------
const USO =
  "uso: node scripts/montar.mjs --reel <pasta com cenas.json> --narracao <mp3> --alinhamento <json> --saida <pasta>" +
  " [--assinaturas <json>] [--avatar <mp4>] [--leitura <md>]\n" +
  "     node scripts/montar.mjs --assinatura --reel <pasta com cenas.json>";
const COM_VALOR = new Set(["--reel", "--narracao", "--alinhamento", "--saida", "--assinaturas", "--avatar", "--leitura"]);
const args = {};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--assinatura") args.assinatura = true;
  else if (COM_VALOR.has(a) && i + 1 < argv.length) args[a.slice(2)] = argv[++i];
  else falha(`argumento desconhecido ou sem valor: ${a}\n${USO}`, 2);
}

// Assinatura da trilha: só bpm, acordes e o conjunto de nomes dos instrumentos.
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:58
const assinatura = (t) => JSON.stringify({ bpm: t.bpm, acordes: t.acordes, instrumentos: Object.keys(t.instrumentos || {}).sort() });

const lerSpec = () => {
  if (!args.reel) falha(`falta --reel\n${USO}`, 2);
  const arq = path.join(args.reel, "cenas.json");
  if (!fs.existsSync(arq)) falha(`falta cenas.json do reel: ${arq}`);
  const spec = JSON.parse(fs.readFileSync(arq, "utf8"));
  if (!spec.trilha?.bpm || !spec.trilha?.acordes?.length) falha("cenas.json sem trilha.bpm e trilha.acordes");
  return spec;
};

if (args.assinatura) {
  console.log(JSON.stringify(assinatura(lerSpec().trilha)));
  process.exit(0);
}

const faltando = ["reel", "narracao", "alinhamento", "saida"].filter((k) => !args[k]);
if (faltando.length) falha(`faltam ${faltando.map((k) => `--${k}`).join(", ")}\n${USO}`, 2);

const FPS = lerFps();
const nome = path.basename(path.resolve(args.reel));
for (const [p, o] of [[args.alinhamento, "alinhamento da narração (--alinhamento)"], [args.narracao, "narração (--narracao)"]]) {
  if (!fs.existsSync(p)) falha(`falta ${o}: ${p}`);
}
// A leitura da referência vem ANTES do código (no 1º pedido real ela foi escrita depois do roteiro e da
// narração). origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:48-52
if (args.leitura && !fs.existsSync(args.leitura)) {
  falha(`falta ${args.leitura}: leia as folhas da referência e escreva a leitura antes de montar.`);
}
const spec = lerSpec();
const al = JSON.parse(fs.readFileSync(args.alinhamento, "utf8"));

// ---------- a trilha não pode repetir a de outra peça ----------
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:56-66 (lá, varrendo src/reels; aqui, a lista do argumento)
if (args.assinaturas) {
  const lista = JSON.parse(fs.readFileSync(args.assinaturas, "utf8"));
  if (!Array.isArray(lista)) falha(`--assinaturas precisa ser uma lista JSON: ${args.assinaturas}`);
  const minha = assinatura(spec.trilha);
  for (const outro of lista) {
    const dela = typeof outro.assinatura === "string" ? outro.assinatura : outro.trilha ? assinatura(outro.trilha) : null;
    if (dela === minha) {
      falha(`a trilha é a mesma do reel ${outro.reel} (bpm, acordes e instrumentos). Cada reel tem a sua: mude andamento, harmonia ou timbre.`);
    }
  }
}

// ---------- palavras com tempo ----------
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:68-83
const palavras = [];
let atual = null;
al.characters.forEach((c, i) => {
  const t0 = al.character_start_times_seconds[i];
  const t1 = al.character_end_times_seconds[i];
  if (/\s/.test(c)) {
    if (atual) palavras.push(atual);
    atual = null;
    return;
  }
  if (!atual) atual = { w: "", t0, t1 };
  atual.w += c;
  atual.t1 = t1;
});
if (atual) palavras.push(atual);
if (!palavras.length) falha("o alinhamento da narração não tem nenhuma palavra");

// Âncora: minúsculas, sem acento, só [a-z0-9]; primeira ocorrência em ordem; a cena entra 0,12 s antes da
// palavra (a primeira em 0). origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:85-97
const RECUO_S = 0.12;
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
const pn = palavras.map((p) => norm(p.w));
let cursor = 0;
const inicios = spec.cenas.map((c, n) => {
  const alvo = c.ancora.split(/\s+/).map(norm).filter(Boolean);
  for (let i = cursor; i < pn.length; i++) {
    if (alvo.every((a, k) => pn[i + k] === a)) {
      cursor = i + 1;
      return n === 0 ? 0 : Math.max(0, palavras[i].t0 - RECUO_S);
    }
  }
  return falha(`cena ${n + 1} (${c.id}): âncora "${c.ancora}" não casou com a narração, em ordem`);
});

// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:99-109 (cauda 1.4 s; aviso abaixo de 1 s de cena)
const CAUDA_S = 1.4;
const fimNarr = palavras[palavras.length - 1].t1;
const totalFrames = Math.round((fimNarr + (spec.cauda_s ?? CAUDA_S)) * FPS);
const cenas = spec.cenas.map((c, i) => {
  const inicio = Math.round(inicios[i] * FPS);
  const fim = i + 1 < inicios.length ? Math.round(inicios[i + 1] * FPS) : totalFrames;
  const { ancora, sons, ...resto } = c;
  return { ...resto, ev: c.ev || {}, inicio, dur: fim - inicio };
});
cenas.forEach((c) => {
  if (c.dur < FPS) console.warn(`aviso: cena ${c.id} dura ${(c.dur / FPS).toFixed(2)}s — curta demais para a animação respirar`);
});

// Legenda em blocos de N palavras (3 por padrão), fechando em pontuação.
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:111-121
const porBloco = spec.legenda?.palavras_por_bloco ?? 3;
const blocos = [];
let buf = [];
palavras.forEach((p, i) => {
  buf.push({ w: p.w, f0: Math.round(p.t0 * FPS), f1: Math.round(p.t1 * FPS) });
  if (buf.length === porBloco || /[.,:?!]$/.test(p.w) || i === palavras.length - 1) {
    blocos.push(buf);
    buf = [];
  }
});

// ---------- eventos de som ----------
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:123-142 (troca padrão: whoosh em -3 desde a cena 1, pop em 5 desde a 0)
const evFrame = (cena, ref) =>
  cena.inicio +
  Math.round(
    ref.split("+").reduce((s, k) => {
      if (k === "0") return s;
      if (!(k in cena.ev)) falha(`cena ${cena.id}: som cita o evento "${k}", que não está em ev`);
      return s + cena.ev[k];
    }, 0) * cena.dur,
  );
const sons = [];
const troca = spec.troca ?? [{ f: -3, tipo: "whoosh", desde: 1 }, { f: 5, tipo: "pop", desde: 0 }];
cenas.forEach((c, i) => {
  troca.forEach((t) => {
    if (i >= (t.desde ?? 1)) sons.push({ f: c.inicio + t.f, tipo: t.tipo, vol: t.vol });
  });
  (spec.cenas[i].sons || []).forEach(([ref, tipo, durFrac, vol]) => {
    sons.push({ f: evFrame(c, ref), tipo, dur: durFrac ? (durFrac * c.dur) / FPS : undefined, vol });
  });
});

// Apresentador: vídeo do avatar gerado da mesma narração; foto parada no lugar de quem fala foi reprovada.
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:148-156
if (spec.apresentador && (!args.avatar || !fs.existsSync(args.avatar))) {
  falha('cenas.json diz "apresentador": true e falta o vídeo do avatar (--avatar), gerado da mesma narração.');
}

// ---------- trilha (antes de gravar qualquer coisa: efeito desconhecido falha sem deixar saída pela metade) ----------
// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:158-161 (0,5 s de sobra, semente 7)
const mix = criarMix(totalFrames / FPS + 0.5, spec.trilha.semente ?? 7);
mix.musica(spec.trilha, totalFrames / FPS);
try {
  sons.forEach((s) => mix.efeito(s.tipo, s.f / FPS, s.dur, s.vol));
} catch (e) {
  falha(e.message);
}

// ---------- gravação, só em --saida ----------
const saida = path.resolve(args.saida);
fs.mkdirSync(saida, { recursive: true });
const gravarAtomico = (destino, escrever) => {
  const tmp = path.join(path.dirname(destino), `.${path.basename(destino)}.${process.pid}.tmp`);
  try {
    escrever(tmp);
    fs.renameSync(tmp, destino);
  } finally {
    if (fs.existsSync(tmp)) fs.rmSync(tmp);
  }
};
gravarAtomico(path.join(saida, "timeline.json"), (t) =>
  fs.writeFileSync(t, JSON.stringify({ fps: FPS, totalFrames, cenas, blocos }, null, 1)),
);
if (path.resolve(args.narracao) !== path.join(saida, "narracao.mp3")) {
  gravarAtomico(path.join(saida, "narracao.mp3"), (t) => fs.copyFileSync(args.narracao, t));
}
if (spec.apresentador && path.resolve(args.avatar) !== path.join(saida, "avatar.mp4")) {
  gravarAtomico(path.join(saida, "avatar.mp4"), (t) => fs.copyFileSync(args.avatar, t));
}
gravarAtomico(path.join(saida, "trilha.wav"), (t) => mix.gravarWav(t));

// origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:180-181
console.log(`${nome}: ${cenas.length} cenas · ${totalFrames} frames (${(totalFrames / FPS).toFixed(1)}s) · ${sons.length} efeitos`);
cenas.forEach((c) => console.log(`  ${c.id.padEnd(14)} ${(c.inicio / FPS).toFixed(2)}s  +${(c.dur / FPS).toFixed(2)}s`));

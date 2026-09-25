import React from "react";
import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from "remotion";
import {
  FPS,
  ProvedorAlma,
  REEL,
  SeloPerfil,
  centralizarNaArea,
  mola,
  pilhaFonte,
  rampa,
  urlDoArquivo,
  useAlma,
  type PropsAlma,
} from "@expxmedia/template";
import { CARTAO, CENAS, tintaDoCartao, type CenaT } from "./cenas";

// Template "narrado em cartão": reel vertical narrado, na estrutura do reel sob medida aprovado — fundo fixo,
// etiqueta de duas linhas, cartão com a cena, barra de progresso por cena, legenda por blocos palavra a palavra
// e o selo de quem publica —, genérico. Tudo que é marca chega por props: cores, fontes, porta-voz e canal pela
// Alma (useAlma); textos pelos slots de cada cena; a linha do tempo pela montagem do motor (scripts/montar.mjs);
// narração e trilha como arquivos do public dir do render.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:1-192

type Palavra = { w: string; f0: number; f1: number };
export type Timeline = { fps: number; totalFrames: number; cenas: CenaT[]; blocos: Palavra[][] };

export type PropsComposicao = {
  alma: PropsAlma;
  timeline: Timeline;
  audio: { narracao: string | null; trilha: string | null };
  // palavra do CTA declarada na peça: ganha destaque na legenda quando é dita
  cta: string | null;
  // "legenda": só a camada da legenda, sem fundo e sem som (o motor tira dela os cartões da verificação)
  camada: "tudo" | "legenda";
};

// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:18 (cartão x 60, y 330, 960 x 780)
const CARD = { x: 60, y: 330, w: CARTAO.w, h: CARTAO.h };
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:19 (12 quadros de sobreposição)
const TRANS = 12;
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:189 (trilha a 0.8, abaixo da voz)
const VOLUME_TRILHA = 0.8;
// Bloco desenhado entre y 124 e 1482, centrado na área segura.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:176-178
const BLOCO = { topo: 124, base: 1482 };
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:186
const Y_SELO = 1392;

const mistura = (a: string, pct: number, b: string) => `color-mix(in srgb, ${a} ${pct}%, ${b})`;
const normalizar = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]/g, "").toUpperCase();

// Etiqueta de duas linhas acima do cartão, com o ícone girando.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:22-59 (top CARD.y − 62, altura 116,
// largura maior linha × 25 + 160, mola 3/11/170, giro f × 3 graus)
const Etiqueta: React.FC<{ linhas: string[]; f: number }> = ({ linhas, f }) => {
  const { cores, fontes } = useAlma();
  const s = mola(f, 3, 11, 170);
  const larg = Math.max(...linhas.map((t) => t.length), 1) * 25 + 160;
  return (
    <div style={{ position: "absolute", left: REEL.largura / 2 - larg / 2, top: CARD.y - 62, width: larg, height: 116,
      transform: `scale(${s})`, background: cores.fundo, borderRadius: 18, boxShadow: "0 8px 24px rgba(0, 0, 0, 0.16)",
      display: "flex", alignItems: "center", gap: 18, padding: "0 26px", zIndex: 5 }}>
      <svg width={62} height={62} style={{ flex: "none" }}>
        <circle cx={31} cy={31} r={31} fill={cores.destaque} />
        <g transform={`translate(31,31) rotate(${f * 3})`}>
          {[0, 60, 120].map((a) => (
            <rect key={a} x={-4} y={-19} width={8} height={38} rx={4} fill={cores.texto_inverso} transform={`rotate(${a})`} />
          ))}
        </g>
      </svg>
      <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 36, lineHeight: 1.1, letterSpacing: -0.5,
        whiteSpace: "nowrap", textTransform: "uppercase" }}>
        <div style={{ color: cores.texto }}>{linhas[0] ?? ""}</div>
        {linhas[1] ? <div style={{ color: cores.destaque }}>{linhas[1]}</div> : null}
      </div>
    </div>
  );
};

// Cartão da cena: wipe circular na entrada e zoom de 1.05 para 1.00.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:61-83
// (circle(0→160% at 100% 45%) em TRANS quadros; zoom em 20 quadros; raio 40)
const Cartao: React.FC<{ c: CenaT; indice: number }> = ({ c, indice }) => {
  const f = useCurrentFrame();
  const { cores } = useAlma();
  const Cena = CENAS[c.kind];
  if (!Cena) throw new Error(`cena ${c.id}: kind "${c.kind}" não existe neste template (${Object.keys(CENAS).join(", ")})`);
  const ev = (nome: string) => (nome === "0" ? 0 : Math.round((c.ev?.[nome] ?? 0) * c.dur));
  const t = tintaDoCartao(c.kind, indice, cores);
  const wipe = indice === 0 ? 160 : rampa(f, 0, TRANS, 0, 160);
  const zoom = 1.05 - 0.05 * rampa(f, 0, 20);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: CARD.x, top: CARD.y, width: CARD.w, height: CARD.h, borderRadius: 40, overflow: "hidden",
        background: t.fundo, clipPath: `circle(${wipe}% at 100% 45%)`, boxShadow: "0 18px 40px rgba(0, 0, 0, 0.22)" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: CARD.w, height: CARD.h, transform: `scale(${zoom})` }}>
          <Cena f={f} d={c.dur} ev={ev} cena={c} t={t} />
        </div>
      </div>
      <Etiqueta linhas={Array.isArray(c.etiqueta) ? c.etiqueta : []} f={f} />
    </AbsoluteFill>
  );
};

// Barra de progresso: um ponto por cena, a cabeça anda com mola até o ponto da cena atual, pontos feitos viram
// tique, o último ponto é a bandeira. origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:85-132
// (y 170, de x 100 a 980, raio 22, mola 13, balanço sin(f/5) × 6)
const Progresso: React.FC<{ f: number; cenas: CenaT[] }> = ({ f, cenas }) => {
  const { cores, fontes } = useAlma();
  const n = cenas.length;
  const x0 = 100;
  const x1 = 980;
  const xs = cenas.map((_, i) => (n > 1 ? x0 + (i * (x1 - x0)) / (n - 1) : x0));
  let idx = 0;
  cenas.forEach((c, i) => {
    if (f >= c.inicio) idx = i;
  });
  const m = idx === 0 ? 1 : mola(f, cenas[idx].inicio, 13);
  const xCab = idx === 0 ? xs[0] : xs[idx - 1] + (xs[idx] - xs[idx - 1]) * m;
  const y = 170;
  const trilho = mistura(cores.apoio, 30, cores.fundo);
  return (
    <svg width={REEL.largura} height={260} style={{ position: "absolute", left: 0, top: 0 }}>
      <rect x={x0} y={y - 8} width={x1 - x0} height={16} rx={8} fill={trilho} />
      <rect x={x0} y={y - 8} width={Math.max(0, xCab - x0)} height={16} rx={8} fill={cores.destaque} />
      {xs.map((x, i) => {
        const feito = i < idx;
        if (i === n - 1 && !feito && n > 1) {
          return (
            <g key={i} transform={`translate(${x},${y})`}>
              <rect x={-4} y={-30} width={8} height={52} rx={3} fill={cores.texto} />
              <path d="M 4 -30 L 34 -20 L 4 -8 Z" fill={cores.destaque} />
            </g>
          );
        }
        const pop = feito && i + 1 < n ? mola(f, cenas[i + 1].inicio + 8, 8) : 0;
        return (
          <g key={i} transform={`translate(${x},${y})`}>
            <circle r={22} fill={feito ? cores.positivo : cores.fundo} stroke={feito ? cores.positivo : trilho} strokeWidth={4}
              transform={`scale(${feito ? 0.8 + 0.2 * pop : 1})`} />
            {feito ? (
              <path d="M -9 0 L -2 7 L 10 -7" stroke={cores.texto_inverso} strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ) : (
              <text textAnchor="middle" y={8} fontFamily={pilhaFonte(fontes.texto)} fontWeight={800} fontSize={22} fill={cores.apoio}>{i + 1}</text>
            )}
          </g>
        );
      })}
      <g transform={`translate(${xCab},${y - 4 - Math.abs(Math.sin(f / 5)) * 6})`}>
        <circle r={36} fill={cores.fundo} stroke={cores.destaque} strokeWidth={6} />
        <path d="M -10 -15 L 16 0 L -10 15 Z" fill={cores.destaque} />
      </g>
    </svg>
  );
};

// Legenda por blocos: o bloco entra 2 quadros antes da primeira palavra, com mola; palavra dita na cor de
// destaque, não dita apagada; a palavra do CTA ganha a pílula quando é dita.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:134-165
// (top 1135, altura 240, margem 60, 90 px, mola 12/200, desce 6 px antes de ser dita)
const Legenda: React.FC<{ f: number; blocos: Palavra[][]; cta: string | null }> = ({ f, blocos, cta }) => {
  const { cores, fontes } = useAlma();
  let atual = -1;
  blocos.forEach((b, i) => {
    if (b.length && f >= b[0].f0 - 2) atual = i;
  });
  if (atual < 0) return null;
  const b = blocos[atual];
  const s = mola(f, b[0].f0 - 2, 12, 200);
  const chave = cta ? normalizar(cta) : null;
  const tamanho = b.map((p) => p.w).join(" ").length > 26 ? 76 : 90;
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 1135, height: 240, display: "flex", alignItems: "center",
      justifyContent: "center", flexWrap: "wrap", columnGap: 26, textAlign: "center",
      transform: `translateY(${(1 - s) * 30}px) scale(${0.9 + 0.1 * s})`, opacity: s }}>
      {b.map((p, i) => {
        const dito = f >= p.f0;
        const ehCta = chave !== null && normalizar(p.w) === chave;
        return (
          <span key={i} style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: tamanho, lineHeight: 1.08,
            color: ehCta && dito ? cores.texto_inverso : dito ? cores.destaque : mistura(cores.apoio, 45, cores.fundo),
            background: ehCta && dito ? cores.destaque : "transparent", borderRadius: 16, padding: ehCta ? "0 14px" : 0,
            transform: `translateY(${dito ? 0 : 6}px)` }}>
            {p.w}
          </span>
        );
      })}
    </div>
  );
};

const Tela: React.FC<Omit<PropsComposicao, "alma">> = ({ timeline, audio, cta, camada }) => {
  const f = useCurrentFrame();
  const { cores } = useAlma();
  const legenda = (
    <AbsoluteFill style={centralizarNaArea(BLOCO.topo, BLOCO.base)}>
      <Legenda f={f} blocos={timeline.blocos} cta={cta} />
    </AbsoluteFill>
  );
  if (camada === "legenda") return legenda;
  const n = timeline.cenas.length;
  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 20% 90%, ${cores.fundo_alt} 0, transparent 40%), radial-gradient(circle at 90% 10%, ${mistura(cores.fundo_alt, 45, cores.fundo)} 0, transparent 45%)` }} />
      <AbsoluteFill style={centralizarNaArea(BLOCO.topo, BLOCO.base)}>
        {timeline.cenas.map((c, i) => (
          <Sequence key={c.id} from={c.inicio} durationInFrames={c.dur + (i < n - 1 ? TRANS : 0)} name={c.id}>
            <Cartao c={c} indice={i} />
          </Sequence>
        ))}
        <Progresso f={f} cenas={timeline.cenas} />
        <SeloPerfil f={f} y={Y_SELO} />
      </AbsoluteFill>
      {legenda}
      {audio.narracao ? <Audio src={urlDoArquivo(audio.narracao)} /> : null}
      {audio.trilha ? <Audio src={urlDoArquivo(audio.trilha)} volume={VOLUME_TRILHA} /> : null}
    </AbsoluteFill>
  );
};

export const Composicao: React.FC<PropsComposicao> = ({ alma, ...resto }) => (
  <ProvedorAlma alma={alma}>
    <Tela {...resto} />
  </ProvedorAlma>
);

// Metadados da composição; o motor acrescenta o id ao registrar o template para um render.
export const composicao = {
  component: Composicao,
  fps: FPS,
  width: REEL.largura,
  height: REEL.altura,
  durationInFrames: 1,
  defaultProps: {} as PropsComposicao,
  calculateMetadata: ({ props }: { props: PropsComposicao }) => ({ durationInFrames: props.timeline.totalFrames }),
};

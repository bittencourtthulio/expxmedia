import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, useCurrentFrame } from "remotion";
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
import { CENAS, FUNDOS, PALETA, normalizar, type CenaT } from "./cenas";

// Reel sob medida do slug ref-validacao. Imita a referência lida em ../../analise/leitura.md:
// - dois modos de tela que se alternam: "dividida" (cartão de interface em cima, apresentador embaixo, legenda
//   em chip escuro na costura) e "cheia" (desenho no terço de cima e a palavra falada grande no meio);
// - troca quase seca, com o cartão entrando por uma mola curta (a cena cuida disso);
// - legenda da tela cheia construída palavra a palavra, com palavra-chave colorida ou em serifa itálica.
// O apresentador é o avatar do porta-voz, gerado do áudio da narração (audio.avatar, por props).

type Palavra = { w: string; f0: number; f1: number };
export type Timeline = { fps: number; totalFrames: number; cenas: CenaT[]; blocos: Palavra[][] };

export type PropsReel = {
  alma: PropsAlma;
  timeline: Timeline;
  audio: { narracao: string | null; trilha: string | null; avatar: string | null };
};

// Sobreposição curta entre cenas: na referência a troca é quase um corte seco.
const TRANS = 4;
const VOLUME_TRILHA = 0.8;
const ENTRA_ANTES = 2;
// O desenho vai de 236 a 1484 (1248 px): cabe inteiro na área segura, centrado, sem encolher.
const BLOCO = { topo: 236, base: 1484 };
// Tela dividida: apresentador de borda a borda entre 770 e 1340 (como na referência, sem moldura), chip da
// legenda sentado na costura (y 770).
const APRESENTADOR = { topo: 770, base: 1340, lado: 0 };
const COSTURA = 770;
// Tela cheia: a palavra grande no meio do bloco.
const GRANDE = { topo: 820, altura: 260, tamanho: 96 };
const Y_SELO = 1362;

const Cena: React.FC<{ c: CenaT; primeira: boolean }> = ({ c, primeira }) => {
  const f = useCurrentFrame();
  const Componente = CENAS[c.id];
  if (!Componente) throw new Error(`cena ${c.id}: falta o componente em CENAS (cenas.tsx)`);
  const ev = (nome: string) => {
    if (nome === "0") return 0;
    const fracao = c.ev[nome];
    if (fracao === undefined) throw new Error(`cena ${c.id}: evento "${nome}" não está em ev do cenas.json`);
    return Math.round(fracao * c.dur);
  };
  const entrada = primeira ? 1 : rampa(f, 0, TRANS);
  return (
    <AbsoluteFill style={{ opacity: entrada, background: FUNDOS[c.id] ?? PALETA.fundo }}>
      <Componente f={f} d={c.dur} ev={ev} cena={c} />
    </AbsoluteFill>
  );
};

const cenaNoQuadro = (cenas: CenaT[], f: number): CenaT => {
  let atual = cenas[0];
  cenas.forEach((c) => {
    if (f >= c.inicio) atual = c;
  });
  return atual;
};

const blocoNoQuadro = (blocos: Palavra[][], f: number): Palavra[] | null => {
  let atual = -1;
  blocos.forEach((b, i) => {
    if (b.length && f >= b[0].f0 - ENTRA_ANTES) atual = i;
  });
  return atual < 0 ? null : blocos[atual];
};

const lista = (c: CenaT, campo: string): string[] => ((c[campo] as string[] | undefined) ?? []).map(normalizar);

// Tela dividida: chip escuro, caixa alta, o bloco inteiro de uma vez (na referência o chip troca de bloco).
const Chip: React.FC<{ f: number; bloco: Palavra[] }> = ({ f, bloco }) => {
  const { fontes } = useAlma();
  const s = mola(f, bloco[0].f0 - ENTRA_ANTES, 14, 260);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: COSTURA - 34, display: "flex", justifyContent: "center",
      zIndex: 5 }}>
      <div style={{ background: PALETA.chip, color: PALETA.branco, fontFamily: pilhaFonte(fontes.texto), fontWeight: 700,
        fontSize: 40, letterSpacing: 3, padding: "10px 22px", textTransform: "uppercase", lineHeight: 1.1,
        transform: `scale(${0.92 + 0.08 * s})`, opacity: s }}>
        {bloco.map((p) => p.w).join(" ")}
      </div>
    </div>
  );
};

// Tela cheia: a palavra grande, construída palavra a palavra; chave em vermelho ou verde, nome em serifa itálica.
const Grande: React.FC<{ f: number; bloco: Palavra[]; cena: CenaT }> = ({ f, bloco, cena }) => {
  const { fontes } = useAlma();
  const vermelho = lista(cena, "vermelho");
  const verde = lista(cena, "verde");
  const italico = lista(cena, "italico");
  const ditas = bloco.filter((p) => f >= p.f0 - ENTRA_ANTES);
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: GRANDE.topo, height: GRANDE.altura, display: "flex",
      alignItems: "center", justifyContent: "center", flexWrap: "wrap", columnGap: 26, textAlign: "center" }}>
      {ditas.map((p, i) => {
        const n = normalizar(p.w);
        const s = mola(f, p.f0 - ENTRA_ANTES, 14, 260);
        const serifa = italico.includes(n);
        const cor = vermelho.includes(n) ? PALETA.vermelho : verde.includes(n) ? PALETA.verde : PALETA.tinta;
        return (
          <span key={i} style={{ fontFamily: pilhaFonte(serifa ? fontes.titulo : fontes.texto), fontWeight: serifa ? 700 : 800,
            fontStyle: serifa ? "italic" : "normal", fontSize: GRANDE.tamanho, lineHeight: 1.12, color: cor,
            opacity: s, transform: `translateY(${(1 - s) * 18}px)` }}>
            {p.w}
          </span>
        );
      })}
    </div>
  );
};

// O porta-voz falando (avatar gerado do áudio da narração). Toca o vídeo inteiro em sincronia com a narração
// e só aparece nas cenas de tela dividida, como o apresentador da referência.
const Apresentador: React.FC<{ src: string; visivel: number }> = ({ src, visivel }) => (
  <div style={{ position: "absolute", left: APRESENTADOR.lado, right: APRESENTADOR.lado, top: APRESENTADOR.topo,
    height: APRESENTADOR.base - APRESENTADOR.topo, borderRadius: 0, overflow: "hidden", opacity: visivel,
    background: PALETA.chip }}>
    <OffthreadVideo src={urlDoArquivo(src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  </div>
);

const Tela: React.FC<Omit<PropsReel, "alma">> = ({ timeline, audio }) => {
  const f = useCurrentFrame();
  if (timeline.fps !== FPS) throw new Error(`linha do tempo a ${timeline.fps} fps; o kit roda a ${FPS}`);
  const n = timeline.cenas.length;
  const cena = cenaNoQuadro(timeline.cenas, f);
  const dividida = cena.tela === "dividida";
  const bloco = blocoNoQuadro(timeline.blocos, f);
  const visivel = dividida ? rampa(f, cena.inicio, cena.inicio + TRANS) : 0;
  return (
    <AbsoluteFill style={{ background: PALETA.fundo }}>
      <AbsoluteFill style={centralizarNaArea(BLOCO.topo, BLOCO.base)}>
        {timeline.cenas.map((c, i) => (
          <Sequence key={c.id} from={c.inicio} durationInFrames={c.dur + (i < n - 1 ? TRANS : 0)} name={c.id}>
            <Cena c={c} primeira={i === 0} />
          </Sequence>
        ))}
        {audio.avatar ? <Apresentador src={audio.avatar} visivel={visivel} /> : null}
        {bloco ? (dividida ? <Chip f={f} bloco={bloco} /> : <Grande f={f} bloco={bloco} cena={cena} />) : null}
        <SeloPerfil f={f} y={Y_SELO} />
      </AbsoluteFill>
      {audio.narracao ? <Audio src={urlDoArquivo(audio.narracao)} /> : null}
      {audio.trilha ? <Audio src={urlDoArquivo(audio.trilha)} volume={VOLUME_TRILHA} /> : null}
    </AbsoluteFill>
  );
};

export const Reel: React.FC<PropsReel> = ({ alma, ...resto }) => (
  <ProvedorAlma alma={alma}>
    <Tela {...resto} />
  </ProvedorAlma>
);

export const composicao = {
  component: Reel,
  fps: FPS,
  width: REEL.largura,
  height: REEL.altura,
  durationInFrames: 1,
  defaultProps: {} as PropsReel,
  calculateMetadata: ({ props }: { props: PropsReel }) => ({ durationInFrames: props.timeline.totalFrames }),
};

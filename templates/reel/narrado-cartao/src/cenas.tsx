import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { clamp, mola, pilhaFonte, rampa, useAlma, type CoresAlma } from "@expxmedia/template";

// Cenas do template "narrado em cartão". Cada cena desenha o miolo do cartão (960 x 780) e recebe o frame
// local, a duração, ev(nome) (o frame local de um evento de cenas.json, o mesmo que dispara o som na
// trilha) e a tinta do cartão. Estrutura do reel sob medida aprovado (cartão, eventos por fração da cena),
// mas genérica: nenhum texto, cor, fonte ou desenho de empresa; tudo que é marca vem da Alma (useAlma) e
// todo texto vem dos slots da cena.
// origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.tsx:7 (f, d, ev)

export const CARTAO = { w: 960, h: 780 } as const;

// Campos que a montagem (scripts/montar.mjs) devolve para cada cena, mais os slots do kind.
export type CenaT = {
  id: string;
  kind: string;
  etiqueta: string[];
  ev: Record<string, number>;
  inicio: number;
  dur: number;
  [slot: string]: unknown;
};

// Cores do cartão, derivadas só dos papéis da Alma. Os pares são os que o contrato garante legíveis:
// texto sobre fundo, texto_inverso sobre texto ou sobre destaque.
export type Tinta = { fundo: string; tinta: string; acento: string; suave: string; apoio: string };

const mistura = (a: string, pct: number, b: string) => `color-mix(in srgb, ${a} ${pct}%, ${b})`;

export const tintaDoCartao = (kind: string, indice: number, c: CoresAlma): Tinta => {
  if (kind === "cta") {
    return { fundo: c.destaque, tinta: c.texto_inverso, acento: c.texto_inverso, suave: mistura(c.texto_inverso, 20, c.destaque), apoio: mistura(c.texto_inverso, 82, c.destaque) };
  }
  if (indice % 2 === 0) {
    return { fundo: c.texto, tinta: c.texto_inverso, acento: c.destaque, suave: mistura(c.texto_inverso, 12, c.texto), apoio: mistura(c.texto_inverso, 72, c.texto) };
  }
  return { fundo: c.fundo_alt, tinta: c.texto, acento: c.destaque, suave: mistura(c.destaque, 16, c.fundo_alt), apoio: c.apoio };
};

export type PropsCena = { f: number; d: number; ev: (nome: string) => number; cena: CenaT; t: Tinta };

const texto = (v: unknown): string => (typeof v === "string" ? v : "");
const lista = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

// Palavras que entram uma a uma, com mola, a partir do quadro `inicio`.
const Palavras: React.FC<{ f: number; inicio: number; frase: string; passo?: number }> = ({ f, inicio, frase, passo = 3 }) => (
  <>
    {frase.split(/\s+/).filter(Boolean).map((p, i) => {
      const s = mola(f, inicio + i * passo, 12, 180);
      return (
        <span key={i} style={{ display: "inline-block", opacity: s, transform: `translateY(${(1 - s) * 40}px)` }}>
          {p}
        </span>
      );
    })}
  </>
);

const Check: React.FC<{ x: number; y: number; r: number; p: number; fundo: string; traco: string }> = ({ x, y, r, p, fundo, traco }) => (
  <g transform={`translate(${x},${y}) scale(${p})`}>
    <circle r={r} fill={fundo} />
    <path
      d={`M ${-r * 0.45} 0 L ${-r * 0.1} ${r * 0.35} L ${r * 0.5} ${-r * 0.35}`}
      stroke={traco}
      strokeWidth={r * 0.2}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </g>
);

const Xis: React.FC<{ x: number; y: number; r: number; p: number; fundo: string; traco: string }> = ({ x, y, r, p, fundo, traco }) => (
  <g transform={`translate(${x},${y}) scale(${p})`}>
    <circle r={r} fill={fundo} />
    <path d={`M ${-r * 0.35} ${-r * 0.35} L ${r * 0.35} ${r * 0.35} M ${r * 0.35} ${-r * 0.35} L ${-r * 0.35} ${r * 0.35}`}
      stroke={traco} strokeWidth={r * 0.2} strokeLinecap="round" />
  </g>
);

// 1. Abertura: o gancho em letras grandes, com um anel girando e três pontos em órbita.
const Abertura: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes } = useAlma();
  const e = ev("titulo");
  const a = ev("apoio");
  const titulo = texto(cena.titulo);
  const apoio = texto(cena.apoio);
  const anel = mola(f, 0, 14, 90);
  return (
    <AbsoluteFill>
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        <circle cx={790} cy={150} r={150 * anel} fill={t.suave} />
        <circle cx={790} cy={150} r={112} fill="none" stroke={t.acento} strokeWidth={10} strokeDasharray="26 20"
          transform={`rotate(${f * 1.5} 790 150)`} opacity={anel} />
        {[0, 1, 2].map((k) => (
          <circle key={k} cx={790 + Math.cos(f / 18 + k * 2.1) * 186} cy={150 + Math.sin(f / 18 + k * 2.1) * 186} r={13}
            fill={t.acento} opacity={anel} />
        ))}
        <rect x={80} y={660} width={rampa(f, e, e + 24, 0, 380)} height={14} rx={7} fill={t.acento} />
      </svg>
      <div style={{ position: "absolute", left: 80, right: 80, top: 200, bottom: 150, display: "flex", flexDirection: "column", justifyContent: "center", gap: 30 }}>
        <div style={{ display: "flex", flexWrap: "wrap", columnGap: 22, fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800,
          fontSize: titulo.length > 26 ? 76 : 94, lineHeight: 1.05, letterSpacing: -1, color: t.tinta }}>
          <Palavras f={f} inicio={e} frase={titulo} />
        </div>
        {apoio ? (
          <div style={{ fontFamily: pilhaFonte(fontes.texto), fontWeight: 600, fontSize: 40, lineHeight: 1.2, color: t.apoio,
            opacity: rampa(f, a, a + 12), transform: `translateY(${rampa(f, a, a + 12, 24, 0)}px)` }}>
            {apoio}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// 2. Número: o algarismo inicial conta de zero até o valor enquanto o arco enche.
const Numero: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes } = useAlma();
  const c = ev("conta");
  const fim = ev("fim");
  const valor = texto(cena.valor);
  const m = /^(\d+)(.*)$/.exec(valor);
  const p = interpolate(f, [c, Math.max(c + 1, fim)], [0, 1], clamp);
  const mostrado = m ? `${Math.round(Number(m[1]) * p)}${m[2]}` : valor;
  const raio = 190;
  const volta = 2 * Math.PI * raio;
  const pulso = fim > 0 ? 1 + 0.06 * Math.sin(Math.PI * rampa(f, fim, fim + 10)) : 1;
  return (
    <AbsoluteFill>
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        <circle cx={480} cy={320} r={raio} fill="none" stroke={t.suave} strokeWidth={34} />
        <circle cx={480} cy={320} r={raio} fill="none" stroke={t.acento} strokeWidth={34} strokeLinecap="round"
          strokeDasharray={volta} strokeDashoffset={volta * (1 - p)} transform="rotate(-90 480 320)" />
        {[0, 1, 2, 3, 4, 5].map((k) => (
          <circle key={k} cx={480 + Math.cos((k / 6) * 2 * Math.PI + f / 30) * 260} cy={320 + Math.sin((k / 6) * 2 * Math.PI + f / 30) * 260}
            r={8} fill={t.acento} opacity={0.5 * rampa(f, c, c + 10)} />
        ))}
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 200, height: 240, display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: mostrado.length > 5 ? 104 : 140, color: t.tinta,
        transform: `scale(${pulso})` }}>
        {mostrado}
      </div>
      <div style={{ position: "absolute", left: 90, right: 90, top: 560, textAlign: "center", fontFamily: pilhaFonte(fontes.texto),
        fontWeight: 700, fontSize: 44, lineHeight: 1.18, color: t.tinta, opacity: rampa(f, c + 6, c + 18) }}>
        {texto(cena.texto)}
      </div>
    </AbsoluteFill>
  );
};

// 3. Lista: cada item entra com um tique no seu evento (i0, i1, ...).
const Lista: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes, cores } = useAlma();
  const itens = lista(cena.itens);
  const e = ev("titulo");
  const topo = 250;
  const passo = Math.min(130, 440 / Math.max(1, itens.length));
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 80, right: 80, top: 80, fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800,
        fontSize: 60, lineHeight: 1.08, color: t.tinta, display: "flex", flexWrap: "wrap", columnGap: 16 }}>
        <Palavras f={f} inicio={e} frase={texto(cena.titulo)} passo={2} />
      </div>
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        {itens.map((_, k) => {
          const s = mola(f, ev(`i${k}`), 9, 160);
          return <Check key={k} x={125} y={topo + k * passo + 36} r={34} p={s} fundo={cores.positivo} traco={cores.texto_inverso} />;
        })}
      </svg>
      {itens.map((item, k) => {
        const s = mola(f, ev(`i${k}`) + 2, 12, 170);
        return (
          <div key={k} style={{ position: "absolute", left: 190, right: 70, top: topo + k * passo, height: 72, display: "flex", alignItems: "center",
            fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 44, color: t.tinta, opacity: s,
            transform: `translateX(${(1 - s) * 60}px)` }}>
            {item}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// 4. Contraste: o lado ruim entra primeiro; o bom desliza por cima e a seta liga os dois.
const Contraste: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes, cores } = useAlma();
  const a = ev("a");
  const b = ev("b");
  const sa = mola(f, a, 12, 160);
  const sb = mola(f, b, 12, 160);
  const Painel: React.FC<{ x: number; s: number; rotulo: string; frase: string; bom: boolean }> = ({ x, s, rotulo, frase, bom }) => (
    <div style={{ position: "absolute", left: x, top: 120, width: 380, height: 520, borderRadius: 32, background: cores.fundo,
      boxShadow: "0 12px 30px rgba(0, 0, 0, 0.18)", opacity: s, transform: `translateY(${(1 - s) * 80}px) rotate(${bom ? 2 : -2}deg)`,
      display: "flex", flexDirection: "column", alignItems: "center", padding: "150px 34px 30px", gap: 22 }}>
      <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 34, letterSpacing: 1, color: cores.texto_inverso,
        background: bom ? cores.positivo : cores.negativo, borderRadius: 40, padding: "8px 26px", textTransform: "uppercase" }}>
        {rotulo}
      </div>
      <div style={{ fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 40, lineHeight: 1.18, textAlign: "center", color: cores.texto }}>
        {frase}
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <Painel x={60} s={sa} rotulo={texto(cena.rotulo_a)} frase={texto(cena.texto_a)} bom={false} />
      <Painel x={520} s={sb} rotulo={texto(cena.rotulo_b)} frase={texto(cena.texto_b)} bom />
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        <Xis x={250} y={200} r={48} p={sa} fundo={cores.negativo} traco={cores.texto_inverso} />
        <Check x={710} y={200} r={48} p={sb} fundo={cores.positivo} traco={cores.texto_inverso} />
        <g transform={`translate(${interpolate(f, [b - 4, b + 10], [440, 480], clamp)},390)`} opacity={rampa(f, b - 4, b + 6)}>
          <circle r={44} fill={t.acento} />
          <path d="M -18 0 L 16 0 M 4 -14 L 18 0 L 4 14" stroke={t.fundo} strokeWidth={8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

// 5. Frase: aspas grandes e a afirmação; o trecho `marca` ganha o marca-texto no evento.
const Frase: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes } = useAlma();
  const e = ev("entra");
  const m = ev("marca");
  const frase = texto(cena.texto);
  const marca = texto(cena.marca);
  const i = marca ? frase.indexOf(marca) : -1;
  const partes = i >= 0 ? [frase.slice(0, i), marca, frase.slice(i + marca.length)] : [frase, "", ""];
  const varre = rampa(f, m, m + 14, 0, 100);
  return (
    <AbsoluteFill>
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        <text x={70} y={230} fontFamily={pilhaFonte(fontes.titulo)} fontWeight={800} fontSize={300} fill={t.acento}
          opacity={mola(f, e, 12, 160)}>
          “
        </text>
        <rect x={80} y={680} width={800 * rampa(f, e, e + 30)} height={10} rx={5} fill={t.suave} />
      </svg>
      <div style={{ position: "absolute", left: 90, right: 90, top: 230, bottom: 130, display: "flex", alignItems: "center",
        fontFamily: pilhaFonte(fontes.titulo), fontWeight: 700, fontSize: frase.length > 70 ? 54 : 66, lineHeight: 1.2, color: t.tinta,
        opacity: rampa(f, e, e + 12), transform: `translateY(${rampa(f, e, e + 12, 30, 0)}px)` }}>
        <div>
          {partes[0]}
          {partes[1] ? (
            <span style={{ backgroundImage: `linear-gradient(${t.acento}, ${t.acento})`, backgroundRepeat: "no-repeat",
              backgroundPosition: "0 88%", backgroundSize: `${varre}% 38%`, padding: "0 4px" }}>
              {partes[1]}
            </span>
          ) : null}
          {partes[2]}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 6. CTA: o pedido em letras grandes, com ondas saindo do alvo e a seta pulando.
const Cta: React.FC<PropsCena> = ({ f, ev, cena, t }) => {
  const { fontes } = useAlma();
  const m = ev("marca");
  const c = ev("chime");
  const s = mola(f, m, 10, 150);
  const apoio = texto(cena.apoio);
  return (
    <AbsoluteFill>
      <svg width={CARTAO.w} height={CARTAO.h} style={{ position: "absolute", left: 0, top: 0 }}>
        {[0, 1, 2].map((k) => {
          const fase = ((f - c + k * 14) % 42) / 42;
          return f >= c ? (
            <circle key={k} cx={480} cy={200} r={60 + fase * 150} fill="none" stroke={t.acento} strokeWidth={6} opacity={1 - fase} />
          ) : null;
        })}
        <g transform={`translate(480,${200 + Math.abs(Math.sin(f / 6)) * -14}) scale(${s})`}>
          <circle r={70} fill={t.acento} />
          <path d="M 0 -30 L 0 28 M -24 6 L 0 30 L 24 6" stroke={t.fundo} strokeWidth={12} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </svg>
      <div style={{ position: "absolute", left: 70, right: 70, top: 330, textAlign: "center", fontFamily: pilhaFonte(fontes.titulo),
        fontWeight: 800, fontSize: 76, lineHeight: 1.05, color: t.tinta, display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 20 }}>
        <Palavras f={f} inicio={m + 4} frase={texto(cena.texto)} />
      </div>
      {apoio ? (
        <div style={{ position: "absolute", left: 90, right: 90, top: 600, textAlign: "center", fontFamily: pilhaFonte(fontes.texto),
          fontWeight: 600, fontSize: 38, lineHeight: 1.2, color: t.apoio, opacity: rampa(f, c, c + 12) }}>
          {apoio}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// Registro kind -> cena. O template.json declara os mesmos kinds, com os slots de cada um.
export const CENAS: Record<string, React.FC<PropsCena>> = {
  abertura: Abertura,
  numero: Numero,
  lista: Lista,
  contraste: Contraste,
  frase: Frase,
  cta: Cta,
};

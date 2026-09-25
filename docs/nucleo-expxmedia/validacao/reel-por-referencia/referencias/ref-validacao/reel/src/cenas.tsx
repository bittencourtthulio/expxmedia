import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { clamp, mola, pilhaFonte, rampa, useAlma } from "@expxmedia/template";

// As 14 cenas deste reel, na ordem da referência (seção 5 de ../../analise/leitura.md). Cada uma desenha a parte
// de cima do quadro (o cartão de interface ou o desenho); a legenda, o apresentador e o selo são do Reel.tsx.
// Tudo desenhado aqui, em SVG e CSS: nenhum quadro, logo, rosto ou texto da referência. Os textos da tela são
// campos do cenas.json (textos), não do código.

export type CenaT = { id: string; ev: Record<string, number>; inicio: number; dur: number; [campo: string]: unknown };
export type PropsCena = { f: number; d: number; ev: (nome: string) => number; cena: CenaT };

// Paleta aproximada da referência (clima de cor, não marca): off-white quente, cartão branco, laranja do ícone,
// vermelho do problema, verde da virada, chip quase preto.
export const PALETA = {
  fundo: "#EFEDE8",
  cartao: "#FFFFFF",
  tinta: "#1C1C1C",
  chip: "#1E1E1E",
  branco: "#FFFFFF",
  laranja: "#DA7550",
  vermelho: "#E5483B",
  verde: "#2E9E48",
  cinza: "#B9B6B0",
  cinzaClaro: "#E6E4DF",
  linha: "#D6D3CC",
  amarelo: "#F6C04A",
  fogo: "#F08A2E",
  marrom: "#4A3226",
  bege: "#E9DCC2",
  pele: "#F3C9A0",
  azul: "#4C8DF6",
};

export const normalizar = (s: string): string =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");

type Textos = Record<string, string | string[]>;
const textos = (c: CenaT): Textos => (c.textos ?? {}) as Textos;
const txt = (c: CenaT, k: string): string => String(textos(c)[k] ?? "");
const itens = (c: CenaT, k: string): string[] => (textos(c)[k] as string[] | undefined) ?? [];

// Texto digitado: quantas letras de `texto` já saíram entre os quadros a e b.
const digitado = (texto: string, f: number, a: number, b: number): string =>
  texto.slice(0, Math.round(interpolate(f, [a, Math.max(a + 1, b)], [0, texto.length], clamp)));

// ---------------------------------------------------------------- peças comuns

// O cartão branco de cima, que entra por uma mola curta (escala 0,95 → 1), como na referência.
const Cartao: React.FC<{ f: number; topo?: number; altura?: number; borda?: string; esq?: number; dir?: number;
  children?: React.ReactNode }> = ({ f, topo = 250, altura = 470, borda, esq = 70, dir = 70, children }) => {
  const s = mola(f, 0, 14, 220);
  return (
    <div style={{ position: "absolute", left: esq, right: dir, top: topo, height: altura, background: PALETA.cartao,
      borderRadius: 28, boxShadow: "0 10px 30px rgba(0,0,0,0.08)", border: borda ? `5px solid ${borda}` : "none",
      overflow: "hidden", opacity: s, transform: `scale(${0.95 + 0.05 * s})` }}>
      {children}
    </div>
  );
};

// O nosso ícone da solução: quadrado laranja de cantos arredondados com um pão desenhado em branco.
const IconePao: React.FC<{ x: number; y: number; t: number }> = ({ x, y, t }) => (
  <g transform={`translate(${x} ${y}) scale(${t / 100})`}>
    <rect x={0} y={0} width={100} height={100} rx={24} fill={PALETA.laranja} />
    <path d="M20 66 Q20 30 50 30 Q80 30 80 66 Z" fill={PALETA.branco} />
    <rect x={20} y={62} width={60} height={10} rx={4} fill={PALETA.branco} />
    {[34, 48, 62].map((cx) => (
      <line key={cx} x1={cx - 5} y1={52} x2={cx + 5} y2={40} stroke={PALETA.laranja} strokeWidth={4} strokeLinecap="round" />
    ))}
  </g>
);

const Svg: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
    {children}
  </svg>
);

// Rosto desenhado (no lugar dos trechos de meme da referência): careta aflita ou sorriso de canto.
const Rosto: React.FC<{ cx: number; cy: number; humor: "careta" | "sorriso"; f: number; marca: number }> = ({
  cx, cy, humor, f, marca,
}) => {
  const s = mola(f, marca, 10, 180);
  const treme = humor === "careta" ? Math.sin(f * 1.7) * 4 * s : 0;
  const giro = humor === "sorriso" ? interpolate(s, [0, 1], [0, -6]) : 0;
  const sobrancelha = humor === "sorriso" ? interpolate(s, [0, 1], [0, -18]) : 0;
  return (
    <g transform={`translate(${cx + treme} ${cy}) rotate(${giro})`}>
      <circle r={150} fill={PALETA.pele} />
      <ellipse cx={-52} cy={-30} rx={16} ry={humor === "careta" ? 12 : 18} fill={PALETA.tinta} />
      <ellipse cx={52} cy={-30} rx={16} ry={18} fill={PALETA.tinta} />
      <line x1={-80} y1={-72} x2={-24} y2={humor === "careta" ? -60 : -76} stroke={PALETA.tinta} strokeWidth={9} strokeLinecap="round" />
      <line x1={24} y1={-76 + sobrancelha} x2={80} y2={-72 + sobrancelha * 1.4} stroke={PALETA.tinta} strokeWidth={9} strokeLinecap="round" />
      {humor === "careta" ? (
        <g>
          <rect x={-70} y={40} width={140} height={48} rx={16} fill={PALETA.branco} stroke={PALETA.tinta} strokeWidth={7} />
          {[-35, 0, 35].map((x) => <line key={x} x1={x} y1={42} x2={x} y2={86} stroke={PALETA.tinta} strokeWidth={5} />)}
          <path d={`M110 -90 q 14 ${26 * s} 0 ${40 * s} q -14 -14 0 -40`} fill={PALETA.azul} opacity={s} />
        </g>
      ) : (
        <path d="M-60 60 Q 10 100 70 40" fill="none" stroke={PALETA.tinta} strokeWidth={10} strokeLinecap="round" />
      )}
    </g>
  );
};

// A janela de aplicativo (três bolinhas, barra lateral, aba do arquivo, área de texto com números de linha).
const Janela: React.FC<{ f: number; cena: CenaT; linhas: string[]; topo?: number; altura?: number;
  children?: React.ReactNode }> = ({ f, cena, linhas, topo = 250, altura = 470, children }) => {
  const { fontes } = useAlma();
  const menu = itens(cena, "menu").length ? itens(cena, "menu") : ["", "", "", ""];
  return (
    <Cartao f={f} topo={topo} altura={altura}>
      <div style={{ position: "absolute", left: 22, top: 20, display: "flex", gap: 10 }}>
        {[PALETA.vermelho, PALETA.amarelo, PALETA.verde].map((c) => (
          <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, top: 54, width: 190, bottom: 0, borderRight: `2px solid ${PALETA.cinzaClaro}`,
        padding: "16px 22px", fontFamily: pilhaFonte(fontes.texto), fontSize: 22, color: PALETA.tinta, lineHeight: 1.9 }}>
        {menu.map((m, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 16, height: 16, borderRadius: 4, background: i === 0 ? PALETA.laranja : PALETA.cinzaClaro }} />
            {m || <div style={{ width: 90, height: 10, borderRadius: 5, background: PALETA.cinzaClaro }} />}
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 206, top: 60, padding: "6px 16px", borderRadius: 10,
        background: PALETA.fundo, fontFamily: pilhaFonte(fontes.texto), fontSize: 20, color: PALETA.tinta, display: "flex",
        alignItems: "center", gap: 8 }}>
        <div style={{ width: 10, height: 10, borderRadius: 5, background: PALETA.laranja }} />
        {txt(cena, "arquivo") || "pedido.txt"}
      </div>
      <div style={{ position: "absolute", left: 206, right: 24, top: 112, fontFamily: pilhaFonte(fontes.texto), fontSize: 28,
        color: PALETA.tinta, lineHeight: 1.55 }}>
        {linhas.map((l, i) => (
          <div key={i} style={{ display: "flex", gap: 18, fontWeight: l.startsWith("#") ? 800 : 500 }}>
            <span style={{ color: PALETA.cinza, width: 22, textAlign: "right" }}>{i + 1}</span>
            <span>{l}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 206, right: 24, bottom: 18, height: 44, borderRadius: 12,
        border: `2px solid ${PALETA.cinzaClaro}` }} />
      {children}
    </Cartao>
  );
};

const Pilula: React.FC<{ texto: string; cor: string; s: number; fonte: string; tam?: number }> = ({ texto, cor, s, fonte, tam = 22 }) => (
  <div style={{ display: "inline-flex", alignItems: "center", padding: "6px 16px", borderRadius: 30, background: cor,
    color: PALETA.branco, fontFamily: fonte, fontWeight: 800, fontSize: tam, transform: `scale(${s})`, opacity: Math.min(1, s * 1.5) }}>
    {texto}
  </div>
);

const Check: React.FC<{ s: number; tam?: number }> = ({ s, tam = 34 }) => (
  <div style={{ width: tam, height: tam, borderRadius: tam / 2, background: PALETA.verde, display: "flex", alignItems: "center",
    justifyContent: "center", transform: `scale(${s})` }}>
    <svg viewBox="0 0 20 20" width={tam * 0.6} height={tam * 0.6}>
      <path d="M4 10 L8 14 L16 6" fill="none" stroke={PALETA.branco} strokeWidth={3} strokeLinecap="round" />
    </svg>
  </div>
);

// ---------------------------------------------------------------- 1. duelo (tela cheia)

// Um figurante da fila, desenhado.
const Pessoa: React.FC<{ x: number; y: number; cor: string }> = ({ x, y, cor }) => (
  <g transform={`translate(${x} ${y})`}>
    <circle cx={0} cy={-38} r={16} fill={PALETA.pele} />
    <rect x={-18} y={-20} width={36} height={52} rx={14} fill={cor} />
  </g>
);

const Duelo: React.FC<PropsCena> = ({ f, d, ev, cena }) => {
  const { fontes } = useAlma();
  const entra = mola(f, ev("entra"), 14, 200);
  const voo = interpolate(f, [ev("dispara"), ev("acerta")], [0, 1], clamp);
  const acertou = f >= ev("acerta");
  const tranco = acertou ? Math.sin((f - ev("acerta")) * 1.2) * 14 * Math.exp(-(f - ev("acerta")) / 10) : 0;
  const tomba = acertou ? interpolate(f, [ev("acerta"), ev("acerta") + 12], [0, 12], clamp) : 0;
  const estrela = mola(f, ev("acerta"), 8, 260);
  const raio = interpolate(f, [ev("explode"), d], [0, 1500], clamp);
  const rotulo = { position: "absolute" as const, top: 530, width: 240, textAlign: "center" as const,
    fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 30, color: PALETA.tinta, opacity: entra };
  return (
    <AbsoluteFill>
      <Svg>
        <line x1={90} y1={510} x2={990} y2={510} stroke={PALETA.linha} strokeWidth={3} opacity={entra} />
        <g opacity={entra} transform={`translate(0 ${(1 - entra) * 40})`}>
          <rect x={80} y={300} width={220} height={200} rx={22} fill={PALETA.bege} />
          <g transform="translate(110 350) rotate(-8)">
            <path d="M0 0 H150 V30 a14 14 0 0 0 0 28 V88 H0 V58 a14 14 0 0 0 0 -28 Z" fill={PALETA.branco} stroke={PALETA.tinta} strokeWidth={4} />
            <line x1={30} y1={30} x2={120} y2={30} stroke={PALETA.cinza} strokeWidth={6} strokeLinecap="round" />
            <line x1={30} y1={54} x2={96} y2={54} stroke={PALETA.laranja} strokeWidth={6} strokeLinecap="round" />
          </g>
          <IconePao x={262} y={284} t={54} />
        </g>
        <g opacity={entra} transform={`translate(${tranco} ${(1 - entra) * 40}) rotate(${tomba} 890 500)`}>
          <rect x={780} y={300} width={220} height={200} rx={22} fill={PALETA.cinzaClaro} />
          {[0, 1, 2, 3].map((i) => (
            <Pessoa key={i} x={820 + i * 48} y={440 + (i % 2) * 6} cor={[PALETA.azul, PALETA.marrom, PALETA.verde, PALETA.vermelho][i]} />
          ))}
          <circle cx={988} cy={492} r={24} fill={PALETA.tinta} />
          <path d="M988 476 V492 L1000 500" stroke={PALETA.branco} strokeWidth={4} fill="none" strokeLinecap="round" />
        </g>
        {voo > 0 && !acertou ? (
          <g transform={`translate(${interpolate(voo, [0, 1], [300, 790])} ${420 - Math.sin(voo * Math.PI) * 60}) rotate(${voo * 360})`}>
            <rect x={-46} y={-14} width={92} height={28} rx={14} fill={PALETA.bege} stroke={PALETA.marrom} strokeWidth={4} />
            {[-22, 0, 22].map((x) => <line key={x} x1={x - 6} y1={6} x2={x + 6} y2={-6} stroke={PALETA.marrom} strokeWidth={3} />)}
          </g>
        ) : null}
        {acertou ? (
          <g transform={`translate(800 410) scale(${estrela}) rotate(${f * 3})`} opacity={1 - rampa(f, ev("acerta") + 10, ev("acerta") + 20)}>
            <polygon points="0,-70 18,-22 68,-26 28,6 44,56 0,26 -44,56 -28,6 -68,-26 -18,-22" fill={PALETA.amarelo} stroke={PALETA.fogo} strokeWidth={6} />
          </g>
        ) : null}
        {raio > 0 ? (
          <g>
            <circle cx={540} cy={420} r={raio} fill={PALETA.marrom} />
            <circle cx={540} cy={420} r={raio * 0.82} fill={PALETA.fogo} />
            <circle cx={540} cy={420} r={raio * 0.6} fill={PALETA.amarelo} />
            <circle cx={540} cy={420} r={raio * 0.34} fill={PALETA.branco} />
          </g>
        ) : null}
      </Svg>
      <div style={{ ...rotulo, left: 70 }}>{txt(cena, "esquerda")}</div>
      <div style={{ ...rotulo, left: 770 }}>{txt(cena, "direita")}</div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 2. chegada (tela cheia)

const Chegada: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const brilho = 1 - rampa(f, 0, ev("cai"));
  const cai = mola(f, ev("cai"), 9, 170);
  const y = interpolate(cai, [0, 1], [-260, 380]);
  const poeira = rampa(f, ev("quica"), ev("quica") + 16);
  const titulo = txt(cena, "titulo");
  const versao = txt(cena, "versao");
  return (
    <AbsoluteFill>
      <Svg>
        <defs>
          <radialGradient id="brilho-chegada">
            <stop offset="0%" stopColor={PALETA.branco} />
            <stop offset="55%" stopColor={PALETA.bege} />
            <stop offset="100%" stopColor={PALETA.fundo} />
          </radialGradient>
        </defs>
        <circle cx={540} cy={420} r={900} fill="url(#brilho-chegada)" opacity={brilho} />
        <line x1={290} y1={560} x2={790} y2={560} stroke={PALETA.linha} strokeWidth={3} />
        {[[-1, 440], [1, 640]].map(([lado, x]) => (
          <circle key={x} cx={x + lado * poeira * 40} cy={548 - poeira * 10} r={16 + poeira * 14} fill={PALETA.cinza}
            opacity={f >= ev("quica") ? 0.8 * (1 - poeira) + 0.1 : 0} />
        ))}
        <IconePao x={455} y={y} t={170} />
      </Svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 600, textAlign: "center", fontFamily: pilhaFonte(fontes.texto),
        fontWeight: 800, fontSize: 60, color: PALETA.tinta }}>
        {digitado(titulo, f, ev("digita"), ev("versao") - 4)}
        {f >= ev("versao") ? <span style={{ color: PALETA.laranja }}> {versao}</span> : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 3. filas (tela dividida)

const IconeItem: React.FC<{ i: number }> = ({ i }) => {
  if (i === 0) return <svg viewBox="0 0 100 100" width={120} height={120}><IconePao x={0} y={0} t={100} /></svg>;
  const fundo = i === 1 ? PALETA.marrom : PALETA.verde;
  return (
    <svg viewBox="0 0 100 100" width={120} height={120}>
      <rect width={100} height={100} rx={24} fill={fundo} />
      {i === 1 ? (
        <g fill="none" stroke={PALETA.branco} strokeWidth={7} strokeLinecap="round">
          <path d="M26 40 H66 V62 a16 16 0 0 1 -16 16 H42 a16 16 0 0 1 -16 -16 Z" />
          <path d="M66 46 h6 a9 9 0 0 1 0 18 h-6" />
        </g>
      ) : (
        <g fill="none" stroke={PALETA.branco} strokeWidth={7} strokeLinejoin="round" strokeLinecap="round">
          <path d="M26 40 H74 L70 78 H30 Z" />
          <path d="M38 40 V32 a12 12 0 0 1 24 0 V40" />
        </g>
      )}
    </svg>
  );
};

const Filas: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const estourou = f >= ev("estoura");
  const nomes = itens(cena, "itens");
  return (
    <Cartao f={f} topo={300} altura={360} borda={estourou ? PALETA.vermelho : undefined}>
      <div style={{ position: "absolute", left: 40, right: 40, top: 44, display: "flex", justifyContent: "space-between" }}>
        {nomes.map((nome, i) => {
          const enche = interpolate(f, [ev("enche") + i * 6, ev("estoura") - (2 - i) * 4], [0.12, 1], clamp);
          return (
            <div key={i} style={{ width: 240, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
              <IconeItem i={i} />
              <div style={{ fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 28, color: PALETA.tinta }}>{nome}</div>
              <div style={{ width: 220, height: 18, borderRadius: 9, background: PALETA.cinzaClaro, overflow: "hidden" }}>
                <div style={{ width: `${enche * 100}%`, height: "100%", borderRadius: 9,
                  background: estourou ? PALETA.vermelho : PALETA.cinza }} />
              </div>
              <div style={{ fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 22,
                color: estourou ? PALETA.vermelho : PALETA.cinza }}>
                {estourou ? txt(cena, "cheia") : txt(cena, "barra")}
              </div>
            </div>
          );
        })}
      </div>
    </Cartao>
  );
};

// ---------------------------------------------------------------- 4. reação (tela cheia)

const Reacao: React.FC<PropsCena> = ({ f, ev }) => {
  const mao = mola(f, ev("mao"), 10, 220);
  return (
    <AbsoluteFill>
      <Cartao f={f} topo={260} altura={400} esq={170} dir={170}>
        <Svg>
          <rect x={0} y={0} width={740} height={400} fill={PALETA.bege} />
          <Rosto cx={370} cy={210} humor="careta" f={f} marca={ev("careta")} />
        </Svg>
      </Cartao>
      <Svg>
        <IconePao x={495} y={700} t={90} />
        <g transform={`translate(600 700) rotate(${interpolate(mao, [0, 1], [-40, 0])} 30 60) scale(${mao})`}>
          <rect x={10} y={30} width={44} height={50} rx={14} fill={PALETA.fogo} />
          <rect x={22} y={0} width={16} height={44} rx={8} fill={PALETA.fogo} />
        </g>
      </Svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 5. solução (tela dividida)

const Solucao: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const resta = interpolate(f, [ev("esvazia"), ev("separado")], [1, 0], clamp);
  const ok = mola(f, ev("separado"), 10, 220);
  return (
    <Cartao f={f} topo={290} altura={380}>
      <svg viewBox="0 0 100 100" width={130} height={130} style={{ position: "absolute", left: 60, top: 70 }}>
        <IconePao x={0} y={0} t={100} />
      </svg>
      <div style={{ position: "absolute", left: 230, top: 80, fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 30,
        color: PALETA.tinta }}>
        {txt(cena, "barra")}
      </div>
      <div style={{ position: "absolute", left: 230, right: 60, top: 130, height: 24, borderRadius: 12, background: PALETA.cinzaClaro,
        overflow: "hidden" }}>
        <div style={{ width: `${resta * 100}%`, height: "100%", background: PALETA.vermelho, borderRadius: 12 }} />
      </div>
      <div style={{ position: "absolute", left: 230, top: 200, display: "flex", alignItems: "center", gap: 14 }}>
        <Check s={ok} />
        <Pilula texto={txt(cena, "separado")} cor={PALETA.verde} s={ok} fonte={pilhaFonte(fontes.texto)} tam={28} />
      </div>
    </Cartao>
  );
};

// ---------------------------------------------------------------- 6. confiante (tela dividida)

const Confiante: React.FC<PropsCena> = ({ f, ev }) => (
  <Cartao f={f} topo={270} altura={420}>
    <Svg>
      <rect x={0} y={0} width={940} height={420} fill={PALETA.bege} />
      <Rosto cx={470} cy={220} humor="sorriso" f={f} marca={ev("sorri")} />
    </Svg>
  </Cartao>
);

// ---------------------------------------------------------------- 7. janela (tela dividida)

const Cursor: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <svg viewBox="0 0 30 40" width={30} height={40} style={{ position: "absolute", left: x, top: y }}>
    <path d="M2 2 L2 32 L10 25 L16 38 L21 36 L15 23 L26 23 Z" fill={PALETA.tinta} stroke={PALETA.branco} strokeWidth={2} />
  </svg>
);

const JanelaCena: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const x = interpolate(f, [ev("cursor"), ev("clica")], [300, 560], clamp);
  const y = interpolate(f, [ev("cursor"), ev("clica")], [80, 150], clamp);
  const pisca = f >= ev("clica") && Math.floor((f - ev("clica")) / 8) % 2 === 0;
  return (
    <Janela f={f} cena={cena} linhas={[pisca ? "|" : " "]}>
      <Cursor x={x} y={y} />
    </Janela>
  );
};

// ---------------------------------------------------------------- 8. escreve (tela cheia)

const Escreve: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const [l1, l2] = itens(cena, "linhas");
  const linhas = [digitado(l1, f, 0, ev("linha2") - 4), digitado(l2, f, ev("linha2"), ev("etiqueta") - 4)];
  const s = mola(f, ev("etiqueta"), 10, 240);
  return (
    <Janela f={f} cena={cena} linhas={linhas}>
      <div style={{ position: "absolute", left: 560, top: 214 }}>
        <Pilula texto={txt(cena, "etiqueta")} cor={PALETA.laranja} s={s} fonte={pilhaFonte(fontes.texto)} />
      </div>
    </Janela>
  );
};

// ---------------------------------------------------------------- 9. fornada (tela dividida)

const Fornada: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const linhas = itens(cena, "linhas");
  const opcoes = itens(cena, "opcoes");
  const escolheu = f >= ev("escolhe");
  const ultima = digitado(linhas[2] ?? "", f, ev("digita"), ev("abre") - 2) + (escolheu ? opcoes[0] : "");
  const menu = mola(f, ev("abre"), 14, 260) * (1 - rampa(f, ev("escolhe") + 4, ev("escolhe") + 10));
  const aviso = mola(f, ev("aviso"), 12, 200);
  return (
    <Janela f={f} cena={cena} linhas={[linhas[0], linhas[1], ultima]}>
      <div style={{ position: "absolute", right: 40, bottom: 76, width: 280, background: PALETA.cartao, borderRadius: 14,
        boxShadow: "0 8px 24px rgba(0,0,0,0.16)", padding: 10, opacity: menu, transform: `scale(${0.9 + 0.1 * menu})`,
        transformOrigin: "bottom right", fontFamily: pilhaFonte(fontes.texto), fontSize: 26 }}>
        {opcoes.map((o, i) => (
          <div key={o} style={{ padding: "10px 14px", borderRadius: 10, fontWeight: 700,
            background: i === 0 && f >= ev("abre") + 8 ? PALETA.cinzaClaro : "transparent", color: PALETA.tinta }}>
            {o}
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", right: 30, bottom: 76, display: "flex", alignItems: "center", gap: 12,
        background: PALETA.cartao, borderRadius: 16, padding: "12px 20px", boxShadow: "0 8px 24px rgba(0,0,0,0.16)",
        transform: `translateX(${(1 - aviso) * 380}px)`, fontFamily: pilhaFonte(fontes.texto), fontWeight: 700, fontSize: 24,
        color: PALETA.tinta }}>
        <Check s={aviso} tam={30} />
        {txt(cena, "aviso")}
      </div>
    </Janela>
  );
};

// ---------------------------------------------------------------- 10. anota (tela dividida)

const Anota: React.FC<PropsCena> = ({ f, d, ev, cena }) => {
  const todas = itens(cena, "linhas");
  const total = todas.join("\n");
  const saiu = digitado(total, f, ev("texto"), Math.round(d * 0.85));
  return <Janela f={f} cena={cena} linhas={saiu.split("\n")} />;
};

// ---------------------------------------------------------------- 11. festa (tela cheia)

const Festa: React.FC<PropsCena> = ({ f, ev }) => {
  const conf = f - ev("confete");
  const cores = [PALETA.amarelo, PALETA.laranja, PALETA.verde, PALETA.azul, PALETA.vermelho];
  return (
    <AbsoluteFill>
      <Cartao f={f} topo={260} altura={420}>
        <Svg>
          <rect x={0} y={0} width={940} height={420} fill={PALETA.marrom} />
          <path d="M0 40 Q 470 120 940 40" stroke={PALETA.bege} strokeWidth={4} fill="none" />
          {Array.from({ length: 12 }).map((_, i) => {
            const x = 40 + i * 78;
            const y = 40 + Math.sin((i / 11) * Math.PI) * 40;
            return <polygon key={i} points={`${x - 22},${y} ${x + 22},${y} ${x},${y + 44}`} fill={cores[i % cores.length]} />;
          })}
          {[0, 1, 2].map((i) => {
            const pulo = f >= ev("danca") ? Math.abs(Math.sin((f - ev("danca")) / 6 + i)) * 50 : 0;
            const x = 250 + i * 220;
            return (
              <g key={i} transform={`translate(${x} ${330 - pulo}) rotate(${Math.sin(f / 5 + i) * 8})`}>
                <rect x={-84} y={10} width={168} height={40} rx={14} fill={PALETA.fogo} />
                <path d="M-80 30 Q-80 -60 0 -60 Q80 -60 80 30 Z" fill={PALETA.bege} stroke={PALETA.fogo} strokeWidth={6} />
                {[-36, 0, 36].map((dx) => <line key={dx} x1={dx - 10} y1={0} x2={dx + 10} y2={-30} stroke={PALETA.fogo} strokeWidth={6} strokeLinecap="round" />)}
                <circle cx={-24} cy={6} r={7} fill={PALETA.tinta} />
                <circle cx={24} cy={6} r={7} fill={PALETA.tinta} />
              </g>
            );
          })}
          {conf > 0
            ? Array.from({ length: 36 }).map((_, i) => {
                const x = (i * 137) % 940;
                const y = ((conf * (6 + (i % 5))) + i * 23) % 440 - 20;
                return <rect key={i} x={x} y={y} width={14} height={24} rx={3} fill={cores[i % cores.length]}
                  transform={`rotate(${(conf * 9 + i * 40) % 360} ${x + 7} ${y + 12})`} />;
              })
            : null}
        </Svg>
      </Cartao>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 12. árvore (tela cheia)

const Arvore: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const trilho = rampa(f, ev("linhas"), ev("c1"));
  const fornadas = itens(cena, "fornadas");
  const nomes = itens(cena, "itens");
  const xs = [200, 540, 880];
  const marcas = [ev("c1"), ev("c2"), ev("c3")];
  const cores = [PALETA.verde, PALETA.tinta, PALETA.verde];
  const s0 = mola(f, 0, 12, 200);
  return (
    <AbsoluteFill>
      <Svg>
        {xs.map((x) => (
          <path key={x} d={`M540 420 C 540 480, ${x} 470, ${x} 540`} fill="none" stroke={PALETA.cinza} strokeWidth={4}
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - trilho} />
        ))}
        <g transform={`translate(0 ${(1 - s0) * 30})`} opacity={s0}>
          <IconePao x={475} y={290} t={130} />
        </g>
      </Svg>
      <div style={{ position: "absolute", left: 630, top: 330, display: "flex", alignItems: "center", gap: 8, padding: "8px 16px",
        borderRadius: 20, background: PALETA.cartao, boxShadow: "0 4px 14px rgba(0,0,0,0.08)", opacity: s0,
        fontFamily: pilhaFonte(fontes.texto), fontSize: 22, color: PALETA.tinta }}>
        <div style={{ width: 10, height: 10, borderRadius: 5, background: PALETA.laranja }} />
        {txt(cena, "arquivo")}
      </div>
      {xs.map((x, i) => {
        const s = mola(f, marcas[i], 12, 240);
        return (
          <div key={x} style={{ position: "absolute", left: x - 140, top: 545, width: 280, height: 170, background: PALETA.cartao,
            borderRadius: 18, boxShadow: "0 6px 18px rgba(0,0,0,0.1)", padding: "16px 18px", opacity: s,
            transform: `scale(${0.8 + 0.2 * s})`, fontFamily: pilhaFonte(fontes.texto), color: PALETA.tinta }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 800, fontSize: 24 }}>
              <svg viewBox="0 0 100 100" width={30} height={30}><IconePao x={0} y={0} t={100} /></svg>
              {txt(cena, "cartao")}
            </div>
            <div style={{ fontSize: 22, margin: "10px 0 12px" }}>{nomes[i]}</div>
            <Pilula texto={fornadas[i]} cor={cores[i]} s={mola(f, marcas[i] + 6, 10, 260)} fonte={pilhaFonte(fontes.texto)} tam={20} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 13. separados (tela dividida)

const Separados: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const nomes = itens(cena, "itens");
  const fornadas = itens(cena, "fornadas");
  const marcas = [ev("r1"), ev("r2"), ev("r3")];
  return (
    <Cartao f={f} topo={270} altura={420}>
      <div style={{ position: "absolute", left: 36, top: 30, display: "flex", alignItems: "center", gap: 14,
        fontFamily: pilhaFonte(fontes.texto), fontWeight: 800, fontSize: 32, color: PALETA.tinta }}>
        <svg viewBox="0 0 100 100" width={44} height={44}><IconePao x={0} y={0} t={100} /></svg>
        {txt(cena, "titulo")}
      </div>
      {nomes.map((nome, i) => {
        const feito = f >= marcas[i];
        const s = mola(f, marcas[i], 10, 260);
        return (
          <div key={i} style={{ position: "absolute", left: 30, right: 30, top: 110 + i * 96, height: 78, borderRadius: 16,
            background: PALETA.fundo, display: "flex", alignItems: "center", padding: "0 20px", gap: 16,
            fontFamily: pilhaFonte(fontes.texto), fontSize: 28, color: PALETA.tinta }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: PALETA.laranja }} />
            <div style={{ flex: 1 }}>{nome}</div>
            <Pilula texto={fornadas[i]} cor={feito ? (i === 1 ? PALETA.tinta : PALETA.verde) : PALETA.cinza} s={1}
              fonte={pilhaFonte(fontes.texto)} />
            <div style={{ width: 36 }}>{feito ? <Check s={s} /> : null}</div>
          </div>
        );
      })}
    </Cartao>
  );
};

// ---------------------------------------------------------------- 14. fecho (tela dividida)

const Fecho: React.FC<PropsCena> = ({ f, ev, cena }) => {
  const { fontes } = useAlma();
  const enviou = f >= ev("envia");
  const campo = enviou ? "" : digitado(txt(cena, "pedido"), f, ev("digita"), ev("envia") - 6);
  const post = mola(f, ev("envia"), 12, 220);
  const curtiu = f >= ev("coracao");
  const bate = mola(f, ev("coracao"), 8, 300);
  const cx = interpolate(f, [ev("envia") - 10, ev("envia"), ev("coracao") - 6, ev("coracao")], [600, 820, 820, 860], clamp);
  const cy = interpolate(f, [ev("envia") - 10, ev("envia"), ev("coracao") - 6, ev("coracao")], [300, 340, 340, 124], clamp);
  const fonte = pilhaFonte(fontes.texto);
  return (
    <AbsoluteFill>
      <Cartao f={f} topo={250} altura={400}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 20, textAlign: "center", fontFamily: fonte, fontWeight: 700,
          fontSize: 30, color: PALETA.tinta }}>
          {txt(cena, "titulo")}
        </div>
        <div style={{ position: "absolute", left: 30, top: 22, fontFamily: fonte, fontSize: 30, color: PALETA.tinta }}>‹</div>
        {!enviou ? (
          <div style={{ position: "absolute", left: 0, right: 0, top: 130, textAlign: "center", fontFamily: fonte, fontSize: 28,
            color: PALETA.tinta }}>
            {txt(cena, "vazio")}
          </div>
        ) : (
          <div style={{ position: "absolute", left: 36, right: 36, top: 90, display: "flex", gap: 18, alignItems: "flex-start",
            opacity: post, transform: `translateY(${(1 - post) * 20}px)`, fontFamily: fonte, color: PALETA.tinta }}>
            <div style={{ width: 54, height: 54, borderRadius: 27, background: PALETA.cinzaClaro }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 22, color: PALETA.cinza }}>{txt(cena, "voce")}</div>
              <div style={{ fontSize: 40, fontWeight: 800 }}>{txt(cena, "pedido")}</div>
            </div>
            <svg viewBox="0 0 40 36" width={44} height={40} style={{ transform: `scale(${curtiu ? 0.8 + 0.2 * bate : 1})` }}>
              <path d="M20 34 L4 18 A9 9 0 0 1 20 6 A9 9 0 0 1 36 18 Z" fill={curtiu ? PALETA.vermelho : "none"}
                stroke={curtiu ? PALETA.vermelho : PALETA.tinta} strokeWidth={3} strokeLinejoin="round" />
            </svg>
          </div>
        )}
        <div style={{ position: "absolute", left: 30, right: 30, bottom: 30, height: 66, borderRadius: 33,
          border: `3px solid ${enviou ? PALETA.cinzaClaro : PALETA.tinta}`, display: "flex", alignItems: "center",
          padding: "0 26px", fontFamily: fonte, fontSize: 28, color: campo ? PALETA.tinta : PALETA.cinza }}>
          <div style={{ flex: 1 }}>{campo || txt(cena, "campo")}</div>
          <div style={{ color: PALETA.azul, fontWeight: 800, fontSize: 24 }}>{txt(cena, "enviar")}</div>
        </div>
        <Cursor x={cx} y={cy} />
      </Cartao>
      <div style={{ position: "absolute", left: 0, right: 0, top: 670, display: "flex", justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 24px", borderRadius: 30,
          background: PALETA.cartao, border: `3px solid ${enviou ? PALETA.azul : PALETA.cinzaClaro}`, fontFamily: fonte,
          fontSize: 24, color: PALETA.tinta }}>
          <div style={{ width: 12, height: 12, borderRadius: 6, background: PALETA.laranja }} />
          {txt(cena, "pilula")}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CENAS: Record<string, React.FC<PropsCena>> = {
  duelo: Duelo,
  chegada: Chegada,
  filas: Filas,
  reacao: Reacao,
  solucao: Solucao,
  confiante: Confiante,
  janela: JanelaCena,
  escreve: Escreve,
  fornada: Fornada,
  anota: Anota,
  festa: Festa,
  arvore: Arvore,
  separados: Separados,
  fecho: Fecho,
};

// Toda cena usa o off-white da referência como fundo.
export const FUNDOS: Record<string, string> = Object.fromEntries(Object.keys(CENAS).map((id) => [id, PALETA.fundo]));

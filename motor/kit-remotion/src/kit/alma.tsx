import React, { createContext, useContext } from "react";
import { useFontes } from "./fontes";

// A Alma dentro do Remotion (regra M13): cores, fontes, porta-voz e canal chegam SÓ por props, montadas pelo
// motor a partir de alma/alma.json. Nenhuma composição do kit carrega cor, nome, @ ou foto de empresa.
// Os papéis de cor são os nove de docs/contrato/CONTRATO-alma.md ("Os papéis de cor").

export const PAPEIS_COR = [
  "fundo",
  "fundo_alt",
  "texto",
  "texto_inverso",
  "apoio",
  "destaque",
  "destaque_2",
  "positivo",
  "negativo",
] as const;
export type PapelCor = (typeof PAPEIS_COR)[number];
export type CoresAlma = Record<PapelCor, string>;

// Um arquivo de fonte servido pelo public dir do render (caminho relativo, M9) ou URL completa.
export type ArquivoFonte = { caminho: string; peso: number | null; estilo: string | null };
export type FonteAlma = { familia: string; arquivos: ArquivoFonte[] };
export type FontesAlma = { titulo: FonteAlma; texto: FonteAlma };

// Quem aparece: o porta-voz (nome e retrato relativo ao public dir) e o canal onde a peça sai (o @).
export type PortaVozAlma = { id: string; nome: string; retrato: string | null };
export type CanalAlma = { canal: string; identificador: string };

export type PropsAlma = {
  cores: CoresAlma;
  fontes: FontesAlma;
  porta_voz: PortaVozAlma | null;
  canal: CanalAlma | null;
};

// Props mínimas de toda composição que veste a Alma.
export type ComAlma = { alma: PropsAlma };

// Defeitos das props da Alma, em português, para a composição falhar dizendo o que falta (chave nunca omitida, M7).
export const problemasAlma = (alma: unknown): string[] => {
  const a = alma as Partial<PropsAlma> | null | undefined;
  if (!a || typeof a !== "object") return ["props sem `alma`"];
  const problemas: string[] = [];
  for (const papel of PAPEIS_COR) {
    if (typeof a.cores?.[papel] !== "string") problemas.push(`alma.cores.${papel} ausente`);
  }
  for (const papel of ["titulo", "texto"] as const) {
    const f = a.fontes?.[papel];
    if (!f || typeof f.familia !== "string" || !Array.isArray(f.arquivos)) problemas.push(`alma.fontes.${papel} ausente`);
  }
  if (!("porta_voz" in a)) problemas.push("alma.porta_voz ausente (use null)");
  if (!("canal" in a)) problemas.push("alma.canal ausente (use null)");
  return problemas;
};

const Contexto = createContext<PropsAlma | null>(null);

// Envolve a composição: confere as props, segura o render até as fontes carregarem e publica a Alma no contexto.
export const ProvedorAlma: React.FC<{ alma: PropsAlma; children: React.ReactNode }> = ({ alma, children }) => {
  const problemas = problemasAlma(alma);
  if (problemas.length) throw new Error(`Alma inválida nas props: ${problemas.join("; ")}`);
  useFontes([alma.fontes.titulo, alma.fontes.texto]);
  return <Contexto.Provider value={alma}>{children}</Contexto.Provider>;
};

export const useAlma = (): PropsAlma => {
  const alma = useContext(Contexto);
  if (!alma) throw new Error("useAlma fora do ProvedorAlma: a composição precisa receber `alma` nas props");
  return alma;
};

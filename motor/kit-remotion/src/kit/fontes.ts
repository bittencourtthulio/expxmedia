import { loadFont } from "@remotion/fonts";
import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import type { FonteAlma } from "./alma";

// Fontes da Alma (D-21): os arquivos chegam por props (o motor resolve Google Fonts em cache local, fonte local
// da instalação ou a Inter embarcada) e são servidos pelo public dir do render. Nada de fonte de sistema e nada
// de rede no render: fonte do Google pedida no render estoura o delayRender sem rede.
// origem: Instragram-Videos/remotion/src/tema.ts:14-22 (loadFont local) e
// Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:168-171 (delayRender → continueRender/cancelRender)

// Caminho relativo vira staticFile (public dir do render); URL completa passa direto.
export const urlDoArquivo = (caminho: string): string =>
  /^(https?:|data:|blob:)/.test(caminho) ? caminho : staticFile(caminho.replace(/^\/+/, ""));

export const carregarFontes = (fontes: FonteAlma[]): Promise<void[]> => {
  const vistos = new Set<string>();
  const pedidos: Promise<void>[] = [];
  for (const fonte of fontes) {
    for (const arq of fonte.arquivos) {
      const chave = `${fonte.familia}|${arq.caminho}|${arq.peso ?? ""}|${arq.estilo ?? ""}`;
      if (vistos.has(chave)) continue;
      vistos.add(chave);
      pedidos.push(
        loadFont({
          family: fonte.familia,
          url: urlDoArquivo(arq.caminho),
          weight: arq.peso == null ? undefined : String(arq.peso),
          style: arq.estilo ?? undefined,
        }),
      );
    }
  }
  return Promise.all(pedidos);
};

// Segura o render até as fontes carregarem; falha de fonte derruba o render com o erro (não cai em outra fonte).
export const useFontes = (fontes: FonteAlma[]): void => {
  const [pronto] = useState(() => delayRender("fontes da Alma"));
  useEffect(() => {
    carregarFontes(fontes)
      .then(() => continueRender(pronto))
      .catch((e) => cancelRender(e));
    // as fontes são fixas durante o render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pronto]);
};

// Pilha CSS de uma fonte da Alma: a família pedida e só a genérica como reserva.
export const pilhaFonte = (fonte: FonteAlma): string => `"${fonte.familia}", sans-serif`;

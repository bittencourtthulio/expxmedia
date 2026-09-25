// Constantes únicas do kit (D-17). O fps mora SÓ aqui: a mola de anim.ts, as composições e a montagem da
// linha do tempo (scripts/montar.mjs lê este arquivo) usam este valor. Na origem o 30 estava repetido em
// Root.tsx, kit/anim.ts, montar-reel.mjs, lib.py e verify.py; mudar um só dessincronizava a mola da linha do tempo.

// origem: Instragram-Videos/remotion/src/Root.tsx:14 e Instragram-Videos/remotion/scripts/montar-reel.mjs:31
export const FPS = 30;

// Quadro vertical do reel. origem: Instragram-Videos/remotion/src/Root.tsx:12-13
export const REEL = { largura: 1080, altura: 1920 } as const;

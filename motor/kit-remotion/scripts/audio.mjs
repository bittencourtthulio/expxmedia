// Motor de áudio da montagem (D-19): síntese em JavaScript puro, sem amostra de terceiro. A música de cada peça
// sai de uma config (`trilha` no cenas.json) e os efeitos de uma biblioteca de 20 timbres. Quem chama é
// scripts/montar.mjs. Porta sem mudança de comportamento: mesmo PRNG (Park-Miller 16807), mesma semente padrão
// (7), mesmos timbres e mesma gravação WAV, para a trilha sair byte a byte igual à da origem (golden G2).
// origem: Instragram-Videos/remotion/scripts/audio.mjs:1-288
//
// Lições medidas (1º reel sob medida aprovado, 24/09/2026):
// - Transição com ruído branco aberto até 4 kHz soa como CHIADO: o dono reprovou. O `whoosh` daqui é ruído
//   filtrado duas vezes, grave (até ~900 Hz), com envelope sin² e um tom subindo por baixo, a 30% do volume.
// - A música fica bem abaixo da voz (ganho ~0.55 antes do mix, e a composição ainda toca a trilha a 0.8).
import fs from "node:fs";

export const SR = 44100; // origem: Instragram-Videos/remotion/scripts/audio.mjs:11
const TAU = Math.PI * 2;

export function criarMix(segundos, semente = 7) {
  const N = Math.ceil(segundos * SR);
  const L = new Float32Array(N);
  const R = new Float32Array(N);
  // PRNG Park-Miller (16807, 2^31-1). origem: Instragram-Videos/remotion/scripts/audio.mjs:18-19
  let seed = semente;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;

  // gen(t, i) devolve a amostra no instante t (s) contado do início do som.
  function tocar(t0, dur, gen, vol = 1, pan = 0) {
    const a = Math.round(t0 * SR);
    const n = Math.round(dur * SR);
    const gl = vol * Math.min(1, 1 - pan);
    const gr = vol * Math.min(1, 1 + pan);
    for (let i = 0; i < n; i++) {
      const k = a + i;
      if (k < 0 || k >= N) continue;
      const s = gen(i / SR, i);
      L[k] += s * gl;
      R[k] += s * gr;
    }
  }
  const lp = (fc) => {
    let y = 0;
    return (x, f = fc) => {
      y += (1 - Math.exp((-TAU * f) / SR)) * (x - y);
      return y;
    };
  };
  const hp = () => {
    let px = 0, py = 0;
    return (x) => {
      py = 0.95 * (py + x - px);
      px = x;
      return py;
    };
  };
  const tri = (ph) => (2 / Math.PI) * Math.asin(Math.sin(ph));
  const env = (t, a, d) => (t < a ? t / a : Math.exp(-(t - a) * d));

  // ---------- instrumentos ----------
  const I = {
    kick(t0, v = 0.55) {
      let ph = 0;
      tocar(t0, 0.35, (t) => {
        ph += (TAU * (45 + 90 * Math.exp(-t * 32))) / SR;
        return Math.sin(ph) * Math.exp(-t * 9);
      }, v);
    },
    caixa(t0, v = 0.16) {
      const h = hp();
      tocar(t0, 0.2, (t) => (h(rnd()) * 0.8 + Math.sin(TAU * 190 * t) * 0.4) * Math.exp(-t * 22), v);
    },
    palma(t0, v = 0.14) {
      [0, 0.012, 0.024].forEach((d) => {
        const h = hp();
        const l = lp(2500);
        tocar(t0 + d, 0.12, (t) => l(h(rnd())) * Math.exp(-t * 30), v);
      });
    },
    chimbal(t0, v = 0.05) {
      const h1 = hp(), h2 = hp();
      tocar(t0, 0.05, (t) => h2(h1(rnd())) * Math.exp(-t * 70), v, 0.2);
    },
    pluck(t0, f, v = 0.07, pan = 0) {
      tocar(t0, 0.6, (t) => (Math.sin(TAU * f * t) + 0.35 * Math.sin(TAU * 2 * f * t)) * env(t, 0.004, 7), v, pan);
    },
    sino(t0, f, v = 0.06, pan = 0) {
      tocar(t0, 1.4, (t) => (Math.sin(TAU * f * t) + 0.4 * Math.sin(TAU * f * 2.76 * t) + 0.2 * Math.sin(TAU * f * 5.4 * t)) * env(t, 0.002, 3), v, pan);
    },
    baixo(t0, f, dur, v = 0.2) {
      const l = lp(400);
      tocar(t0, dur, (t) => l(Math.sin(TAU * f * t) + 0.25 * tri(TAU * f * t)) * env(t, 0.01, 2.5), v);
    },
    pad(t0, fs, dur, v = 0.028) {
      fs.forEach((f, j) => {
        const l = lp(1100);
        tocar(t0, dur + 0.4, (t) => {
          const a = Math.min(1, t / 0.35) * (t > dur ? Math.max(0, 1 - (t - dur) / 0.4) : 1);
          return l(tri(TAU * f * t * (1 + 0.002 * Math.sin(TAU * 0.3 * t)))) * a;
        }, v, j % 2 ? 0.3 : -0.3);
      });
    },
  };

  // ---------- efeitos ----------
  const tick = (t0, v = 0.5) => tocar(t0, 0.03, (t) => (Math.sin(TAU * 2200 * t) + rnd() * 0.5) * Math.exp(-t * 150), v * 0.35);
  const ding = (t0, v = 0.5) =>
    tocar(t0, 1.0, (t) => (Math.sin(TAU * 1318.5 * t) + 0.5 * Math.sin(TAU * 1975.5 * t) + 0.2 * Math.sin(TAU * 2637 * t)) * env(t, 0.003, 4.5), v * 0.25);
  const SFX = {
    whoosh(t0, dur = 0.4, v = 0.6) {
      const l1 = lp(300), l2 = lp(300);
      let ph = 0;
      tocar(t0, dur, (t) => {
        const x = t / dur;
        const e = Math.pow(Math.sin(Math.PI * x), 2);
        const fc = 250 + 650 * Math.sin(Math.PI * x);
        ph += (TAU * (220 + 180 * x)) / SR;
        return l2(l1(rnd(), fc), fc) * e * 1.6 + Math.sin(ph) * e * 0.12;
      }, v * 0.3);
    },
    pop(t0, _d, v = 0.5) {
      let ph = 0;
      tocar(t0, 0.1, (t) => {
        ph += (TAU * (300 + 700 * Math.exp(-t * 40))) / SR;
        return Math.sin(ph) * Math.exp(-t * 35);
      }, v * 0.6);
    },
    bolha(t0, _d, v = 0.5) {
      let ph = 0;
      tocar(t0, 0.12, (t) => {
        ph += (TAU * (400 + 900 * (t / 0.12))) / SR;
        return Math.sin(ph) * env(t, 0.005, 25);
      }, v * 0.4);
    },
    check(t0, _d, v = 1) {
      I.pluck(t0, 1318.5, 0.08 * v, 0.3);
      I.pluck(t0 + 0.06, 1760, 0.07 * v, 0.3);
    },
    ding: (t0, _d, v) => ding(t0, v),
    tick: (t0, _d, v) => tick(t0, v),
    digita(t0, dur = 0.8) {
      for (let t = 0; t < dur; t += 0.05 + Math.abs(rnd()) * 0.07) tick(t0 + t, 0.35 + Math.abs(rnd()) * 0.3);
    },
    erro(t0) {
      [0, 0.13].forEach((d, j) => {
        const l = lp(1400);
        tocar(t0 + d, 0.11, (t) => l(Math.sign(Math.sin(TAU * (j ? 150 : 200) * t))) * env(t, 0.005, 12), 0.13);
      });
    },
    carimbo(t0) {
      I.kick(t0, 0.7);
      const l = lp(900);
      tocar(t0, 0.25, (t) => l(rnd()) * Math.exp(-t * 20), 0.5);
      ding(t0 + 0.08, 0.35);
    },
    impacto(t0) {
      I.kick(t0, 0.8);
      const l = lp(400);
      tocar(t0, 0.5, (t) => l(rnd()) * Math.exp(-t * 8), 0.4);
    },
    subida(t0, dur = 1.5) {
      let ph = 0;
      tocar(t0, dur, (t) => {
        const x = t / dur;
        ph += (TAU * (300 * Math.pow(4, x))) / SR;
        return Math.sin(ph) * 0.5 * x * (1 - Math.max(0, (x - 0.92) / 0.08));
      }, 0.12);
      for (let t = 0; t < dur; t += 0.07 - 0.035 * (t / dur)) tick(t0 + t, 0.3);
    },
    descida(t0, dur = 0.6) {
      let ph = 0;
      tocar(t0, dur, (t) => {
        const x = t / dur;
        ph += (TAU * (900 * Math.pow(0.3, x))) / SR;
        return Math.sin(ph) * (1 - x);
      }, 0.1);
    },
    moeda(t0) {
      tocar(t0, 0.5, (t) => (t < 0.07 ? Math.sin(TAU * 1568 * t) : Math.sin(TAU * 2093 * t)) * env(t, 0.002, 6), 0.14);
    },
    snip(t0) {
      [0, 0.06].forEach((d) => {
        const h = hp();
        tocar(t0 + d, 0.04, (t) => h(rnd()) * Math.exp(-t * 90), 0.45);
      });
    },
    clack(t0) {
      tocar(t0, 0.12, (t) => (rnd() * 0.6 + Math.sin(TAU * 320 * t)) * Math.exp(-t * 45), 0.35);
    },
    plim(t0) {
      I.pluck(t0, 1760, 0.09, 0.4);
      I.pluck(t0 + 0.05, 2637, 0.06, 0.4);
    },
    hum(t0) {
      let ph = 0;
      tocar(t0, 0.3, (t) => {
        ph += (TAU * (190 - 50 * t)) / SR;
        return tri(ph) * env(t, 0.02, 8);
      }, 0.12, -0.4);
    },
    chime(t0) {
      [880, 1108.7, 1318.5, 1760].forEach((f, i) => I.pluck(t0 + i * 0.09, f, 0.1, -0.3 + i * 0.2));
    },
    passos(t0, dur = 1) {
      for (let t = 0; t < dur; t += 0.15) {
        let ph = 0;
        tocar(t0 + t, 0.08, (tt) => {
          ph += (TAU * (60 + 80 * Math.exp(-tt * 60))) / SR;
          return Math.sin(ph) * Math.exp(-tt * 40);
        }, 0.3);
      }
    },
    pagina(t0) {
      const l = lp(3000);
      tocar(t0, 0.25, (t) => l(rnd()) * Math.sin(Math.PI * (t / 0.25)) * 0.5, 0.25);
    },
  };

  // ---------- música ----------
  // cfg: { bpm, acordes: [[raizHz, [notasHz...]], ...], instrumentos: {kick, caixa|palma, chimbal, pluck|sino, pad, baixo},
  //        arpejo: [índices], ganho, fade_s }. Instrumento ausente ou 0 não toca.
  function musica(cfg, fim) {
    const inst = cfg.instrumentos || {};
    const BEAT = 60 / cfg.bpm;
    const arp = cfg.arpejo || [0, 1, 2, 1, 2, 0, 1, 2];
    const ini = mixSnapshot();
    for (let bar = 0; bar * 4 * BEAT < fim; bar++) {
      const t0 = bar * 4 * BEAT;
      const [raiz, notas] = cfg.acordes[bar % cfg.acordes.length];
      if (inst.pad) I.pad(t0, notas.map((f) => f / 2), 4 * BEAT, inst.pad);
      if (inst.baixo) {
        I.baixo(t0, raiz, BEAT * 1.5, inst.baixo);
        I.baixo(t0 + 2.5 * BEAT, raiz, BEAT * 1.2, inst.baixo);
      }
      for (let b = 0; b < 4; b++) {
        const tb = t0 + b * BEAT;
        if (inst.kick && (b === 0 || b === 2)) I.kick(tb, inst.kick);
        if (inst.caixa && (b === 1 || b === 3)) I.caixa(tb, inst.caixa);
        if (inst.palma && (b === 1 || b === 3)) I.palma(tb, inst.palma);
        if (inst.chimbal) {
          I.chimbal(tb + BEAT / 2, inst.chimbal);
          I.chimbal(tb, inst.chimbal * 0.6);
        }
      }
      arp.forEach((k, j) => {
        if (bar % 2 === 1 && j % 2 === 1) return;
        const f = notas[k % notas.length] * 2;
        if (inst.pluck) I.pluck(t0 + j * (BEAT / 2), f, inst.pluck, j % 2 ? 0.35 : -0.35);
        if (inst.sino) I.sino(t0 + j * (BEAT / 2), f, inst.sino, j % 2 ? 0.35 : -0.35);
      });
    }
    // fade no fim e ganho da música: só no que a música escreveu (efeitos entram depois)
    // origem: Instragram-Videos/remotion/scripts/audio.mjs:246-247 (fade 1.6 s, ganho 0.55)
    const fade = cfg.fade_s ?? 1.6;
    const g = cfg.ganho ?? 0.55;
    const fi = Math.round((fim - fade) * SR);
    for (let k = 0; k < N; k++) {
      const dl = L[k] - ini.L[k];
      const dr = R[k] - ini.R[k];
      const gf = k < fi ? 1 : Math.max(0, 1 - (k - fi) / (fade * SR));
      L[k] = ini.L[k] + dl * g * gf;
      R[k] = ini.R[k] + dr * g * gf;
    }
  }
  function mixSnapshot() {
    return { L: L.slice(), R: R.slice() };
  }

  function efeito(tipo, t0, dur, vol) {
    if (!SFX[tipo]) throw new Error(`efeito desconhecido: ${tipo} (existem: ${Object.keys(SFX).join(", ")})`);
    SFX[tipo](t0, dur, vol);
  }

  function gravarWav(caminho) {
    const b = Buffer.alloc(44 + N * 4);
    b.write("RIFF", 0);
    b.writeUInt32LE(36 + N * 4, 4);
    b.write("WAVEfmt ", 8);
    b.writeUInt32LE(16, 16);
    b.writeUInt16LE(1, 20);
    b.writeUInt16LE(2, 22);
    b.writeUInt32LE(SR, 24);
    b.writeUInt32LE(SR * 4, 28);
    b.writeUInt16LE(4, 32);
    b.writeUInt16LE(16, 34);
    b.write("data", 36);
    b.writeUInt32LE(N * 4, 40);
    for (let k = 0; k < N; k++) {
      b.writeInt16LE(Math.round(Math.tanh(L[k]) * 32000), 44 + k * 4);
      b.writeInt16LE(Math.round(Math.tanh(R[k]) * 32000), 46 + k * 4);
    }
    fs.writeFileSync(caminho, b);
  }

  return { musica, efeito, gravarWav, EFEITOS: Object.keys(SFX) };
}

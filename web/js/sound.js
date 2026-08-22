/* Barnaby's bell.
 *
 * A jingle bell on the collar, synthesised in Web Audio — no asset files, so
 * the "clone it and run two commands" promise survives and there is no binary
 * blob in the repo.
 *
 * This file is mostly restraint. Gesture is built for brains that find
 * unexpected sound genuinely aversive, and the hardware spec marks the tone
 * **Optional** for exactly that reason. So:
 *
 *   - It rings on the *onset* of a jiggle and never loops. The jiggle itself
 *     has no timeout; a bell that matched it would be torture.
 *   - Circus mode defaults on. Quiet mode defaults off — costume down means
 *     sensory down.
 *   - `prefers-reduced-motion` defaults it off in both modes. There is no
 *     `prefers-reduced-sound`, but someone who has asked the OS to calm things
 *     down has told us enough.
 *   - An explicit choice by the user always beats those defaults, and sticks.
 *   - It is quiet, short, and rolled off above 6kHz so it can't be shrill.
 *
 * The pet chime matters more than the jiggle one. It is the sound of having
 * come back into your body, and it is the only audio feedback in the app that
 * confirms a thing the user *did*.
 */

/* Note name -> Hz, equal temperament, A4 = 440. */
const SEMITONE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

function hz(name) {
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(name);
  if (!m) return 440;
  const [, letter, accidental, octave] = m;
  const midi =
    (Number(octave) + 1) * 12 +
    SEMITONE[letter] +
    (accidental === '#' ? 1 : accidental === 'b' ? -1 : 0);
  return 440 * Math.pow(2, (midi - 69) / 12);
}

/* "Entry of the Gladiators" — Julius Fučík, 1897. Public domain worldwide.
 *
 * A micro-arrangement of the opening, not the march: the long chromatic
 * descent that is the piece's signature, answered by a rising arpeggio so it
 * finishes lifting rather than sinking. A full descent is unmistakably the
 * circus but lands somewhere melancholy, which is the wrong note to start
 * somebody's morning on.
 *
 * Format is [note, length in beats, velocity?] — `null` for a rest. It is
 * plain data on purpose: this was transcribed by ear, so adjusting it is
 * editing one array rather than unpicking synthesis code.
 *
 * The eight-note descent carries a light diminuendo — a flat-velocity
 * chromatic run reads as mechanical, a hand playing it eases off toward the
 * landing — so the sustained E4 underneath it can arrive as the phrase's
 * actual downbeat rather than just the ninth note in a row.
 */
const GLADIATORS = [
  ['C5', 1, 1.15], ['B4', 1, 0.97], ['A#4', 1, 0.94], ['A4', 1, 0.91],
  ['G#4', 1, 0.89], ['G4', 1, 0.87], ['F#4', 1, 0.86], ['F4', 1, 0.85],
  ['E4', 2], [null, 0.5],
  ['E4', 0.5], ['G4', 1], ['C5', 1], ['E5', 2, 1.1],
  ['G5', 4, 1.2],
];

/* Quiet mode gets a morning, not a march. Three rising notes, no metaphor to
 * translate — the same promise the rest of Quiet mode makes. */
const MORNING_QUIET = [
  ['G4', 2], ['C5', 2], ['E5', 4, 0.9],
];

/* The curtain-call flourish: the ten-note grace-note trill that opens
 * "Entry of the Gladiators", transcribed from a music-box MIDI arrangement
 * (General MIDI program 10, Music Box) rather than by ear like GLADIATORS
 * above. Same [note, length in beats, velocity?] format; lengths keep the
 * source's rhythm (eighths either side of a run of sixteenths) and
 * velocities are the MIDI values normalised around their own mean. */
const CURTAIN_FLOURISH = [
  ['D6', 1, 1.11], ['C#6', 1, 1.03], ['C6', 0.5, 0.97], ['C#6', 0.5, 1.03],
  ['C6', 0.5, 0.97], ['B5', 0.5, 1.0], ['A#5', 1, 1.06], ['A5', 1, 0.97],
  ['G#5', 1, 0.94], ['A5', 1.5, 1.03],
];

const Bell = {
  ctx: null,
  master: null,
  enabled: false,
  _lastSettle: 0,
  _overture: null,
  _overtureEnd: null,

  /* Browsers refuse to start audio before a user gesture, so the context is
   * built on first interaction rather than at load. If a check-in comes due
   * before the user has touched anything, there is simply no sound — correct
   * behaviour, and nothing to apologise for. */
  _ensure() {
    if (this.ctx) return this.ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    try {
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.9;

      // Take the glassy top off. A bright synthetic bell is exactly the
      // texture that makes people flinch.
      const soften = this.ctx.createBiquadFilter();
      soften.type = 'lowpass';
      soften.frequency.value = 6200;
      soften.Q.value = 0.6;

      this.master.connect(soften).connect(this.ctx.destination);
    } catch {
      this.ctx = null;
    }
    return this.ctx;
  },

  unlock() {
    const ctx = this._ensure();
    if (ctx && ctx.state === 'suspended') ctx.resume();
  },

  setEnabled(on, { remember = true } = {}) {
    this.enabled = !!on;
    if (remember) localStorage.setItem('gesture.sound', on ? '1' : '0');
    if (on) this.unlock();
    // Muting must cut a phrase that is already playing. Waiting four seconds
    // for the circus to finish after being asked to stop is not muting.
    else this.stopOverture();
  },

  /* One strike of a small bell.
   *
   * Bells are inharmonic — that is what separates them from a flute. These
   * partial ratios are deliberately not integers; with a harmonic series this
   * sounds like an organ, not a bell. Higher partials also decay faster, which
   * is what gives a real bell its bright attack and warm tail.
   */
  _strike(at, freq, gain, decay) {
    const ctx = this.ctx;
    const PARTIALS = [1, 1.51, 2.14, 2.87, 3.63];
    PARTIALS.forEach((ratio, i) => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq * ratio;

      const amp = gain / (i * 1.5 + 1.4);
      const life = decay * (1 - i * 0.13);

      env.gain.setValueAtTime(0.0001, at);
      env.gain.linearRampToValueAtTime(amp, at + 0.004);
      env.gain.exponentialRampToValueAtTime(0.0001, at + life);

      osc.connect(env).connect(this.master);
      osc.start(at);
      osc.stop(at + life + 0.05);
    });
  },

  /* The jiggle bell. Two strikes a breath apart at slightly different
   * pitches — a single strike reads as a notification chime, two read as a
   * bell on a collar that just moved. */
  ring(intensity = 0.6) {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx || ctx.state !== 'running') return;
    const t = ctx.currentTime;
    const g = 0.05 + 0.035 * Math.min(Math.max(intensity, 0), 1);
    this._strike(t, 2340, g, 0.5);
    this._strike(t + 0.055, 2570, g * 0.72, 0.42);
  },

  /* The pet chime: two descending notes, softer and rounder. Settling, not
   * alerting. Throttled so a run of taps can't turn it into a rattle. */
  settle() {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx || ctx.state !== 'running') return;
    if (ctx.currentTime - this._lastSettle < 0.35) return;
    this._lastSettle = ctx.currentTime;
    const t = ctx.currentTime;
    this._strike(t, 1880, 0.045, 0.55);
    this._strike(t + 0.1, 1410, 0.038, 0.7);
  },

  // ------------------------------------------------------------------
  // The morning overture
  // ------------------------------------------------------------------

  /* One tooth of a music-box comb.
   *
   * A comb tooth is a struck cantilever bar, so its partials run much wider
   * than a bell's — roughly 1 : 2 : 3 : 4 : 6 with a bright, fast-fading top.
   * The thin "tinny" quality is mostly the *absence* of low end: the whole
   * voice is high-passed on the bus below, which is what makes it read as a
   * small mechanical object rather than a piano.
   */
  _pluck(at, freq, gain, decay, bus) {
    const ctx = this.ctx;
    const PARTIALS = [1, 2.01, 3.03, 4.16, 6.28];
    const AMPS = [1, 0.55, 0.36, 0.2, 0.11];

    // A hand-cranked box is never quite in tune. A few cents of wander per
    // note is the difference between a music box and a sine wave.
    const wow = 1 + (Math.random() - 0.5) * 0.004;

    PARTIALS.forEach((ratio, i) => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq * ratio * wow;

      const amp = gain * AMPS[i];
      const life = decay * (1 - i * 0.14);

      env.gain.setValueAtTime(0.0001, at);
      env.gain.linearRampToValueAtTime(amp, at + 0.003);
      env.gain.exponentialRampToValueAtTime(0.0001, at + life);

      osc.connect(env).connect(bus);
      osc.start(at);
      osc.stop(at + life + 0.05);
    });

    // The tick of the pin catching the tooth. Tiny, but without it the notes
    // sound synthesised rather than plucked.
    const n = ctx.createBufferSource();
    const buf = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * 0.004), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    }
    n.buffer = buf;
    const ng = ctx.createGain();
    ng.gain.value = gain * 0.28;
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 2600;
    n.connect(hp).connect(ng).connect(bus);
    n.start(at);
  },

  /* The morning overture: Entry of the Gladiators on a small music box.
   *
   * Fires when the day is begun — the tent going up. Kept to a few seconds:
   * it is an overture, not a song, and it plays at the one moment the user
   * has just deliberately pressed a button, so it is never a surprise.
   */
  overture(mode = 'circus') {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx || ctx.state !== 'running') return;

    this.stopOverture();

    const bus = ctx.createGain();
    bus.gain.value = 1;

    // Thin it out. Removing the low end is what makes a music box sound
    // small; the lowpass keeps the metallic top from turning shrill.
    const thin = ctx.createBiquadFilter();
    thin.type = 'highpass';
    thin.frequency.value = 620;
    const soften = ctx.createBiquadFilter();
    soften.type = 'lowpass';
    soften.frequency.value = 7000;

    bus.connect(thin).connect(soften).connect(this.master);
    this._overture = bus;

    const phrase = mode === 'quiet' ? MORNING_QUIET : GLADIATORS;
    const beat = mode === 'quiet' ? 0.26 : 0.2;   // seconds per unit
    const t0 = ctx.currentTime + 0.06;
    let at = t0;

    phrase.forEach(([note, len, vel = 1]) => {
      if (note) {
        const f = hz(note);
        // Long notes ring longer, high notes fade faster — as a real comb does.
        const decay = Math.min(2.4, (beat * len * 2.6) + 0.5) * (f > 900 ? 0.75 : 1);
        this._pluck(at, f, 0.055 * vel, decay, bus);
      }
      at += beat * len;
    });

    // Let the tail ring out, then tear the bus down.
    this._overtureEnd = setTimeout(
      () => this.stopOverture({ fade: 0 }),
      (at - t0 + 2.8) * 1000
    );
  },

  stopOverture({ fade = 0.12 } = {}) {
    clearTimeout(this._overtureEnd);
    const bus = this._overture;
    if (!bus || !this.ctx) return;
    this._overture = null;
    const t = this.ctx.currentTime;
    try {
      bus.gain.cancelScheduledValues(t);
      bus.gain.setValueAtTime(bus.gain.value, t);
      bus.gain.linearRampToValueAtTime(0.0001, t + fade);
    } catch {
      /* the bus may already be gone */
    }
    setTimeout(() => {
      try { bus.disconnect(); } catch { /* already detached */ }
    }, (fade + 0.05) * 1000);
  },

  /* Curtain call and finished acts. The music box's opening trill — the
   * only flourish in the app, and it only ever plays after something is
   * already over. Played at the source MIDI's own tempo (108 BPM, so an
   * eighth note — one length-unit below — is ~0.278s): it earned the
   * couple of seconds that takes, and a rushed version of a music box
   * reads as broken, not brief. */
  flourish() {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx || ctx.state !== 'running') return;

    const bus = ctx.createGain();
    bus.gain.value = 1;
    const thin = ctx.createBiquadFilter();
    thin.type = 'highpass';
    thin.frequency.value = 620;
    const soften = ctx.createBiquadFilter();
    soften.type = 'lowpass';
    soften.frequency.value = 7000;
    bus.connect(thin).connect(soften).connect(this.master);

    const beat = 0.278;
    let at = ctx.currentTime;
    CURTAIN_FLOURISH.forEach(([note, len, vel]) => {
      const f = hz(note);
      const decay = Math.min(1.4, beat * len * 2.6 + 0.3) * 0.75;
      this._pluck(at, f, 0.055 * vel, decay, bus);
      at += beat * len;
    });

    const total = CURTAIN_FLOURISH.reduce((s, [, len]) => s + len, 0) * beat;
    setTimeout(() => {
      try { bus.disconnect(); } catch { /* already detached */ }
    }, (total + 1.6) * 1000);
  },
};

/* Defaults, when the user has not said otherwise. */
function defaultSoundEnabled(mode) {
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return false;
    }
  } catch {
    /* matchMedia is not worth a crash */
  }
  return mode === 'circus';
}

window.Bell = Bell;
window.defaultSoundEnabled = defaultSoundEnabled;

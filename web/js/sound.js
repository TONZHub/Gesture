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

const Bell = {
  ctx: null,
  master: null,
  enabled: false,
  _lastSettle: 0,

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

  /* Curtain call and finished acts. Three rising strikes — the only flourish
   * in the app, and it only ever plays after something is already over. */
  flourish() {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx || ctx.state !== 'running') return;
    const t = ctx.currentTime;
    [1760, 2200, 2640].forEach((f, i) =>
      this._strike(t + i * 0.085, f, 0.042, 0.5)
    );
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

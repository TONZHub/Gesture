/* Barnaby — the on-screen tardigrade.
 *
 * A water bear jester: plump, segmented, slate blue-grey, eight stubby clawed
 * legs, big round eyes, a purple three-lobe cap with gold bells, and a white
 * Pierrot ruff. He breathes constantly, blinks on his own schedule, and when a
 * check-in comes due he shakes until you touch him.
 *
 * The tardigrade is not a costume change. A water bear survives the
 * unsurvivable by curling into a *tun* — it dries out, goes dormant, waits out
 * the bad conditions, then rehydrates and carries on. That is the app's whole
 * posture: a zero-capacity day is a tun, not a failure; held is not dropped;
 * and the water you log is the thing that brings him back.
 *
 * The jiggle still has no timeout. It stops when a hand lands on it, because
 * coming back into your body is the intervention, not the reminder.
 */

const BODY     = '#8f97ab'; // slate blue-grey
const BODY_LT  = '#a8aebf'; // top highlight
const BODY_DK  = '#767d97'; // legs, shading
const BODY_DKR = '#5f6482'; // deep underside
const RUFF     = '#f7f4ec'; // the Pierrot collar
const RUFF_DK  = '#dad6cc'; // ruff shadow
const HAT       = '#8a5cc4'; // purple lobes
const HAT_FRONT = '#403d95'; // indigo front panels
const GOLD      = '#f4c64c'; // bells, band
const GOLD_DK   = '#e0ac38';
const CLAW      = '#33323d';
const DARK       = '#20202a'; // eyes
const MOUTH_IN   = '#7c2c40';
const LIP        = '#c25d70';
const TONGUE     = '#ec93a7';

const EYES = {
  soft: `
    <ellipse cx="80" cy="104" rx="12.5" ry="15" fill="${DARK}"/>
    <ellipse cx="120" cy="104" rx="12.5" ry="15" fill="${DARK}"/>
    <circle cx="84.5" cy="98" r="4.3" fill="#fff"/>
    <circle cx="124.5" cy="98" r="4.3" fill="#fff"/>
    <circle cx="76.5" cy="109" r="2" fill="#fff" opacity=".4"/>
    <circle cx="116.5" cy="109" r="2" fill="#fff" opacity=".4"/>`,

  listening: `
    <ellipse cx="80" cy="103" rx="13.5" ry="16.5" fill="${DARK}"/>
    <ellipse cx="120" cy="103" rx="13.5" ry="16.5" fill="${DARK}"/>
    <circle cx="85" cy="96.5" r="4.8" fill="#fff"/>
    <circle cx="125" cy="96.5" r="4.8" fill="#fff"/>`,

  delighted: `
    <path d="M67 107 Q80 91 93 107" stroke="${DARK}" stroke-width="6.5"
          fill="none" stroke-linecap="round"/>
    <path d="M107 107 Q120 91 133 107" stroke="${DARK}" stroke-width="6.5"
          fill="none" stroke-linecap="round"/>`,

  relieved: `
    <path d="M68 103 Q80 113 92 103" stroke="${DARK}" stroke-width="6"
          fill="none" stroke-linecap="round"/>
    <path d="M108 103 Q120 113 132 103" stroke="${DARK}" stroke-width="6"
          fill="none" stroke-linecap="round"/>`,

  worried: `
    <ellipse cx="80" cy="106" rx="11" ry="12.5" fill="${DARK}"/>
    <ellipse cx="120" cy="106" rx="11" ry="12.5" fill="${DARK}"/>
    <circle cx="83.5" cy="101" r="3.6" fill="#fff"/>
    <circle cx="123.5" cy="101" r="3.6" fill="#fff"/>
    <path d="M67 89 L91 84" stroke="${BODY_DK}" stroke-width="4.5"
          stroke-linecap="round"/>
    <path d="M133 89 L109 84" stroke="${BODY_DK}" stroke-width="4.5"
          stroke-linecap="round"/>`,
};

const MOUTHS = {
  // A gentle closed smile — the resting face from the reference art.
  smile: `<path d="M89 129 Q100 139 111 129" stroke="${DARK}" stroke-width="3.2"
             fill="none" stroke-linecap="round"/>`,

  // The open, delighted mouth with a little tongue — his circus face.
  open: `
    <path d="M89 127 Q100 131 111 127 Q109 145 100 146 Q91 145 89 127 Z"
          fill="${MOUTH_IN}"/>
    <path d="M93.5 139 Q100 149 106.5 139 Q100 143 93.5 139 Z" fill="${TONGUE}"/>
    <path d="M89 127 Q100 131 111 127" stroke="${LIP}" stroke-width="2.4"
          fill="none" stroke-linecap="round"/>`,
};

function mouthFor(face) {
  return face === 'delighted' ? 'open' : 'smile';
}

const SCENE_GLOW = {
  off:      null,
  dim:      '#3a3358',
  overture: '#f2a05c',
  focus:    '#5a7ad0',
  break:    '#63c8a8',
  curtain:  '#c86fa8',
};

/* Claws — the signature of a water bear. A small fan of dark points at a
 * foot, aimed in `dir` (radians). */
function claws(x, y, dir, n = 3, len = 8, spread = 0.42) {
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = dir + (i - (n - 1) / 2) * spread;
    const x2 = x + Math.cos(a) * len;
    const y2 = y + Math.sin(a) * len;
    s += `<path d="M${x.toFixed(1)} ${y.toFixed(1)} L${x2.toFixed(1)} ${y2.toFixed(1)}"
            stroke="${CLAW}" stroke-width="3.4" stroke-linecap="round"/>`;
  }
  return s;
}

/* One plump leg: a rounded haunch with a clawed foot. Drawn before the body,
 * so the body overlaps the top and only the rounded end and claws show. */
function leg(x, y, rx, ry, footX, footY, dir) {
  return `
    <ellipse cx="${x}" cy="${y + 2}" rx="${rx}" ry="${ry}" fill="${BODY_DK}"/>
    <ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${BODY}"/>
    ${claws(footX, footY, dir)}`;
}

/* Eight legs, four pairs, cascading down each side with the two innermost feet
 * meeting at the front. Left side listed; the right is mirrored. */
function legs() {
  const L = [
    // x,   y,   rx, ry, footX, footY, dir(down-and-out)
    [50, 150, 16, 21, 44, 171, 2.05],
    [44, 186, 16, 21, 40, 208, 1.92],
    [58, 212, 15, 19, 54, 233, 1.75],
    [86, 216, 14, 18, 84, 236, 1.62],
  ];
  let s = '';
  for (const [x, y, rx, ry, fx, fy, dir] of L) {
    s += leg(x, y, rx, ry, fx, fy, dir);                       // left
    s += leg(200 - x, y, rx, ry, 200 - fx, fy, Math.PI - dir); // right
  }
  return s;
}

/* The white Pierrot ruff: a scalloped band that dips at the front and rises at
 * the sides, with a soft shadow row behind it. */
function ruff() {
  const N = 12;
  let back = '';
  let front = '';
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const x = 44 + t * 112;
    const y = 139 + Math.sin(t * Math.PI) * 15;
    back += `<circle cx="${x.toFixed(1)}" cy="${(y + 3).toFixed(1)}" r="11.5"
               fill="${RUFF_DK}"/>`;
    front += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="10.5"
                fill="${RUFF}"/>`;
  }
  return back + front;
}

/* A single hat lobe: a purple teardrop from `base` to `tip`, with a narrower
 * indigo front panel and a gold bell at the tip. Parametric so the three lobes
 * and their mirrors stay consistent. */
function lobe(baseX, baseY, tipX, tipY, halfW) {
  const a = Math.atan2(tipY - baseY, tipX - baseX);
  const nx = Math.cos(a + Math.PI / 2);
  const ny = Math.sin(a + Math.PI / 2);
  const dx = tipX - baseX;
  const dy = tipY - baseY;

  const Lx = baseX + nx * halfW, Ly = baseY + ny * halfW;
  const Rx = baseX - nx * halfW, Ry = baseY - ny * halfW;
  // Bow the sides right out near the base so the lobe reads as a fat, floppy
  // teardrop rather than a spike, then converge on the tip.
  const cLx = Lx + dx * 0.28 + nx * halfW * 1.15;
  const cLy = Ly + dy * 0.28 + ny * halfW * 1.15;
  const cRx = Rx + dx * 0.28 - nx * halfW * 1.15;
  const cRy = Ry + dy * 0.28 - ny * halfW * 1.15;

  const outer = `M${Lx.toFixed(1)} ${Ly.toFixed(1)}
    Q${cLx.toFixed(1)} ${cLy.toFixed(1)} ${tipX} ${tipY}
    Q${cRx.toFixed(1)} ${cRy.toFixed(1)} ${Rx.toFixed(1)} ${Ry.toFixed(1)} Z`;

  // Indigo front panel: the whole front-facing half of the lobe. Base runs
  // from the tip-side edge across to the far inner edge, so the two-tone reads
  // clearly the way it does in the reference art.
  const fLx = baseX + nx * halfW * 0.42, fLy = baseY + ny * halfW * 0.42;
  const fRx = baseX - nx * halfW * 0.9, fRy = baseY - ny * halfW * 0.9;
  const front = `M${fLx.toFixed(1)} ${fLy.toFixed(1)}
    Q${(cLx * 0.55 + tipX * 0.45).toFixed(1)} ${(cLy * 0.55 + tipY * 0.45).toFixed(1)}
     ${tipX} ${tipY}
    Q${cRx.toFixed(1)} ${cRy.toFixed(1)} ${fRx.toFixed(1)} ${fRy.toFixed(1)} Z`;

  return `
    <path d="${outer}" fill="${HAT}"/>
    <path d="${front}" fill="${HAT_FRONT}" opacity=".92"/>
    <circle class="b-bell" cx="${tipX}" cy="${tipY}" r="6" fill="${GOLD}"/>
    <circle class="b-bell" cx="${tipX}" cy="${(tipY - 1.6).toFixed(1)}" r="2.2"
            fill="#fff" opacity=".5"/>`;
}

/* The three-lobe jester cap: a gold band across the brow, three purple lobes
 * with bells, and a small gold bell resting on the forehead.
 *
 * The band arches slightly *upward* at the centre so its lowest points sit
 * clear of the raised brows of the `worried` face — a band that eats his
 * eyebrows costs him the whole expression. */
function jesterHat() {
  return `
    <g class="b-hat">
      ${lobe(76, 72, 33, 52, 16)}
      ${lobe(124, 72, 167, 52, 16)}
      ${lobe(100, 68, 100, 22, 17)}

      <!-- gold band across the brow -->
      <path d="M56 82 Q100 73 144 82 L144 72 Q100 62 56 72 Z" fill="${GOLD}"/>
      <path d="M56 82 Q100 73 144 82 L144 79 Q100 70 56 79 Z" fill="${GOLD_DK}"
            opacity=".55"/>

      <!-- the forehead bell -->
      <circle class="b-bell" cx="100" cy="86" r="6.5" fill="${GOLD}"/>
      <circle class="b-bell" cx="98" cy="84" r="2.4" fill="#fff" opacity=".5"/>
    </g>`;
}

function svg(face) {
  return `
<svg class="barnaby" viewBox="0 0 200 250" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Barnaby, a jester tardigrade">

  <ellipse class="b-glow" cx="100" cy="150" rx="98" ry="104" fill="var(--glow, #3a3358)"/>

  <g class="b-body">
    ${legs()}

    <!-- body: head lobe and belly lobe, merged into one plush form -->
    <ellipse cx="100" cy="180" rx="62" ry="60" fill="${BODY}"/>
    <circle cx="100" cy="108" r="52" fill="${BODY}"/>

    <!-- form shading -->
    <ellipse cx="100" cy="214" rx="40" ry="26" fill="${BODY_DKR}" opacity=".35"/>
    <ellipse cx="100" cy="88" rx="40" ry="24" fill="${BODY_LT}" opacity=".5"/>
    <path d="M46 150 Q100 164 154 150" stroke="${BODY_DK}" stroke-width="2.5"
          fill="none" opacity=".3"/>
    <path d="M50 192 Q100 206 150 192" stroke="${BODY_DK}" stroke-width="2.5"
          fill="none" opacity=".28"/>

    ${jesterHat()}

    <g class="b-ruff">${ruff()}</g>

    <g class="b-eyes">${EYES[face] || EYES.soft}</g>
    <g class="b-mouth">${MOUTHS[mouthFor(face)]}</g>
  </g>
</svg>`;
}

class BarnabyView {
  constructor(host) {
    this.host = host;
    this.face = 'soft';
    this.host.innerHTML = svg(this.face);
    this.el = this.host.querySelector('svg');
    this.el.style.cursor = 'pointer';
    this._blink();
  }

  setFace(face) {
    if (!EYES[face] || face === this.face) return;
    this.face = face;
    this.el.querySelector('.b-eyes').innerHTML = EYES[face];
    const mouth = this.el.querySelector('.b-mouth');
    if (mouth) mouth.innerHTML = MOUTHS[mouthFor(face)];
  }

  /* A blink every few seconds is the difference between a graphic and
   * something that is in the room with you. */
  _blink() {
    const tick = () => {
      if (!document.body.contains(this.el)) return;
      if (['soft', 'listening', 'worried'].includes(this.face)) {
        const eyes = this.el.querySelector('.b-eyes');
        const held = this.face;
        eyes.innerHTML = EYES.relieved;
        setTimeout(() => {
          if (this.face === held) eyes.innerHTML = EYES[held];
        }, 130);
      }
      setTimeout(tick, 2600 + Math.random() * 4200);
    };
    setTimeout(tick, 1800 + Math.random() * 2600);
  }

  jiggle(intensity = 0.6) {
    this.el.classList.add('jiggle');
    this.el.style.setProperty('--jiggle-i', intensity);
  }

  still() {
    this.el.classList.remove('jiggle');
  }

  celebrate() {
    this.setFace('delighted');
    this.el.animate(
      [
        { transform: 'translateY(0) rotate(0)' },
        { transform: 'translateY(-14px) rotate(-7deg)' },
        { transform: 'translateY(0) rotate(6deg)' },
        { transform: 'translateY(-7px) rotate(-3deg)' },
        { transform: 'translateY(0) rotate(0)' },
      ],
      { duration: 900, easing: 'cubic-bezier(.22,.68,.36,1)' }
    );
  }

  project(scene) {
    const color = SCENE_GLOW[scene];
    if (!color) {
      this.el.classList.remove('lit');
      return;
    }
    this.el.style.setProperty('--glow', color);
    this.el.classList.add('lit');
  }
}

/* One Barnaby, many windows onto him. Every slot in the DOM shows the same
 * state, so he never contradicts himself between screens. */
window.Barnaby = {
  views: [],

  mountAll() {
    this.views = [];
    document.querySelectorAll('[data-barnaby]').forEach((host) => {
      this.views.push(new BarnabyView(host));
    });
    return this.views;
  },

  each(fn) { this.views.forEach(fn); },
  setFace(f)    { this.each((v) => v.setFace(f)); },
  still()       { this.each((v) => v.still()); },
  project(s)    { this.each((v) => v.project(s)); },

  /* The bell rings on the *transition* into jiggling, never on the state.
   * A due check-in re-broadcasts on reconnect and on every sync, and a
   * reminder that re-rings each time you open a tab is a reminder people
   * learn to mute. */
  jiggle(i, { silent = false } = {}) {
    const wasStill = !this.jiggling;
    this.each((v) => v.jiggle(i));
    if (wasStill && !silent && window.Bell) window.Bell.ring(i);
  },

  celebrate() {
    this.each((v) => v.celebrate());
    if (window.Bell) window.Bell.flourish();
  },

  get jiggling() {
    return this.views.some((v) => v.el.classList.contains('jiggle'));
  },
};

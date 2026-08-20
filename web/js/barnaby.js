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

/* Whether the viewer has asked the OS to reduce motion. Checked live so it is
 * correct even if the setting changes mid-session. */
const reduceMotion = () => {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
};

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
 * meeting at the front. Left side listed; the right is mirrored.
 *
 * `hideFront` drops the top pair, so an act pose can raise those two as arms
 * to grip a bar or throw a ball without giving him ten limbs. */
function legs(hideFront = false) {
  const L = [
    // x,   y,   rx, ry, footX, footY, dir(down-and-out)
    [50, 150, 16, 21, 44, 171, 2.05],
    [44, 186, 16, 21, 40, 208, 1.92],
    [58, 212, 15, 19, 54, 233, 1.75],
    [86, 216, 14, 18, 84, 236, 1.62],
  ];
  let s = '';
  for (let i = hideFront ? 1 : 0; i < L.length; i++) {
    const [x, y, rx, ry, fx, fy, dir] = L[i];
    s += leg(x, y, rx, ry, fx, fy, dir);                       // left
    s += leg(200 - x, y, rx, ry, 200 - fx, fy, Math.PI - dir); // right
  }
  return s;
}

/* A raised arm: a plump limb from a shoulder to a little clawed hand. Used by
 * the act poses in place of the front legs. */
function arm(sx, sy, hx, hy, w = 14) {
  const a = Math.atan2(hy - sy, hx - sx);
  return `
    <path d="M${sx} ${sy} L${hx} ${hy}" stroke="${BODY_DK}"
          stroke-width="${w + 3}" stroke-linecap="round"/>
    <path d="M${sx} ${sy} L${hx} ${hy}" stroke="${BODY}"
          stroke-width="${w}" stroke-linecap="round"/>
    ${claws(hx, hy, a, 3, 5.5, 0.5)}`;
}

/* A striped circus ball, the same make as the ones on his cap. */
function circusBall(x, y, r, c1) {
  return `
    <circle cx="${x}" cy="${y}" r="${r}" fill="${GOLD}"/>
    <path d="M${x} ${y - r} a${r} ${r} 0 0 1 0 ${2 * r} z" fill="${c1}"/>
    <circle cx="${(x - r * 0.35).toFixed(1)}" cy="${(y - r * 0.35).toFixed(1)}"
            r="${(r * 0.3).toFixed(1)}" fill="#fff" opacity=".5"/>`;
}

/* A stroked arc from a1° to a2° on a circle — for the hoop. */
function arcPath(cx, cy, r, a1, a2) {
  const rad = (d) => (d * Math.PI) / 180;
  const x1 = cx + r * Math.cos(rad(a1)), y1 = cy + r * Math.sin(rad(a1));
  const x2 = cx + r * Math.cos(rad(a2)), y2 = cy + r * Math.sin(rad(a2));
  const large = Math.abs(a2 - a1) > 180 ? 1 : 0;
  const sweep = a2 > a1 ? 1 : 0;
  return `M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 ${large} ${sweep} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
}

const BALLS = ['#ff87b4', '#6fc7d1', '#8b6bc4', '#7fcf9e', '#f2a05c'];

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

/* The inner body groups, shared by the live companion and the act poses.
 * `opts.hideFrontLegs` drops the top leg pair; `opts.arms` injects raised arms
 * (drawn in front of the ruff). */
function barnabyInner(face, opts = {}) {
  return `
  <g class="b-body">
    ${legs(opts.hideFrontLegs)}

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
    ${opts.arms || ''}
    <g class="b-eyes">${EYES[face] || EYES.soft}</g>
    <g class="b-mouth">${MOUTHS[mouthFor(face)]}</g>
  </g>`;
}

/* Everything inside the <svg>: the glow, the act props (if a pose is given),
 * and the body between them. Shared by the live companion and the still act
 * thumbnails — the only difference is whether the glow layer is present. */
function barnabyMarkup(face, pose, { glow = true } = {}) {
  const art = ACT_ART[pose] || {};
  const opts = { hideFrontLegs: !!art.hideFrontLegs, arms: art.arms || '' };
  return `
  ${glow ? `<ellipse class="b-glow" cx="100" cy="150" rx="98" ry="104" fill="var(--glow, #3a3358)"/>` : ''}
  ${art.behind || ''}
  ${barnabyInner(face, opts)}
  ${art.front || ''}`;
}

function svg(face, pose) {
  return `
<svg class="barnaby" viewBox="0 0 200 250" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Barnaby, a jester tardigrade">
  ${barnabyMarkup(face, pose, { glow: true })}
</svg>`;
}

/* The six acts, each drawn as Barnaby performing it — the reference poses.
 * `behind` sits below him (ropes, the back of the hoop), `arms` replaces his
 * front legs, `front` sits over him (the bar, the pole, the balls he throws). */
const ROPE = '#c8a06a';
const POLE = '#8b6bc4';

/* A plate spinning on the tip of a pole — a flattened disc, a gold rim, and a
 * faint motion arc so it reads as still turning rather than sitting there. */
function spinPlate(cx, cy) {
  return `
    <ellipse cx="${cx}" cy="${cy}" rx="22" ry="6.5" fill="${RUFF}"
             stroke="${GOLD}" stroke-width="2"/>
    <ellipse cx="${cx}" cy="${cy - 1.5}" rx="12" ry="3.2" fill="none"
             stroke="${GOLD_DK}" stroke-width="1.2" opacity=".55"/>
    <path d="M${cx - 27} ${cy - 5} Q${cx} ${cy - 12} ${cx + 27} ${cy - 5}"
          stroke="${BODY_LT}" stroke-width="1.6" fill="none" opacity=".35"/>`;
}

const ACT_ART = {
  // Juggling — arms up, striped balls arcing to either side of the cap.
  juggling: {
    hideFrontLegs: true,
    arms: arm(64, 150, 52, 116) + arm(136, 150, 148, 116),
    front: `
      <path d="M40 96 Q46 66 74 52" stroke="${BODY_LT}" stroke-width="2"
            fill="none" opacity=".4"/>
      <path d="M160 96 Q154 66 126 52" stroke="${BODY_LT}" stroke-width="2"
            fill="none" opacity=".4"/>
      ${circusBall(52, 112, 11, BALLS[0])}
      ${circusBall(148, 112, 11, BALLS[1])}
      ${circusBall(38, 74, 10, BALLS[2])}
      ${circusBall(162, 74, 10, BALLS[3])}`,
  },

  // Hoops — a ring he stands inside, purple with gold segments.
  hoops: {
    behind: `
      <circle cx="100" cy="132" r="95" fill="none" stroke="${POLE}" stroke-width="9"/>
      <path d="${arcPath(100, 132, 95, 196, 236)}" stroke="${GOLD}"
            stroke-width="9" fill="none" stroke-linecap="round"/>
      <path d="${arcPath(100, 132, 95, 8, 40)}" stroke="${GOLD}"
            stroke-width="9" fill="none" stroke-linecap="round"/>`,
    front: `
      <path d="${arcPath(100, 132, 95, 40, 140)}" stroke="${POLE}"
            stroke-width="9" fill="none"/>
      <path d="${arcPath(100, 132, 95, 92, 128)}" stroke="${GOLD}"
            stroke-width="9" fill="none" stroke-linecap="round"/>`,
  },

  // Balancing — the calm, steady one. The plain resting pose from the art.
  balancing: {},

  // Tightrope — a rope underfoot and a long balance pole held across.
  tightrope: {
    hideFrontLegs: true,
    behind: `
      <line x1="0" y1="239" x2="200" y2="239" stroke="${ROPE}" stroke-width="4.5"/>
      <line x1="0" y1="237.5" x2="200" y2="237.5" stroke="#e0c49a"
            stroke-width="1.4" opacity=".7"/>`,
    arms: arm(66, 152, 58, 150) + arm(134, 152, 142, 150),
    front: `
      <line x1="12" y1="150" x2="188" y2="150" stroke="${POLE}" stroke-width="6"
            stroke-linecap="round"/>
      <circle cx="12" cy="150" r="6" fill="${GOLD}"/>
      <circle cx="188" cy="150" r="6" fill="${GOLD}"/>`,
  },

  // Trapeze — two ropes to a bar he grips with both hands.
  trapeze: {
    hideFrontLegs: true,
    behind: `
      <line x1="50" y1="4" x2="58" y2="150" stroke="${ROPE}" stroke-width="4"/>
      <line x1="150" y1="4" x2="142" y2="150" stroke="${ROPE}" stroke-width="4"/>`,
    arms: arm(64, 150, 58, 148) + arm(136, 150, 142, 148),
    front: `
      <line x1="54" y1="150" x2="146" y2="150" stroke="${POLE}" stroke-width="6"
            stroke-linecap="round"/>
      <circle cx="54" cy="150" r="6" fill="${GOLD}"/>
      <circle cx="146" cy="150" r="6" fill="${GOLD}"/>`,
  },

  // Plate spinning — recurring upkeep. A pole in each hand, a plate turning on
  // each tip. He taps them so they don't fall; he never carries one.
  plates: {
    hideFrontLegs: true,
    arms: arm(64, 150, 54, 148) + arm(136, 150, 146, 148),
    front: `
      <line x1="54" y1="150" x2="45" y2="66" stroke="${POLE}" stroke-width="5"
            stroke-linecap="round"/>
      <line x1="146" y1="150" x2="155" y2="66" stroke="${POLE}" stroke-width="5"
            stroke-linecap="round"/>
      ${spinPlate(45, 62)}
      ${spinPlate(155, 62)}`,
  },
};

/* Barnaby performing an act. Static — no breathing, no glow, no BarnabyView. */
function actScene(kind, face = 'soft') {
  return `
<svg class="barnaby act-art" viewBox="0 0 200 250" xmlns="http://www.w3.org/2000/svg"
     role="img" aria-label="Barnaby performing ${kind}">
  ${barnabyMarkup(face, kind, { glow: false })}
</svg>`;
}

class BarnabyView {
  constructor(host) {
    this.host = host;
    this.slot = host.dataset.barnaby || '';
    this.face = 'soft';
    this.pose = null;
    this.host.innerHTML = svg(this.face, this.pose);
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

  /* Adopt (or clear) an act pose. Re-renders the SVG's contents in place, so
   * the <svg> element itself — and with it the jiggle/lit classes, the --glow
   * variable and the click handler — carries over untouched. */
  setPose(pose) {
    pose = pose || null;
    if (pose === this.pose) return;
    this.pose = pose;
    this.el.innerHTML = barnabyMarkup(this.face, this.pose, { glow: true });
  }

  /* A blink every few seconds is the difference between a graphic and
   * something that is in the room with you. Skipped under reduced-motion —
   * a blink is small, but it is still motion — and re-checked on every tick
   * rather than once at startup, so a preference flipped mid-session (the OS
   * setting, or a dev tool) takes effect without a reload. */
  _blink() {
    const tick = () => {
      if (!document.body.contains(this.el)) return;
      if (!reduceMotion() && ['soft', 'listening', 'worried'].includes(this.face)) {
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
    // The delighted face is the celebration; the hop is the flourish on top.
    // Under reduced-motion, keep the face and drop the hop.
    this.setFace('delighted');
    if (reduceMotion()) return;
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

  /* Barnaby performing an act, as an SVG string — the act header art. */
  actArt(kind, face = 'soft') { return actScene(kind, face); },

  /* Have the live companion adopt an act pose. Only the day-screen Barnaby by
   * default — the dock and the overlays stay in their resting pose. Pass null
   * to return him to standing. */
  setPose(pose, slots = ['day']) {
    this.each((v) => { if (slots.includes(v.slot)) v.setPose(pose); });
  },

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

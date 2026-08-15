/* Barnaby — the on-screen seal.
 *
 * Round, dusty rose, dark too-big eyes, whiskers, purple jester collar, one
 * ball balanced above his nose. He breathes constantly, blinks on his own
 * schedule, and when a check-in comes due he shakes until you touch him.
 *
 * That last part is the whole hardware thesis running in software: the jiggle
 * has no timeout. It stops when a hand lands on it, because coming back into
 * your body is the intervention, not the reminder.
 */

const FUR       = '#c98fa8';
const FUR_DARK  = '#a86e89';
const BELLY     = '#e9c3d2';
const DARK      = '#241726';
const COLLAR    = '#7b5ea7';
const COLLAR_HI = '#9878c9';
const GOLD      = '#f2c98d';

const EYES = {
  soft: `
    <ellipse cx="80" cy="104" rx="12.5" ry="14.5" fill="${DARK}"/>
    <ellipse cx="120" cy="104" rx="12.5" ry="14.5" fill="${DARK}"/>
    <circle cx="84.5" cy="98.5" r="4.2" fill="#fff" opacity=".92"/>
    <circle cx="124.5" cy="98.5" r="4.2" fill="#fff" opacity=".92"/>
    <circle cx="76" cy="109" r="2" fill="#fff" opacity=".45"/>
    <circle cx="116" cy="109" r="2" fill="#fff" opacity=".45"/>`,

  listening: `
    <ellipse cx="80" cy="103" rx="13.5" ry="16" fill="${DARK}"/>
    <ellipse cx="120" cy="103" rx="13.5" ry="16" fill="${DARK}"/>
    <circle cx="85" cy="97" r="4.8" fill="#fff" opacity=".95"/>
    <circle cx="125" cy="97" r="4.8" fill="#fff" opacity=".95"/>`,

  delighted: `
    <path d="M67 108 Q80 92 93 108" stroke="${DARK}" stroke-width="6.5"
          fill="none" stroke-linecap="round"/>
    <path d="M107 108 Q120 92 133 108" stroke="${DARK}" stroke-width="6.5"
          fill="none" stroke-linecap="round"/>`,

  relieved: `
    <path d="M68 104 Q80 114 92 104" stroke="${DARK}" stroke-width="6"
          fill="none" stroke-linecap="round"/>
    <path d="M108 104 Q120 114 132 104" stroke="${DARK}" stroke-width="6"
          fill="none" stroke-linecap="round"/>`,

  worried: `
    <ellipse cx="80" cy="106" rx="11" ry="12" fill="${DARK}"/>
    <ellipse cx="120" cy="106" rx="11" ry="12" fill="${DARK}"/>
    <circle cx="83.5" cy="101" r="3.6" fill="#fff" opacity=".9"/>
    <circle cx="123.5" cy="101" r="3.6" fill="#fff" opacity=".9"/>
    <path d="M67 88 L91 83" stroke="${DARK}" stroke-width="4.5"
          stroke-linecap="round"/>
    <path d="M133 88 L109 83" stroke="${DARK}" stroke-width="4.5"
          stroke-linecap="round"/>`,
};

const SCENE_GLOW = {
  off:      null,
  dim:      '#3a3358',
  overture: '#f2a05c',
  focus:    '#5a7ad0',
  break:    '#63c8a8',
  curtain:  '#c86fa8',
};

/* The hanging points of the jester collar, following the curve of the band so
 * the middle ones sit lower than the ones at his shoulders. */
function collarPoints() {
  const pts = [
    { x: 60,  y: 158 },
    { x: 80,  y: 166 },
    { x: 100, y: 169 },
    { x: 120, y: 166 },
    { x: 140, y: 158 },
  ];
  return pts
    .map(
      (p) => `
      <path d="M${p.x - 10} ${p.y} L${p.x + 10} ${p.y} L${p.x} ${p.y + 18} Z"
            fill="${COLLAR}"/>
      <circle class="b-bell" cx="${p.x}" cy="${p.y + 21}" r="4" fill="${GOLD}"/>`
    )
    .join('');
}

function svg(face) {
  return `
<svg class="barnaby" viewBox="0 0 200 250" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Barnaby, a round circus seal">

  <ellipse class="b-glow" cx="100" cy="140" rx="96" ry="104" fill="var(--glow, #3a3358)"/>

  <!-- the balanced ball -->
  <g class="b-ball">
    <circle cx="100" cy="40" r="17" fill="${GOLD}"/>
    <path d="M100 23 a17 17 0 0 1 0 34 z" fill="${'#ef8fb4'}"/>
    <circle cx="94" cy="33" r="4.5" fill="#fff" opacity=".55"/>
  </g>

  <g class="b-body">
    <!-- flippers -->
    <ellipse cx="42" cy="196" rx="19" ry="12" fill="${FUR_DARK}"
             transform="rotate(-22 42 196)"/>
    <ellipse cx="158" cy="196" rx="19" ry="12" fill="${FUR_DARK}"
             transform="rotate(22 158 196)"/>
    <!-- tail -->
    <ellipse cx="100" cy="228" rx="30" ry="11" fill="${FUR_DARK}"/>

    <!-- body -->
    <ellipse cx="100" cy="178" rx="62" ry="50" fill="${FUR}"/>
    <ellipse cx="100" cy="188" rx="40" ry="36" fill="${BELLY}" opacity=".55"/>

    <!-- head -->
    <circle cx="100" cy="112" r="54" fill="${FUR}"/>

    <!-- jester collar: drawn after the head so it sits at the neck in front
         of it, rather than being swallowed by the skull. -->
    <g class="b-collar">
      ${collarPoints()}
      <path d="M52 146 Q100 168 148 146 L148 158 Q100 180 52 158 Z"
            fill="${COLLAR}"/>
      <path d="M52 146 Q100 168 148 146 Q100 172 52 152 Z" fill="${COLLAR_HI}"/>
    </g>

    <!-- whiskers -->
    <g stroke="${DARK}" stroke-width="1.6" stroke-linecap="round" opacity=".62">
      <path d="M78 130 L48 124"/><path d="M78 134 L46 136"/>
      <path d="M78 138 L49 147"/>
      <path d="M122 130 L152 124"/><path d="M122 134 L154 136"/>
      <path d="M122 138 L151 147"/>
    </g>

    <!-- snout -->
    <ellipse cx="100" cy="134" rx="21" ry="15" fill="${BELLY}"/>
    <ellipse cx="100" cy="126" rx="7.5" ry="5.5" fill="${DARK}"/>
    <path d="M100 131 Q94 139 88 134" stroke="${DARK}" stroke-width="2.2"
          fill="none" stroke-linecap="round"/>
    <path d="M100 131 Q106 139 112 134" stroke="${DARK}" stroke-width="2.2"
          fill="none" stroke-linecap="round"/>

    <!-- eyes -->
    <g class="b-eyes">${EYES[face] || EYES.soft}</g>
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
  jiggle(i)     { this.each((v) => v.jiggle(i)); },
  still()       { this.each((v) => v.still()); },
  celebrate()   { this.each((v) => v.celebrate()); },
  project(s)    { this.each((v) => v.project(s)); },
  get jiggling() {
    return this.views.some((v) => v.el.classList.contains('jiggle'));
  },
};

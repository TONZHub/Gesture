/* The Window.
 *
 * Your week as a sky that shifts from night to day. Each day is a vertical
 * band painted in its own light, feathered into its neighbours so the week
 * reads as one continuous piece of weather rather than seven bars — because a
 * bar chart invites comparison between days, and comparison between days is
 * the thing that makes every other tracker hurt to open.
 *
 * You feel it before you read it. The numbers are underneath, for later.
 */

const BAND_COLORS = {
  three_am:   ['#05070f', '#0b1020', '#161d33'],
  predawn:    ['#0a1024', '#1b2447', '#3a3f63'],
  magic_hour: ['#233056', '#6b5a76', '#c99a72'],
  dawn:       ['#3b4a7a', '#a886a0', '#f0c48a'],
  // Deliberately neutral, not navy — a day with no data is a blank, not a
  // very dark night. Slate grays read as "we don't know" without borrowing
  // the hue that three_am and predawn use to mean "we know, and it was
  // rough," the same distinction the dashed absence-tick below draws.
  unlit:      ['#121218', '#18181f', '#232229'],
};

/* Deterministic star field — a redraw must not reshuffle the sky. */
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function colsFor(day) {
  if (!day.lit) return BAND_COLORS.unlit;
  return BAND_COLORS[day.band] || BAND_COLORS.predawn;
}

function paintColumn(ctx, x, w, h, colors, alpha) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, colors[0]);
  g.addColorStop(0.55, colors[1]);
  g.addColorStop(1, colors[2]);
  ctx.globalAlpha = alpha;
  ctx.fillStyle = g;
  ctx.fillRect(x, 0, w, h);
  ctx.globalAlpha = 1;
}

function renderSky(canvas, sky) {
  const ctx = canvas.getContext('2d');
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = canvas.getBoundingClientRect();
  const w = Math.max(rect.width, 320);
  const h = Math.max(rect.width * 0.48, 220);

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.height = h + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const days = sky.days && sky.days.length ? sky.days : [{ lit: false }];
  const colW = w / days.length;

  // --- day bands, painted offscreen then feathered ------------------------
  const off = document.createElement('canvas');
  off.width = w * dpr;
  off.height = h * dpr;
  const octx = off.getContext('2d');
  octx.setTransform(dpr, 0, 0, dpr, 0, 0);

  paintColumn(octx, 0, w, h, sky.colors || BAND_COLORS.unlit, 1);
  days.forEach((d, i) => {
    // Overlap each band into its neighbours; the blur below does the rest.
    // A day we only partly heard from is painted faintly, so it reads as
    // uncertain rather than as a confident middling day.
    const alpha = d.lit ? 0.4 + 0.5 * (d.coverage ?? 1) : 0.9;
    paintColumn(octx, i * colW - colW * 0.3, colW * 1.6, h, colsFor(d), alpha);
  });

  ctx.save();
  ctx.filter = 'blur(26px)';
  ctx.drawImage(off, 0, 0, w, h);
  ctx.restore();

  // --- stars, denser where the week was darker ----------------------------
  const rand = mulberry32(1897); // Fučík, Entry of the Gladiators
  for (let i = 0; i < 260; i++) {
    const x = rand() * w;
    const y = rand() * h * 0.82;
    const idx = Math.min(days.length - 1, Math.floor(x / colW));
    const light = days[idx].lit ? days[idx].light : 0.12;
    const alpha = Math.max(0, 0.85 - light * 1.15) * (0.35 + rand() * 0.65);
    if (alpha <= 0.02) continue;
    const r = rand() * 1.25 + 0.35;
    ctx.globalAlpha = alpha * (1 - (y / h) * 0.55);
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;

  // --- horizon: the threshold the whole metaphor turns on -----------------
  const horizon = h * 0.86;
  const glow = ctx.createLinearGradient(0, horizon - h * 0.28, 0, horizon);
  const warm = (sky.light ?? 0) > 0.45 ? 'rgba(242,201,141,' : 'rgba(120,120,190,';
  glow.addColorStop(0, warm + '0)');
  glow.addColorStop(1, warm + (0.1 + (sky.light ?? 0) * 0.4) + ')');
  ctx.fillStyle = glow;
  ctx.fillRect(0, horizon - h * 0.28, w, h * 0.28);

  ctx.fillStyle = 'rgba(6,4,12,.92)';
  ctx.fillRect(0, horizon, w, h - horizon);

  // --- day labels ---------------------------------------------------------
  ctx.font = '500 11px ui-rounded, system-ui, sans-serif';
  ctx.textAlign = 'center';
  days.forEach((d, i) => {
    if (!d.date) return;
    const label = new Date(d.date + 'T00:00:00').toLocaleDateString(undefined, {
      weekday: 'short',
    });
    ctx.fillStyle = d.lit ? 'rgba(247,239,230,.72)' : 'rgba(247,239,230,.26)';
    ctx.fillText(label, i * colW + colW / 2, h - 12);
  });

  // A dashed tick under days with no data — absence, marked as absence rather
  // than quietly rendered as a bad day.
  ctx.strokeStyle = 'rgba(247,239,230,.22)';
  ctx.setLineDash([3, 4]);
  days.forEach((d, i) => {
    if (d.lit) return;
    ctx.beginPath();
    ctx.moveTo(i * colW + colW * 0.3, horizon + 8);
    ctx.lineTo(i * colW + colW * 0.7, horizon + 8);
    ctx.stroke();
  });
  ctx.setLineDash([]);
}

window.renderSky = renderSky;

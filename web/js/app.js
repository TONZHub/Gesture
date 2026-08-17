/* Gesture — app controller. */

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const api = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

/* Two vocabularies for the same interface. Quiet mode is not a reduced
 * feature set — it is the same app with the metaphor load removed, because
 * for a chunk of autistic users the metaphor is friction, not charm. */
const COPY = {
  circus: {
    'capacity-label': 'How many balls can you catch today?',
    'intention-label': 'Anything you want to tell me about today?',
    'acts-label': "What's your act today?",
    'begin-cta': 'Raise the curtain',
    'window-cta': 'The Window',
    'curtain-cta': 'Curtain call',
    'stuck-q': 'Where are you stuck right now?',
  },
  quiet: {
    'capacity-label': 'How much have you got today?',
    'intention-label': 'Anything you want to note about today?',
    'acts-label': 'What are you doing today?',
    'begin-cta': 'Begin',
    'window-cta': 'This week',
    'curtain-cta': 'End the day',
    'stuck-q': 'What is in the way right now?',
  },
};

const ANCHORS = [
  ['cant_start',    "I can't start",        'The wall is right at the beginning.'],
  ['forgot_flow',   'I lost the thread',    'It was in my hands a minute ago.'],
  ['scared',        "I'm scared of it",     'Something about this one has teeth.'],
  ['zero_capacity', "I've got nothing left", 'Not tired. Empty.'],
  ['brain_dump',    'Everything at once',   'All of it, no order, right now.'],
];

const MOODS = {
  circus: ['🫠', '😞', '😐', '🙂', '✨'],
  quiet:  ['1', '2', '3', '4', '5'],
};

const state = {
  mode: localStorage.getItem('gesture.mode') || null,
  draftActs: [],
  selectedKind: 'juggling',
  catalogue: [],
  checkin: { id: null, weight: 'full', mood: null, water: 0 },
  stuckAnchor: null,
  polling: null,
};

/* ------------------------------------------------------------------ screens */

function show(name) {
  $$('.screen').forEach((s) => (s.hidden = s.dataset.screen !== name));
  // The dock (pet / ground / bell) belongs to Barnaby once the day is under
  // way — not during onboarding. Hidden on the begin screen, shown elsewhere.
  // (It used to also check state.mode, but applyMode sets that while merely
  // painting the door, which flipped the dock visible mid-onboarding.)
  $('#dock').hidden = name === 'begin';
  $('#stuck-fab').hidden = name === 'begin';
  window.scrollTo({ top: 0 });
}

function applyMode(mode) {
  state.mode = mode;
  localStorage.setItem('gesture.mode', mode);
  document.documentElement.dataset.mode = mode;
  const copy = COPY[mode];
  $$('[data-copy]').forEach((el) => {
    if (copy[el.dataset.copy]) el.textContent = copy[el.dataset.copy];
  });
  renderMoods();

  syncSound(mode);
}

/* Sound follows the mode only until the user has an opinion. Once they have
 * touched the toggle, that choice outranks the mode forever — switching to
 * Circus must never hand someone back a sound they turned off. */
function syncSound(mode = state.mode || 'circus') {
  const stored = localStorage.getItem('gesture.sound');
  window.Bell.setEnabled(
    stored === null ? window.defaultSoundEnabled(mode) : stored === '1',
    { remember: false }
  );
  renderSoundToggle();
}

function renderSoundToggle() {
  const on = window.Bell.enabled;
  const btn = $('#btn-sound');
  const icon = btn.querySelector('span');
  if (icon) icon.textContent = on ? '🔔' : '🔕';
  btn.setAttribute('aria-pressed', String(on));
  const label = on ? "Barnaby's bell, currently on" : "Barnaby's bell, currently off";
  btn.setAttribute('aria-label', label);
  btn.title = label;
}

/* ------------------------------------------------------------------ begin */

function capacityWord(v) {
  if (v <= 0) return 'Nothing left';
  if (v < 15) return 'Survival';
  if (v < 40) return 'Low';
  if (v < 65) return 'Steady';
  if (v < 85) return 'Good';
  return state.mode === 'quiet' ? 'Plenty' : 'Full circus';
}

function renderCapacity() {
  const v = +$('#capacity').value;
  $('#capacity-out').textContent = capacityWord(v);
  $('.battery-fill').style.width = v + '%';
  const balls = v <= 0 ? 0 : v < 25 ? 1 : v < 40 ? 2 : v < 65 ? 3 : v < 85 ? 4 : 5;
  $('#balls-hint').textContent = balls === 0
    ? (state.mode === 'circus'
        ? "Nothing goes in the air. Barnaby holds all of it."
        : "Nothing in play. Barnaby holds all of it.")
    : (state.mode === 'circus'
        ? `About ${balls} ball${balls === 1 ? '' : 's'} in the air. The rest wait with Barnaby.`
        : `About ${balls} thing${balls === 1 ? '' : 's'} in play. The rest wait.`);
}

function renderActKinds() {
  $('#act-kinds').innerHTML = state.catalogue.map((k) => `
    <button class="act-kind" data-kind="${k.kind}" type="button"
            aria-pressed="${k.kind === state.selectedKind}" title="${escapeHtml(k.blurb)}">
      <span class="act-name">${escapeHtml(k.name)}</span>
      <span class="act-art-slot">${window.Barnaby.actArt(k.kind)}</span>
    </button>`).join('');

  $$('#act-kinds .act-kind').forEach((b) => {
    b.onclick = () => {
      state.selectedKind = b.dataset.kind;
      $$('#act-kinds .act-kind').forEach((o) =>
        o.setAttribute('aria-pressed', o === b));
    };
  });
}

function renderDraft() {
  $('#act-draft').innerHTML = state.draftActs.map((a, i) => {
    const k = state.catalogue.find((c) => c.kind === a.kind);
    return `<li><span class="k">${k ? k.name : a.kind}</span>
              <span>${escapeHtml(a.title)}</span>
              <button class="x" data-i="${i}" aria-label="Remove">✕</button></li>`;
  }).join('');
  $$('#act-draft .x').forEach((b) => {
    b.onclick = () => { state.draftActs.splice(+b.dataset.i, 1); renderDraft(); };
  });
}

function addDraftAct() {
  const title = $('#act-title').value.trim();
  if (!title) return;
  state.draftActs.push({ kind: state.selectedKind, title });
  $('#act-title').value = '';
  renderDraft();
}

/* ------------------------------------------------------------------ day */

function renderBalls(inPlay, held) {
  $('#balls').innerHTML = inPlay.map((a) => `
    <button class="ball ${a.done ? 'done' : ''}" data-id="${a.id}">
      <span class="act-mini">${window.Barnaby.actArt(a.kind)}</span>
      <span class="t">
        <b>${escapeHtml(a.title)}</b>
        <span>${labelFor(a.kind)}</span>
      </span>
    </button>`).join('') || `<p class="hint">Nothing in play right now.</p>`;

  $$('#balls .ball').forEach((b) => {
    b.onclick = async () => {
      const done = !b.classList.contains('done');
      b.classList.toggle('done', done);
      const r = await api.patch(`/api/acts/${b.dataset.id}`, { done });
      renderBalls(r.in_play, r.held);
    };
  });

  // The live companion is "on" whatever act he's working right now — the first
  // one not yet done. When they're all done, or nothing is in play, he stands.
  const current = inPlay.find((a) => !a.done);
  window.Barnaby.setPose(current ? current.kind : null);

  $('#held-wrap').hidden = !held.length;
  if (held.length) {
    $('#held-label').textContent = state.mode === 'circus'
      ? `Barnaby is holding ${held.length}. They are not going anywhere.`
      : `${held.length} set aside for now. They'll keep.`;
    $('#held-list').innerHTML = held.map((a) =>
      `<li><span>${escapeHtml(a.title)}</span></li>`).join('');
  }
}

function labelFor(kind) {
  const k = state.catalogue.find((c) => c.kind === kind);
  return k ? k.name : kind;
}

function renderRhythm(r) {
  if (!r) return;
  const next = r.next_at
    ? new Date(r.next_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;
  $('#rhythm-summary').textContent = next
    ? `Barnaby comes back around ${next} · every ~${r.interval_minutes} min`
    : `No more check-ins today. The day's window has closed.`;
  $('#rhythm-notes').textContent = r.notes.join(' ');
  $('#rhythm-factors').innerHTML = Object.entries(r.factors).map(([k, v]) => `
    <tr class="${v > 1 ? 'up' : ''}">
      <td>${k}</td><td>×${v.toFixed(2)}</td>
    </tr>`).join('') +
    `<tr><td>base</td><td>${r.base_minutes} min</td></tr>` +
    `<tr><td>dismissed in a row</td><td>${r.dismiss_streak}</td></tr>`;
}

async function refreshDay(sayText) {
  const s = await api.get('/api/state');
  state.catalogue = s.acts_catalogue;
  renderBalls(s.in_play, s.held);
  renderRhythm(s.rhythm);
  if (sayText) $('#day-say').textContent = sayText;
  $('#btn-curtain').hidden = false;
  if (s.checkin_due) openCheckin();
  return s;
}

/* ------------------------------------------------------------------ check-in */

function renderMoods() {
  const set = MOODS[state.mode || 'circus'];
  $('#moods').innerHTML = set.map((m, i) => `
    <button class="mood" data-v="${i + 1}" aria-pressed="false"
            aria-label="Mood ${i + 1} of 5"><span aria-hidden="true">${m}</span></button>`).join('');
  $$('#moods .mood').forEach((b) => {
    b.onclick = () => {
      state.checkin.mood = +b.dataset.v;
      $$('#moods .mood').forEach((o) => o.setAttribute('aria-pressed', o === b));
    };
  });
}

/* ---------------------------------------------------- overlay focus handling
 *
 * The check-in and stuck sheets are modal dialogs. When one opens, focus moves
 * into it and Tab is trapped inside; when it closes, focus returns to whatever
 * had it before. Escape closes the stuck sheet, and — deliberately — dismisses
 * a check-in: the Intentional Dismiss is meant to be the zero-friction way out,
 * and a keyboard escape hatch is exactly that. Dismissing costs nothing by
 * design, so an accidental Escape is harmless. */
let _lastFocus = null;

function focusablesIn(root) {
  return [...root.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), ' +
    'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((el) => el.offsetParent !== null);
}

function openOverlay(el) {
  _lastFocus = document.activeElement;
  el.hidden = false;
  const first = focusablesIn(el)[0];
  if (first) requestAnimationFrame(() => first.focus());
}

function closeOverlay(el) {
  el.hidden = true;
  if (_lastFocus && document.contains(_lastFocus)) _lastFocus.focus();
  _lastFocus = null;
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (!$('#stuck').hidden) { closeOverlay($('#stuck')); return; }
    if (!$('#checkin').hidden) { sendCheckin(true); return; }
  }
  if (e.key !== 'Tab') return;
  const open = document.querySelector('.overlay:not([hidden])');
  if (!open) return;
  const f = focusablesIn(open);
  if (!f.length) return;
  const first = f[0];
  const last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

async function openCheckin() {
  if (!$('#checkin').hidden) return;
  const c = await api.get('/api/checkin');
  if (!c.due) return;

  state.checkin = { id: c.id, weight: c.weight, mood: null, water: 0 };
  $('#checkin-say').textContent = c.barnaby.text;
  $$('#checkin .ci-block').forEach((b) => {
    b.hidden = !b.dataset.weight.split(' ').includes(c.weight);
  });
  $('#water-count').textContent = '0';
  $('#ci-note').value = '';
  renderMoods();

  // A feather check-in asks for nothing at all, so the button stops
  // pretending there is something to submit.
  $('#ci-send').textContent = c.weight === 'feather' ? "I'm here" : 'Send';
  openOverlay($('#checkin'));
  window.Barnaby.setFace(c.barnaby.face);
}

async function sendCheckin(dismissed) {
  const payload = dismissed
    ? { dismissed: true }
    : {
        dismissed: false,
        mood: state.checkin.mood,
        water: state.checkin.water || null,
        note: $('#ci-note').value.trim() || null,
      };
  const r = await api.post('/api/checkin', payload);
  closeOverlay($('#checkin'));
  $('#day-say').textContent = r.barnaby.text;
  window.Barnaby.setFace(r.barnaby.face);
  window.Barnaby.still();
  renderRhythm(r.rhythm);
  await refreshDay();
}

/* ------------------------------------------------------------------ stuck */

function renderAnchors() {
  $('#anchors').innerHTML = ANCHORS.map(([id, title, sub]) => `
    <button class="anchor" data-a="${id}" aria-pressed="false">
      <strong>${title}</strong><em>${sub}</em>
    </button>`).join('');
  $$('#anchors .anchor').forEach((b) => {
    b.onclick = () => {
      state.stuckAnchor = b.dataset.a;
      $$('#anchors .anchor').forEach((o) => o.setAttribute('aria-pressed', o === b));
    };
  });
}

/* ------------------------------------------------------------------ window */

async function openWindow() {
  const data = await api.get('/api/window?days=7');
  show('window');
  requestAnimationFrame(() => window.renderSky($('#sky'), data.sky));

  $('#sky-name').textContent = data.sky.name;
  $('#sky-line').textContent = data.sky.line;

  $('#patterns').innerHTML = data.patterns.length
    ? data.patterns.map((p) => `
        <div class="pattern">
          <p>${escapeHtml(p.text)}</p>
          <p class="meta">${p.r !== undefined
              ? `correlation ${p.r} across ${p.n} days · ${p.confidence}`
              : 'timing pattern'}</p>
        </div>`).join('')
    : `<div class="pattern"><p>Nothing worth surfacing yet. Barnaby stays quiet
       until a pattern is actually there.</p></div>`;

  $('#detail').innerHTML = `
    <table>
      <thead><tr>
        <th>Day</th><th>Mood</th><th>Sleep</th><th>Water</th>
        <th>Check-ins</th><th>Waved off</th><th>Done</th>
      </tr></thead>
      <tbody>${data.sky.days.map((d) => `
        <tr>
          <td>${d.date ? new Date(d.date + 'T00:00:00')
                .toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
              : '—'}</td>
          <td>${d.detail.mood ?? '—'}</td>
          <td>${d.detail.sleep_hours ?? '—'}</td>
          <td>${d.detail.water || '—'}</td>
          <td>${d.detail.checkins || '—'}</td>
          <td>${d.detail.dismissed || '—'}</td>
          <td>${d.detail.acts_done || '—'}</td>
        </tr>`).join('')}</tbody>
    </table>`;
}

/* ------------------------------------------------------------------ curtain */

async function openCurtain() {
  const r = await api.post('/api/curtain');
  show('curtain');
  $('#curtain-lines').innerHTML = r.lines.map((l) =>
    `<li>${escapeHtml(l)}</li>`).join('');
  $('#curtain-say').textContent = r.barnaby.text;
  $('#star').hidden = false;
  window.Barnaby.celebrate();
}

/* ------------------------------------------------------------------ events */

function connectEvents() {
  const es = new EventSource('/api/events');

  // Sent on connect. Events only reach subscribers present when they were
  // published, so without this a tab that opens just after a check-in came
  // due would show a perfectly still Barnaby.
  es.addEventListener('sync', (e) => {
    const s = JSON.parse(e.data);
    window.Barnaby.setFace(s.expression);
    window.Barnaby.project(s.scene);
    // Silent: this is catching up on a jiggle that already started, not a new
    // one. The moment the bell marks has passed, and the shaking says it.
    if (s.jiggling) window.Barnaby.jiggle(0.6, { silent: true });
    else window.Barnaby.still();
  });

  es.addEventListener('jiggle', (e) => {
    const d = JSON.parse(e.data);
    window.Barnaby.jiggle(d.intensity);
    window.Barnaby.setFace('worried');
  });
  es.addEventListener('still',     () => window.Barnaby.still());
  es.addEventListener('pet',       () => { window.Barnaby.still();
                                           window.Barnaby.setFace('relieved');
                                           window.Bell.settle(); });
  es.addEventListener('face',      (e) => window.Barnaby.setFace(JSON.parse(e.data).expression));
  es.addEventListener('project',   (e) => window.Barnaby.project(JSON.parse(e.data).scene));
  es.addEventListener('celebrate', () => window.Barnaby.celebrate());
  es.onerror = () => {/* EventSource retries on its own */};
}

/* ------------------------------------------------------------------ util */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* -------------------------------------------------------------- demo panel
 * Filming aids, wired only when the server reports demo mode. Each button is
 * one beat of the video script: reset to the top, bring a check-in due, catch
 * the model live, jump to the bow. */
function setupDemo() {
  const panel = $('#demo-panel');
  panel.hidden = false;

  $('#demo-collapse').onclick = () => panel.classList.toggle('collapsed');

  $('#demo-reset').onclick = async () => {
    await api.post('/api/demo/reset');
    location.reload();
  };

  $('#demo-due').onclick = async () => {
    await api.post('/api/demo/due-now');
    if ($('#screen-day').hidden) { await refreshDay(); }
    openCheckin();
  };

  $('#demo-guard').onclick = async () => {
    const r = await api.post('/api/demo/guard-trip');
    const box = $('#demo-result');
    box.hidden = false;
    box.innerHTML = `
      <div>model tried:</div>
      <div class="att">${escapeHtml(r.attempted)}</div>
      <div>guard: <span class="rule">${r.rules.join(', ') || '—'}</span></div>
      <div>served instead:</div>
      <div class="srv">${escapeHtml(r.served)}</div>`;
  };

  $('#demo-curtain').onclick = () => openCurtain();
}

/* ------------------------------------------------------------------ boot */

async function boot() {
  window.Barnaby.mountAll();

  // Restore a remembered sound choice before anything can try to ring.
  syncSound(localStorage.getItem('gesture.mode') || 'circus');

  // Muting in one tab must mute every tab. People leave this open on a second
  // monitor — that is half the point of the rhythm — so a muted window being
  // rung by a forgotten one is precisely the failure this feature can't have.
  window.addEventListener('storage', (e) => {
    if (e.key === 'gesture.sound') syncSound();
  });

  // Audio can't start until the user has interacted with the page, so the
  // context is opened on the first gesture of any kind.
  const unlock = () => window.Bell.unlock();
  ['pointerdown', 'keydown'].forEach((e) =>
    window.addEventListener(e, unlock, { once: true, passive: true })
  );

  connectEvents();
  renderAnchors();

  // Petting is the core gesture. Every Barnaby on screen is a target.
  $$('[data-barnaby]').forEach((slot) => {
    slot.onclick = () => api.post('/api/barnaby/pet');
  });

  const s = await api.get('/api/state');
  state.catalogue = s.acts_catalogue;
  if (s.demo) setupDemo();

  if (state.mode) {
    applyMode(state.mode);
    $('#door').hidden = true;
    $('#begin-form').hidden = false;
  } else {
    applyMode('circus');            // paint something while they choose
    $('#door').hidden = false;
    $('#begin-form').hidden = true;
  }

  renderActKinds();
  renderCapacity();

  const g = await api.get('/api/greeting');
  $('#begin-say').textContent = g.text;

  if (s.day.began_at && !s.day.closed_at) {
    show('day');
    await refreshDay(g.text);
  } else {
    show('begin');
  }

  // Poll for a check-in coming due. Cheap, and it means the tab left open on
  // a second monitor still gets Barnaby's attention at the right moment.
  state.polling = setInterval(async () => {
    if (!$('#screen-day').hidden && $('#checkin').hidden) {
      const st = await api.get('/api/state');
      renderRhythm(st.rhythm);
      if (st.checkin_due) openCheckin();
    }
  }, 20000);
}

/* ------------------------------------------------------------------ wiring */

document.addEventListener('DOMContentLoaded', () => {
  // Escape closes an open dialog; Tab is trapped inside it.
  document.addEventListener('keydown', onKeydown);

  $$('.door-choice').forEach((b) => {
    b.onclick = () => {
      applyMode(b.dataset.mode);
      api.post(`/api/mode/${b.dataset.mode}`);
      $('#door').hidden = true;
      $('#begin-form').hidden = false;
      renderActKinds();
      renderCapacity();
    };
  });

  $('#capacity').oninput = renderCapacity;
  $('#act-add').onclick = addDraftAct;
  $('#act-title').onkeydown = (e) => { if (e.key === 'Enter') addDraftAct(); };

  $('#begin-go').onclick = async () => {
    const sleep = $('#sleep').value;
    const r = await api.post('/api/begin', {
      mode: state.mode,
      capacity: +$('#capacity').value,
      window_start: $('#win-start').value,
      window_end: $('#win-end').value,
      intention: $('#intention').value.trim() || null,
      sleep_hours: sleep ? +sleep : null,
      acts: state.draftActs,
    });
    // The overture. Fires here rather than on the greeting because audio
    // cannot start before a user gesture — and because this is the actual
    // moment the tent goes up.
    window.Bell.overture(state.mode);

    show('day');
    $('#day-say').textContent = r.barnaby.text;
    renderBalls(r.in_play, r.held);
    renderRhythm(r.rhythm);
  };

  $('#rhythm-toggle').onclick = (e) => {
    const open = e.currentTarget.getAttribute('aria-expanded') === 'true';
    e.currentTarget.setAttribute('aria-expanded', String(!open));
    $('#rhythm-body').hidden = open;
  };

  $('#ci-send').onclick = () => sendCheckin(false);
  $('#ci-dismiss').onclick = () => sendCheckin(true);
  $('#water').onclick = (e) => {
    if (!e.target.dataset.add) return;
    state.checkin.water += +e.target.dataset.add;
    $('#water-count').textContent = state.checkin.water;
  };

  $('#stuck-fab').onclick = () => {
    $('#stuck-say').hidden = true;
    openOverlay($('#stuck'));
  };
  $('#stuck-close').onclick = () => closeOverlay($('#stuck'));
  $('#stuck-send').onclick = async () => {
    if (!state.stuckAnchor) return;
    const r = await api.post('/api/stuck', {
      anchor: state.stuckAnchor,
      text: $('#stuck-text').value.trim() || null,
    });
    $('#stuck-say').textContent = r.text;
    $('#stuck-say').hidden = false;
    window.Barnaby.setFace(r.face);
    refreshDay();
  };

  $('#btn-window').onclick = openWindow;
  $('#window-back').onclick = () => show('day');
  $('#btn-curtain').onclick = openCurtain;
  $('#curtain-back').onclick = () => show('day');

  $('#detail-toggle').onclick = (e) => {
    const open = e.currentTarget.getAttribute('aria-expanded') === 'true';
    e.currentTarget.setAttribute('aria-expanded', String(!open));
    $('#detail').hidden = open;
    e.currentTarget.textContent = open
      ? 'Show the numbers underneath' : 'Hide the numbers';
  };

  $('#btn-pet').onclick = () => api.post('/api/barnaby/pet');
  $('#btn-nudge').onclick = () => api.post('/api/barnaby/nudge');

  $('#btn-sound').onclick = () => {
    window.Bell.setEnabled(!window.Bell.enabled);
    renderSoundToggle();
    // Play the gentler of the two so turning it on demonstrates itself at
    // the quietest thing it will ever do.
    if (window.Bell.enabled) setTimeout(() => window.Bell.settle(), 90);
  };

  window.addEventListener('resize', () => {
    if (!$('#screen-window').hidden) openWindow();
  });

  boot();
});

/* ══════════════════════════════════════════════════════════════════════
   FormCheck front end  (static/js/app.js)
   ══════════════════════════════════════════════════════════════════════
   WHAT THIS FILE DOES
   Opens the webcam, POSTs a small JPEG frame to your Flask route about 10×/second,
   and draws whatever JSON comes back (rep count, form score, tips, skeleton).
   It does NO pose maths – all MediaPipe work belongs in the backend.

   ─── THE ENTIRE BACKEND CONTRACT: ONE ROUTE ───────────────────────────

   POST /api/analyze            Content-Type: application/json

   Request body
     { "sid":      "k3j9x2fa",   // random id per page load – key your per-user rep state on this
       "exercise": "pushup",     // "pushup" | "squat" | "dip"
       "reset":    false,        // true on the first frame of a new set (or after switching
                                 //   exercise): zero the rep counter / phase state for this sid
       "image":    "/9j/4AAQ…" } // base64 JPEG, with NO "data:image/jpeg;base64," prefix

   Response body (JSON)
     { "reps": 4,                // running rep count for the current set
       "score": 87,              // 0–100 form rating right now; null = no person detected
       "phase": "down",          // optional – text on the video chip: "up" / "down" / "hold" …
       "tips": [ {"level":"warn", "text":"Hips are sagging"} ],   // level: "good" | "warn" | "bad"
       "landmarks": [ {"x":0.52,"y":0.31,"v":0.99}, … ],          // optional – 33 MediaPipe points
       "set_complete": false }   // optional – true ends the set now (otherwise it ends at the goal)

   Minimal Flask side (fill in the TODO with your angle / rep / scoring logic):

     @app.route("/api/analyze", methods=["POST"])
     def analyze():
         d = request.get_json()
         img = cv2.imdecode(np.frombuffer(base64.b64decode(d["image"]), np.uint8), cv2.IMREAD_COLOR)
         res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))      # pose = mp.solutions.pose.Pose()
         lm = res.pose_landmarks.landmark if res.pose_landmarks else None
         # TODO: if d["reset"]: zero the state stored for d["sid"]; then update reps, phase, score, tips
         return jsonify(reps=reps, score=score, phase=phase, tips=tips,
                        landmarks=[{"x": p.x, "y": p.y, "v": p.visibility} for p in lm] if lm else [])

   NOTES FOR WHOEVER WIRES UP THE BACKEND
   • No person in frame? Return score=null and a tip such as {"level":"warn","text":"Step back so your whole body is visible"}.
   • Landmarks: send MediaPipe's x/y exactly as returned (normalised 0–1 on the un-mirrored frame we upload).
     The canvas is mirrored with CSS to match the selfie-style video, so do NOT flip them yourself.
   • Only one request is in flight at a time, so a slow backend lowers the frame rate instead of piling up requests.
   • Browsers only allow camera access on https:// or http://localhost (127.0.0.1) – not on a plain LAN IP.
   • With no backend reachable the page falls back to simulated data (CONFIG.DEMO_FALLBACK) so the UI still
     previews; add ?demo to the URL to force it. Set DEMO_FALLBACK to false once the real backend is live.
   • Example gifs are served from static/gifs/ (see EX below). Missing files just show a placeholder.
   ══════════════════════════════════════════════════════════════════════ */

/* ── 1. CONFIG  ◆ start here ─────────────────────────────────────────── */
const CONFIG = {
  API_URL: '/api/analyze',  // ◆ change if your route is named differently
  FPS: 10,                  // maximum frames sent per second
  FRAME_WIDTH: 480,         // frames are downscaled to this width before upload (smaller = faster)
  JPEG_QUALITY: 0.6,        // 0–1
  DEMO_FALLBACK: true       // show fake data if the backend can't be reached
};

/* ── 2. EXERCISES ────────────────────────────────────────────────────────
   Keys ("pushup", "squat", "dip") are exactly what the backend receives as "exercise".
   To add an exercise: add an entry here and handle its key in your backend. */
const EX = {
  pushup: { name: 'Push-ups',   gif: '/static/gifs/pushup.gif',    cam: 'Place the camera low and side-on so your whole body is in frame.',
            cues: ['Straight line from head to heels', 'Elbows about 45° from your torso', 'Chest to fist height, then full lockout'] },
  squat:  { name: 'Squats',     gif: '/static/gifs/squat.gif',     cam: 'Place the camera at hip height, side-on, 6–8 ft away.',
            cues: ['Feet shoulder-width, chest tall', 'Knees track over your toes', 'Hips below knees, heels grounded'] },
  dip:    { name: 'Chair dips', gif: '/static/gifs/chair-dip.gif', cam: 'Place the camera side-on so your arms, hips and chair are visible.',
            cues: ['Hands on the edge, fingers forward', 'Keep your back close to the chair', 'Lower to a 90° elbow bend, shoulders down'] }
};

/* ── State + tiny helpers (nothing to change here) ───────────────────── */
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = s => s < 60 ? s : Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
const SID = Math.random().toString(36).slice(2, 10);   // sent as "sid" with every request
const S = { ex: 'pushup', state: 'idle',               // state: idle → active → rest → active …
  reps: 0, target: 10, set: 1, rest: 60, left: 0, score: null, shown: 0, phase: '', tips: '',
  stream: null, camId: '', loop: 0, linked: false, fails: 0, needReset: true, gen: 0, demo: null, timer: null };
try { S.camId = localStorage.camId || ''; } catch (e) {}   // remember the last-used camera
const video = $('#video'), overlay = $('#overlay'), grab = document.createElement('canvas'), gctx = grab.getContext('2d');
/* New set / new exercise: zero the UI counter and tell the backend to zero its own on the next frame.
   S.gen lets us ignore replies to frames that were already in flight before the reset. */
const resetCounter = () => { S.reps = 0; S.gen++; S.needReset = true; };

/* ── 3. CAMERA + CAMERA PICKER ───────────────────────────────────────── */
async function startCamera() {
  if (S.stream) S.stream.getTracks().forEach(t => t.stop());   // switching devices: release the old one first
  const size = { width: { ideal: 1280 }, height: { ideal: 720 } };
  const ask = id => navigator.mediaDevices.getUserMedia({ audio: false, video: id ? { ...size, deviceId: { exact: id } } : { ...size, facingMode: 'user' } });
  try {
    try { S.stream = await ask(S.camId); }
    catch (e) { if (!S.camId) throw e; S.camId = ''; S.stream = await ask(''); }   // saved webcam unplugged → default camera
    video.srcObject = S.stream; await video.play(); $('#ph').hidden = true;
    S.camId = S.stream.getVideoTracks()[0].getSettings().deviceId || '';
    try { localStorage.camId = S.camId; } catch (e) {}
    listCameras(); return true;
  } catch (err) {
    S.stream = null;
    $('#phTitle').textContent = 'Camera unavailable';
    $('#camHint').textContent = 'Allow camera access in your browser. The page must be on https:// or localhost.';
    return false;
  }
}
/* Device names are blank until the user has granted permission, so this runs after the first successful start
   and again whenever a webcam is plugged in or removed. */
async function listCameras() {
  const cams = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput'), sel = $('#camSel');
  sel.innerHTML = cams.map((d, i) => `<option value="${esc(d.deviceId)}">${esc(d.label || 'Camera ' + (i + 1))}</option>`).join('') || '<option value="">Default camera</option>';
  sel.value = S.camId;
}
$('#camSel').onchange = e => { S.camId = e.target.value; if (S.stream) startCamera(); };   // switch live; otherwise used on next Start
if (navigator.mediaDevices) navigator.mediaDevices.addEventListener('devicechange', listCameras);

/* ── 4. SENDING FRAMES TO THE BACKEND  ◆ INTEGRATION POINT ──────────────
   tick() grabs a frame, POSTs it to CONFIG.API_URL, waits for the reply, applies it, then schedules itself again. */
function startBackend() {
  if (new URLSearchParams(location.search).has('demo')) return startDemo();
  setStatus('connecting'); S.linked = false; S.fails = 0; tick(++S.loop);
}
async function tick(id) {
  if (id !== S.loop) return;                                  // loop was stopped or restarted
  if (!video.videoWidth) return setTimeout(() => tick(id), 100);   // camera still warming up
  const t0 = performance.now(), gen = S.gen, reset = S.needReset;
  S.needReset = false;                                        // put back below if this request fails
  grab.width = CONFIG.FRAME_WIDTH; grab.height = Math.round(video.videoHeight * CONFIG.FRAME_WIDTH / video.videoWidth);
  gctx.drawImage(video, 0, 0, grab.width, grab.height);       // raw, un-mirrored frame
  const image = grab.toDataURL('image/jpeg', CONFIG.JPEG_QUALITY).split(',')[1];   // strip the "data:…;base64," prefix
  try {
    const r = await fetch(CONFIG.API_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sid: SID, exercise: S.ex, reset, image }) });           // ◆ the request
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();                                                     // ◆ the response
    if (id !== S.loop) return;
    S.linked = true; S.fails = 0; setStatus('live');
    if (gen !== S.gen) { delete data.reps; delete data.set_complete; }   // reply to a pre-reset frame: ignore its rep count
    onFeedback(data);
  } catch (err) {
    console.warn('FormCheck: backend request failed –', err);
    if (reset) S.needReset = true;
    if (!S.linked && CONFIG.DEMO_FALLBACK) { S.loop++; return startDemo(); }   // never reached the backend
    if (++S.fails >= 3) setStatus('offline');                                  // keeps retrying in the background
  }
  setTimeout(() => tick(id), Math.max(0, 1000 / CONFIG.FPS - (performance.now() - t0)));
}

/* ── 5. APPLYING THE RESPONSE  ◆ INTEGRATION POINT ───────────────────────
   Every field of the backend JSON is consumed here. If your keys are named differently, rename them in this one function. */
function onFeedback(m) {
  if (typeof m.score === 'number') S.score = Math.max(0, Math.min(100, m.score));   // score     → ring + label
  else if (m.score === null) S.score = null;                                        // null      → "Waiting for pose"
  if (m.phase !== undefined) S.phase = m.phase;                                     // phase     → chip on the video
  renderTips(m.tips || []);                                                         // tips      → list + pill on the video
  draw(m.landmarks);                                                                // landmarks → skeleton overlay
  if (S.state === 'active') {
    if (typeof m.reps === 'number' && m.reps !== S.reps) {                          // reps      → big counter
      S.reps = m.reps; const b = $('#big'); b.classList.remove('bump'); void b.offsetWidth; b.classList.add('bump');
    }
    if (S.reps >= S.target || m.set_complete) finishSet();                          // goal reached → rest timer starts
  }
  render();
}
function renderTips(t) {
  const k = JSON.stringify(t); if (k === S.tips) return; S.tips = k;                // skip if nothing changed
  $('#tips').innerHTML = t.length ? t.slice(0, 4).map(x => `<li class="${esc(x.level || 'good')}">${esc(x.text)}</li>`).join('') : '<li class="empty">Start a set and your coaching tips will appear here.</li>';
  const top = t.find(x => x.level === 'bad') || t.find(x => x.level === 'warn') || t[0], l = $('#live');   // worst tip goes on the video
  l.textContent = top ? top.text : ''; l.className = 'live' + (top ? ' on ' + (top.level || 'good') : '');
}
/* Skeleton: pairs of MediaPipe Pose landmark indices (shoulders, arms, torso, legs). Points under 0.4 visibility are skipped. */
const PAIRS = [[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
function draw(lm) {
  const c = overlay, x = c.getContext('2d');
  if (video.videoWidth && c.width !== video.videoWidth) { c.width = video.videoWidth; c.height = video.videoHeight; }
  x.clearRect(0, 0, c.width, c.height);
  if (!lm || !lm.length) return;
  const P = i => lm[i] && (lm[i].v == null || lm[i].v > .4) ? [lm[i].x * c.width, lm[i].y * c.height] : null;
  x.lineWidth = Math.max(3, c.width / 220); x.lineCap = 'round'; x.strokeStyle = 'rgba(255,255,255,.92)'; x.fillStyle = '#8f9bff';
  PAIRS.forEach(([a, b]) => { const p = P(a), q = P(b); if (p && q) { x.beginPath(); x.moveTo(p[0], p[1]); x.lineTo(q[0], q[1]); x.stroke(); } });
  new Set(PAIRS.flat()).forEach(i => { const p = P(i); if (p) { x.beginPath(); x.arc(p[0], p[1], x.lineWidth * 1.3, 0, 6.3); x.fill(); } });
}

/* ── 6. SET FLOW (UI only – no backend work needed) ──────────────────────
   idle ──Start set──▶ active ──goal reached / Finish set──▶ rest (countdown) ──timer ends / Skip──▶ active (next set) */
function finishSet() {
  if (S.state !== 'active') return;
  S.state = 'rest'; S.left = S.rest; clearInterval(S.timer);
  S.timer = setInterval(() => { if (--S.left <= 0) nextSet(); else render(); }, 1000);
  render();
}
function nextSet() { clearInterval(S.timer); S.set++; S.state = 'active'; resetCounter(); render(); }
function stopAll() {
  if (S.stream) S.stream.getTracks().forEach(t => t.stop());
  S.stream = null; video.srcObject = null; $('#ph').hidden = false;
  S.loop++; clearInterval(S.timer); clearInterval(S.demo); S.demo = null;        // stops the frame loop + demo
  Object.assign(S, { state: 'idle', reps: 0, set: 1, score: null, phase: '' });
  $('#phTitle').textContent = 'Camera is off'; $('#camHint').textContent = EX[S.ex].cam;
  renderTips([]); draw(null); setStatus('offline'); render();
}
function selectEx(k) {
  const e = EX[k]; S.ex = k; S.score = null;
  if (S.state === 'rest') { clearInterval(S.timer); S.state = 'active'; }
  document.querySelectorAll('.tab').forEach(b => { const on = b.dataset.ex === k; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
  $('#gifFig').classList.remove('m'); $('#gif').src = e.gif; $('#gifName').textContent = e.gif;
  $('#cues').innerHTML = e.cues.map(c => `<li>${c}</li>`).join('');
  if (!S.stream) $('#camHint').textContent = e.cam;
  resetCounter(); renderTips([]); render();                                       // backend is told via reset:true on the next frame
}
$('#tabs').innerHTML = Object.entries(EX).map(([k, e]) => `<button class="tab" data-ex="${k}" aria-pressed="false">${e.name}</button>`).join('');
$('#tabs').onclick = e => { const b = e.target.closest('.tab'); if (b) selectEx(b.dataset.ex); };
$('#go').onclick = async () => {                                                  // Start set / Finish set / Skip rest
  if (S.state === 'idle') { if (!await startCamera()) return; resetCounter(); S.state = 'active'; startBackend(); render(); }
  else if (S.state === 'active') finishSet();
  else nextSet();
};
$('#stop').onclick = stopAll;
document.querySelectorAll('[data-d]').forEach(b => b.onclick = () => { S.target = Math.max(1, Math.min(50, S.target + +b.dataset.d)); render(); });
$('#restSel').onchange = e => { S.rest = +e.target.value; };

/* ── 7. RENDERING (UI only) ──────────────────────────────────────────── */
function setStatus(s) { const el = $('#status'); el.className = 'status ' + s; el.querySelector('span').textContent = { offline: 'Offline', connecting: 'Connecting…', live: 'Backend connected', demo: 'Demo mode' }[s]; }
function render() {
  const rest = S.state === 'rest';
  $('#counter').classList.toggle('rest', rest);                                   // card turns dark while resting
  $('#lab').textContent = rest ? 'Rest' : 'Reps';
  $('#setPill').textContent = rest ? `Set ${S.set} done` : `Set ${S.set}`;
  $('#big').textContent = rest ? fmt(S.left) : S.reps;                            // big number: reps, or rest countdown
  $('#sub').textContent = rest ? 'Next set starts automatically' : `of ${S.target} reps`;
  $('#fill').style.width = (rest ? S.left / S.rest : Math.min(1, S.reps / S.target)) * 100 + '%';
  $('#go').textContent = { idle: 'Start set', active: 'Finish set', rest: 'Skip rest' }[S.state];
  $('#stop').hidden = S.state === 'idle';
  $('#target').textContent = S.target;
  $('#chip').textContent = rest ? 'Resting' : S.state === 'idle' ? 'Ready' : (S.phase ? S.phase[0].toUpperCase() + S.phase.slice(1) : 'Tracking');
}
const ringV = $('#ringV'), sn = $('#scoreNum'), sl = $('#scoreLab'), sc = $('#score');
(function loop() {                                                                // eases the score ring/number toward the latest value
  const has = S.score !== null; S.shown += ((has ? S.score : 0) - S.shown) * .18;
  const v = Math.round(S.shown);
  ringV.style.strokeDashoffset = 326.7 * (1 - S.shown / 100);
  sn.textContent = has ? v : '—';
  sc.style.setProperty('--sc', !has ? 'var(--mu)' : v >= 80 ? 'var(--good)' : v >= 60 ? 'var(--warn)' : 'var(--bad)');
  sl.textContent = !has ? 'Waiting for pose' : v >= 90 ? 'Excellent' : v >= 80 ? 'Good form' : v >= 60 ? 'Needs work' : 'Poor form';
  requestAnimationFrame(loop);
})();

/* ── 8. DEMO MODE: simulated feedback so the UI can be previewed without a backend (safe to delete later) ── */
const DEMO = {
  pushup: [['good', 'Body is in a straight line'], ['warn', 'Hips are sagging, squeeze your glutes'], ['warn', 'Elbows flaring, tuck them to about 45°'], ['good', 'Great depth, chest nearly to the floor']],
  squat:  [['good', 'Solid depth, hips below knees'], ['warn', 'Knees caving in, push them out'], ['warn', 'Chest dropping, stay tall'], ['good', 'Heels planted, nice control']],
  dip:    [['good', 'Elbows tracking straight back'], ['warn', 'Go lower, aim for a 90° elbow bend'], ['bad', 'Shoulders shrugging, pull them down'], ['good', 'Back stays close to the chair']]
};
function startDemo() {
  if (S.demo) return; setStatus('demo'); let t = 0;
  S.demo = setInterval(() => {
    t++; const L = DEMO[S.ex], i = Math.floor(t / 30), a = L[i % L.length], b = L[(i + 1) % L.length];
    onFeedback({ score: Math.round(72 + 18 * Math.sin(t / 40) + (Math.random() - .5) * 4), phase: t % 24 < 12 ? 'down' : 'up',
      reps: S.reps + (t % 24 === 0 && S.state === 'active' ? 1 : 0), tips: [{ level: a[0], text: a[1] }, { level: b[0], text: b[1] }] });
  }, 100);
}

/* ── 9. INIT ─────────────────────────────────────────────────────────── */
selectEx('pushup'); setStatus('offline');

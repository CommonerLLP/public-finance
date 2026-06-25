/* LMMHA public browser. Vanilla JS, no build step.
   Loads viz/lmmha_browser.json and renders:
     - account-class navigation -> drill Major -> Sub-Major -> Minor
     - per-code detail with scope notes + correction-slip history
     - subject lookup: one topic (e.g. "public libraries") across all account classes
     - a change-over-time timeline (2012-2026)
   Deep-linkable: #code/4202-04-105 , #subject/library */

const state = {
  data: null,
  byCode: new Map(),
  childrenOf: new Map(),     // parent code -> [node]
  classOf: new Map(),        // class key -> class def
  observed: {},              // code -> { state, unit, series:[{fy,be}] }
  observedMeta: null,
  tab: "browse",
};

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));

/* normalise for search: lowercase, punctuation -> space, collapse.
   so "Mid-day Meals", "mid day meal", "middaymeal" all reconcile. */
const norm = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const tokens = (s) => norm(s).split(" ").filter(Boolean);

init();

async function init() {
  const data = await (await fetch("lmmha_browser.json")).json();
  state.data = data;

  // observed state-reporting layer (optional; degrade gracefully if absent)
  try {
    const obs = await (await fetch("observed.json")).json();
    state.observed = obs.observed || {};
    state.observedMeta = obs.meta || null;
  } catch (e) { /* no observed layer — browser still works */ }

  for (const n of data.nodes) {
    n._s = norm(n.c + " " + n.d);   // precomputed search string
    state.byCode.set(n.c, n);
    if (n.p) {
      if (!state.childrenOf.has(n.p)) state.childrenOf.set(n.p, []);
      state.childrenOf.get(n.p).push(n);
    }
  }
  // codes that carry scope notes
  for (const code of Object.keys(data.notes)) {
    const n = state.byCode.get(code);
    if (n) n._note = true;
  }
  for (const c of data.classes) state.classOf.set(c.key, c);

  renderMasthead();
  renderClassGrid();
  bindSearch();
  bindTabs();
  bindAnchorNav();

  if (!routeFromHash()) {
    showDetailEmpty();
  }
  window.addEventListener("hashchange", routeFromHash);
}

/* ---------------- masthead ---------------- */
function renderMasthead() {
  const m = state.data.meta, c = m.counts;
  $("#counts").innerHTML =
    `<strong>${c.total.toLocaleString()}</strong> heads of account &nbsp;·&nbsp; ` +
    `${c.major} major &nbsp;·&nbsp; ${c.sub_major} sub-major &nbsp;·&nbsp; ${c.minor.toLocaleString()} minor ` +
    `&nbsp;·&nbsp; <strong>${c.notes.toLocaleString()}</strong> scope notes &nbsp;·&nbsp; ` +
    `<strong>${c.events}</strong> correction-slip changes (2012–2026)`;
}

/* ---------------- account-class navigation ---------------- */
function renderClassGrid() {
  const grid = $("#class-grid");
  const counts = {};
  for (const n of state.data.nodes) {
    if (n.t === "Major Head") counts[n.k] = (counts[n.k] || 0) + 1;
  }
  grid.innerHTML = state.data.classes.map((c) => `
    <div class="class-card" style="--cls:var(--c${c.key})" data-class="${c.key}">
      <span class="count">${counts[c.key] || 0} major heads</span>
      <span class="digits">first digit ${esc(c.digits)}</span>
      <h3>${esc(c.name)}</h3>
      <p>${esc(c.summary)}</p>
    </div>`).join("");
  grid.querySelectorAll(".class-card").forEach((el) =>
    el.addEventListener("click", () => openClass(el.dataset.class)));
}

function openClass(key) {
  setTab("browse");
  $("#class-grid").querySelectorAll(".class-card").forEach((e) =>
    e.classList.toggle("active", e.dataset.class === key));
  const cls = state.classOf.get(key);
  const majors = state.data.nodes
    .filter((n) => n.t === "Major Head" && n.k === key)
    .sort((a, b) => a.c.localeCompare(b.c));
  $("#tree").innerHTML =
    `<div class="crumbs"><a id="crumb-home">All account classes</a><span class="sep">›</span>` +
    `<span style="color:var(--c${key});font-weight:600">${esc(cls.name)}</span></div>` +
    `<div class="class-explain" style="margin:12px 16px">${esc(cls.detail)}</div>` +
    `<div class="tree">${majors.map(rowHTML).join("")}</div>`;
  $("#crumb-home").onclick = () => { $("#tree").innerHTML = ""; $("#class-grid").querySelectorAll(".class-card").forEach((e) => e.classList.remove("active")); };
  bindRows($("#tree"));
}

function rowHTML(n) {
  const kids = state.childrenOf.get(n.c);
  const chev = kids && kids.length ? `<span class="chev">›</span>` : "";
  const tag = n.t === "Major Head" ? "major" : n.t === "Sub-Major Head" ? "sub-major" : "minor";
  return `<div class="row ${n._note ? "has-note" : ""}" data-code="${esc(n.c)}">
      <span class="code">${esc(n.c)}</span>
      <span class="desc">${esc(n.d)}</span>
      <span class="tag">${tag}</span>${chev}
    </div>`;
}

function bindRows(scope) {
  scope.querySelectorAll(".row").forEach((el) =>
    el.addEventListener("click", () => location.hash = "code/" + el.dataset.code));
}

/* ---------------- detail view ---------------- */
function showCode(code) {
  setTab("browse");
  const n = state.byCode.get(code);
  if (!n) { showDetailEmpty(`No head with code ${esc(code)}.`); return; }

  // sync the navigator to this code's class + major head
  syncNavTo(n);

  const cls = state.classOf.get(n.k);
  const chain = ancestry(n);          // [major, submajor?, this] top-down
  const kids = (state.childrenOf.get(n.c) || []).slice().sort((a, b) => a.c.localeCompare(b.c));
  const notes = state.data.notes[n.c] || [];
  const events = historyFor(n);

  const breadcrumb = chain.map((x) => {
    const cur = x.c === n.c ? "cur" : "";
    return `<span class="step ${cur}" data-code="${esc(x.c)}" style="--cls:var(--c${n.k})">
        <span class="c">${esc(x.c)}</span>${esc(x.d)}</span>`;
  }).join("");

  let html = `
    <span class="d-class-pill" style="--cls:var(--c${n.k})">${esc(cls.name)}</span>
    <div class="d-code">${esc(n.c)}</div>
    <div class="d-type">${esc(n.t)}</div>
    <div class="d-desc">${esc(n.d)}</div>
    <div class="d-breadcrumb">${breadcrumb}</div>
    <div class="d-section">
      <h4>What this class records</h4>
      <div class="class-explain">${esc(cls.detail)}</div>
    </div>`;

  html += observedHTML(n);

  if (notes.length) {
    html += `<div class="d-section"><h4>Scope notes — what governments should book here</h4>` +
      notes.map((nt) => `<div class="note"><span class="num">Note ${esc(nt.num)}.</span> ${esc(nt.text)}</div>`).join("") +
      `</div>`;
  }

  if (kids.length) {
    html += `<div class="d-section"><h4>${kids.length} head${kids.length > 1 ? "s" : ""} under this one</h4>` +
      `<div class="children-list">${kids.map(rowHTML).join("")}</div></div>`;
  }

  // sibling subjects: same description in OTHER account classes (the cross-cutting story)
  const siblings = state.data.nodes.filter((x) =>
    x.c !== n.c && x.d.toLowerCase() === n.d.toLowerCase() && x.k !== n.k);
  if (siblings.length) {
    html += `<div class="d-section"><h4>The same subject in other account classes</h4>
      <p style="font-size:13px;color:var(--ink-soft);margin:0 0 8px">
      "${esc(n.d)}" is also reported elsewhere in the chart of accounts. To see the full picture of this
      function you must read across all of these:</p>
      <div class="children-list">${siblings.map(rowHTML).join("")}</div></div>`;
  }

  html += historyHTML(events, n);
  $("#detail").innerHTML = html;
  $("#detail").scrollTop = 0;
  bindRows($("#detail"));
  $("#detail").querySelectorAll(".step").forEach((el) =>
    el.addEventListener("click", () => location.hash = "code/" + el.dataset.code));
}

/* observed state reporting: real budgeted amounts booked under this exact code */
function observedHTML(n) {
  const o = state.observed[n.c];
  if (!o || !o.series || !o.series.length) return "";
  const max = Math.max(...o.series.map((p) => p.be));
  const fmtCr = (lakh) => (lakh / 100).toLocaleString("en-IN", { maximumFractionDigits: 1 });
  const bars = o.series.map((p) => `
    <div class="ob-col" title="${esc(p.fy)}: ₹${fmtCr(p.be)} cr">
      <span class="ob-val">${fmtCr(p.be)}</span>
      <div class="ob-bar" style="height:${Math.max(2, Math.round((p.be / max) * 90))}px"></div>
      <span class="ob-fy">${esc(p.fy)}</span>
    </div>`).join("");
  const src = state.observedMeta ? state.observedMeta.source : "";
  return `<div class="d-section">
    <h4>Observed reporting — what a government actually booked here</h4>
    <p style="font-size:13px;color:var(--ink-soft);margin:0 0 4px">
      <strong>${esc(o.state)}</strong> budgeted under this exact head, in ₹ crore (Budget Estimate):</p>
    <div class="ob-bars">${bars}</div>
    <p class="caveat">Source: ${esc(src)}. Single-source — illustrative, not yet cross-checked against
      RBI State Finances. This is the "observed" layer: how one government used the code, separate from the
      normative list above.</p>
  </div>`;
}

function ancestry(n) {
  const chain = [n];
  let cur = n;
  while (cur.p && state.byCode.has(cur.p)) {
    cur = state.byCode.get(cur.p);
    chain.unshift(cur);
  }
  return chain;
}

/* Correction-slip events touching this head's major head (reliable join);
   flag the lines whose flattened (major-minor) key matches this exact minor. */
function historyFor(n) {
  const out = [];
  const myFlat = n.mn ? `${n.mh}-${n.mn}` : null;
  for (const ev of state.data.events) {
    if (!ev.majors.includes(n.mh)) continue;
    const rel = ev.changes.filter((ch) => ch.mh === n.mh);
    out.push({ ev, rel, exact: myFlat ? rel.some((ch) => ch.code === myFlat) : false });
  }
  return out;
}

function historyHTML(events, n) {
  if (!events.length) {
    return `<div class="d-section"><h4>Changes over time</h4>
      <p style="font-size:13px;color:var(--ink-faint)">No correction slip in the 2012–2026 ledger
      touched major head ${esc(n.mh)}.</p></div>`;
  }
  const cards = events.map(({ ev, rel, exact }) => `
    <div class="event">
      <div class="ev-head"><span class="ev-slip">${esc(ev.slip)}</span><span class="ev-date">${esc(ev.date)}</span></div>
      <div class="ev-changes">${rel.map((ch) => chgHTML(ch, n)).join("")}</div>
    </div>`).join("");
  return `<div class="d-section">
    <h4>Changes over time — correction slips touching major head ${esc(n.mh)}</h4>
    ${cards}
    <p class="caveat">Correction-slip records use the older flattened code form (major-minor), so they are
    matched to this head by its major head ${esc(n.mh)}; lines highlighted below match this exact minor head.</p>
  </div>`;
}

function chgHTML(ch, n) {
  const act = (ch.action || "").toLowerCase();
  const isMatch = n.mn && ch.code === `${n.mh}-${n.mn}`;
  const old = ch.action === "RENAME" && ch.old_label ? `<span class="old">${esc(ch.old_label)}</span> → ` : "";
  return `<div class="chg ${isMatch ? "match" : ""}">
      <span class="act ${act}">${esc(ch.action)}</span>
      <span class="ccode">${esc(ch.code)}</span>
      <span>${old}${esc(ch.label)}</span>
    </div>`;
}

function syncNavTo(n) {
  $("#class-grid").querySelectorAll(".class-card").forEach((e) =>
    e.classList.toggle("active", e.dataset.class === n.k));
  // only re-render the tree if it isn't already showing this class
  const cur = $("#tree .crumbs span[style*='font-weight']");
  if (!cur) openClass(n.k);
  $("#tree").querySelectorAll(".row").forEach((el) =>
    el.classList.toggle("selected", el.dataset.code === n.c));
}

function showDetailEmpty(msg) {
  $("#detail").innerHTML = `<div class="detail-empty">
    <h2>${msg ? esc(msg) : "Pick an account class, or search for a subject"}</h2>
    <p>The LMMHA is the master list the Government of India uses to classify every rupee it
    receives and spends. Choose one of the five account classes on the left to browse it, or
    search a subject like <a href="#subject/public libraries">public libraries</a>,
    <a href="#subject/mid day meal">mid day meal</a>, or
    <a href="#subject/drinking water">drinking water</a> to see every head it is reported under.</p>
  </div>`;
}

/* ---------------- subject lookup ---------------- */
function bindSearch() {
  const input = $("#search");
  let t;
  input.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      const q = input.value.trim();
      if (q.length < 2) return;
      location.hash = "subject/" + q;
    }, 220);
  });
}

function showSubject(q) {
  setTab("browse");
  $("#search").value = q;
  const qt = tokens(q);
  // every query token must appear in the node's normalised text (order-independent)
  const hits = qt.length
    ? state.data.nodes.filter((n) => qt.every((t) => n._s.includes(t)))
    : [];

  if (!hits.length) {
    $("#detail").innerHTML = `<div class="detail-empty"><h2>Nothing matches “${esc(q)}”.</h2>
      <p>Try a broader word — “library”, “water”, “school”, “hospital”.</p></div>`;
    return;
  }

  // group by account class, ordered as receipts → revenue → capital → debt → public account
  const order = ["0", "2", "4", "6", "8"];
  const groups = {};
  for (const n of hits) (groups[n.k] = groups[n.k] || []).push(n);

  const classesHit = order.filter((k) => groups[k]);
  let summary = "";
  if (classesHit.length > 1) {
    summary = `<div class="class-explain" style="margin-bottom:18px">
      <strong>“${esc(q)}”</strong> is reported across <strong>${classesHit.length} account classes</strong>.
      To understand the full fiscal picture of this function you have to read across all of them — money
      received, money spent on running it, money spent building it, and loans given for it are recorded
      under separate heads by design.</div>`;
  }

  const sections = classesHit.map((k) => {
    const cls = state.classOf.get(k);
    const rows = groups[k].sort((a, b) => a.c.localeCompare(b.c)).map(rowHTML).join("");
    return `<div class="d-section">
      <h4><span class="d-class-pill" style="--cls:var(--c${k})">${esc(cls.name)}</span>
        &nbsp;${groups[k].length} head${groups[k].length > 1 ? "s" : ""}</h4>
      <div class="children-list">${rows}</div></div>`;
  }).join("");

  $("#detail").innerHTML = `<div class="d-desc" style="margin-bottom:6px">Subject: “${esc(q)}”</div>
    <p style="color:var(--ink-soft);font-size:13.5px;margin-top:0">${hits.length} matching head${hits.length > 1 ? "s" : ""} in the chart of accounts.</p>
    ${summary}${sections}`;
  $("#detail").scrollTop = 0;
  bindRows($("#detail"));
}

/* ---------------- timeline tab ---------------- */
function renderTimeline() {
  const ev = state.data.events;
  const byYear = {};
  for (const e of ev) {
    const y = (e.date || "").slice(0, 4);
    (byYear[y] = byYear[y] || []).push(e);
  }
  const years = Object.keys(byYear).sort();
  const max = Math.max(...years.map((y) => byYear[y].length));
  const bars = years.map((y) => `
    <div class="year-bar" data-year="${y}">
      <span class="n">${byYear[y].length}</span>
      <div class="bar" style="height:${Math.round((byYear[y].length / max) * 100)}px"></div>
      <span class="yr">${y}</span>
    </div>`).join("");

  $("#timeline-view").innerHTML = `<div class="timeline-wrap">
    <h2 style="margin:0 0 4px">How the chart of accounts has changed</h2>
    <p class="tl-intro">Each year the CGA issues <em>correction slips</em> that add, rename or remove heads of
      account. They are the audit trail of how the state's reporting categories evolve — a new minor head for a
      new scheme, a renamed programme, a deleted obsolete head.</p>
    <p class="tl-coverage">${esc(state.data.meta.timeline_coverage)}</p>
    <div class="year-bars">${bars}</div>
    <div id="year-events"></div>
  </div>`;
  $("#timeline-view").querySelectorAll(".year-bar").forEach((el) =>
    el.addEventListener("click", () => {
      $("#timeline-view").querySelectorAll(".year-bar").forEach((b) => b.classList.remove("active"));
      el.classList.add("active");
      showYearEvents(el.dataset.year, byYear[el.dataset.year]);
    }));
}

function showYearEvents(year, events) {
  $("#year-events").innerHTML = `<h3 style="margin:6px 0 12px">${year} — ${events.length} correction slip${events.length > 1 ? "s" : ""}</h3>` +
    events.map((ev) => `
      <div class="event">
        <div class="ev-head"><span class="ev-slip">${esc(ev.slip)}</span><span class="ev-date">${esc(ev.date)}</span></div>
        <div class="ev-changes">${ev.changes.map((ch) => chgHTML(ch, {})).join("")}</div>
      </div>`).join("");
}

/* ---------------- in-page jump nav + back-to-top ---------------- */
function bindAnchorNav() {
  // jump nav writes a shareable hash (#about/<section>); routeFromHash does the scroll
  document.querySelectorAll(".toc button[data-target]").forEach((b) =>
    b.addEventListener("click", () => {
      location.hash = "about/" + b.dataset.target.replace(/^a-/, "");
    }));
  const top = $("#to-top");
  if (top) {
    top.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    window.addEventListener("scroll", () => top.classList.toggle("show", window.scrollY > 500));
  }
}

/* ---------------- tabs + routing ---------------- */
function bindTabs() {
  // both the header tab buttons and any [data-tab] link (e.g. footer "methodology")
  document.querySelectorAll("[data-tab]").forEach((el) =>
    el.addEventListener("click", (e) => { e.preventDefault(); setTab(el.dataset.tab); }));
}
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((e) => e.classList.toggle("active", e.dataset.tab === tab));
  $("#browse-view").classList.toggle("hidden", tab !== "browse");
  $("#timeline-view").classList.toggle("hidden", tab !== "timeline");
  $("#about-view").classList.toggle("hidden", tab !== "about");
  $(".searchbar").classList.toggle("hidden", tab !== "browse");
  if (tab === "timeline" && !$("#timeline-view").innerHTML.trim()) renderTimeline();
  if (tab === "about") window.scrollTo(0, 0);
}

function routeFromHash() {
  const h = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (h.startsWith("code/")) { showCode(h.slice(5)); return true; }
  if (h.startsWith("subject/")) { showSubject(h.slice(8)); return true; }
  if (h === "timeline") { setTab("timeline"); return true; }
  if (h === "about") { setTab("about"); return true; }
  if (h.startsWith("about/")) {           // shareable deep-link to a methodology subsection
    setTab("about");
    const el = document.getElementById("a-" + h.slice(6));
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    return true;
  }
  return false;
}

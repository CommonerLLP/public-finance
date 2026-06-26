/* LMMHA money-flow Sankey. State + year + view are chosen from the manifest;
   each is just a sankey_<state>_<view>_<fy>.json file built by viz/build_sankey.py.
   Two views: balance (sources -> exchequer -> sectors) and detailed (sector -> sub).
   d3 + d3-sankey. */

const fmt = (v) => "₹" + d3.format(",.0f")(v) + " cr";
const trunc = (s) => (s.length > 42 ? s.slice(0, 41) + "…" : s);
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const qs = new URLSearchParams(location.search);
let STATE = (qs.get("state") || "assam").toLowerCase();
let FY = qs.get("fy") || "";
let VIEW = qs.get("view") || "balance";

let MANIFEST = null;
let stateEntry = null;

const fileFor = (view, fy) => `sankey_${STATE}_${view === "balance" ? "balance" : "sector"}_${fy}.json`;
const titleFor = (view) => view === "balance"
  ? `Where ${cap(STATE)}'s money comes from, and goes`
  : `Where ${cap(STATE)}'s money goes — by sector`;

// ----- selectors -----
function go(next) {
  const p = new URLSearchParams({ state: STATE, fy: FY, view: VIEW, ...next });
  location.search = p.toString();
}
function yearsFor(view) {
  return (stateEntry.views[view] || []).slice().sort();
}
function buildPicker() {
  const selState = document.getElementById("sel-state");
  selState.innerHTML = MANIFEST.states
    .map((s) => `<option value="${esc(s.state)}" ${s.state === STATE ? "selected" : ""}>${esc(s.label)}</option>`).join("");
  selState.onchange = () => go({ state: selState.value, fy: "" });

  const selFy = document.getElementById("sel-fy");
  const years = yearsFor(VIEW);
  selFy.innerHTML = years.map((y) => `<option value="${esc(y)}" ${y === FY ? "selected" : ""}>${esc(y)}</option>`).join("");
  selFy.onchange = () => go({ fy: selFy.value });
}
function bindToggle() {
  document.querySelectorAll(".flow-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      const v = b.dataset.view;
      const years = yearsFor(v);
      const fy = years.includes(FY) ? FY : years[years.length - 1];
      go({ view: v, fy });
    }));
}

// ----- main diagram -----
async function render() {
  const data = await (await fetch(fileFor(VIEW, FY))).json();
  const m = data.meta;

  document.getElementById("title").textContent = titleFor(VIEW) + " — " + m.fy;
  document.getElementById("subtitle").textContent = m.headline || m.classification || "";
  document.getElementById("total").textContent =
    `Total ${fmt(m.total_cr)} (${m.unit}). Source: ${m.source}.`;
  document.getElementById("caveat").textContent = m.caveat;
  document.getElementById("legend").innerHTML = (m.legend || []).map((s) =>
    `<span><i class="swatch" style="background:${esc(s.color)}"></i> ${esc(s.label)}</span>`).join("");
  document.querySelectorAll(".flow-toggle button").forEach((x) =>
    x.classList.toggle("active", x.dataset.view === VIEW));

  const avail = document.querySelector(".flow-wrap").clientWidth;
  const width = Math.max(680, Math.min(1120, avail));
  const height = Math.max(480, data.links.length * 30 + 60);
  const M = Math.min(200, width * 0.27);

  const svg = d3.select("#sankey").attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%").attr("height", height);
  svg.selectAll("*").remove();

  const sankey = d3.sankey()
    .nodeWidth(15).nodePadding(16).iterations(48)
    .extent([[M, 12], [width - M, height - 12]]);
  const graph = sankey({
    nodes: data.nodes.map((d) => Object.assign({}, d)),
    links: data.links.map((d) => Object.assign({}, d)),
  });
  const colorOf = (n) => n.color || "#888";
  const linkColor = (d) => colorOf(d.source.kind === "pool" ? d.target : d.source);

  svg.append("g").selectAll("path")
    .data(graph.links).join("path")
    .attr("class", "link").attr("d", d3.sankeyLinkHorizontal())
    .attr("stroke", linkColor).attr("stroke-width", (d) => Math.max(1, d.width))
    .append("title").text((d) => `${d.source.name} → ${d.target.name}\n${fmt(d.value)}`);

  const node = svg.append("g").selectAll("g")
    .data(graph.nodes).join("g").attr("class", "node");
  node.append("rect")
    .attr("x", (d) => d.x0).attr("y", (d) => d.y0)
    .attr("height", (d) => Math.max(1, d.y1 - d.y0)).attr("width", (d) => d.x1 - d.x0)
    .attr("fill", colorOf).append("title").text((d) => `${d.name}\n${fmt(d.value)}`);
  node.each(function (d) {
    const isSource = !d.targetLinks.length, isSink = !d.sourceLinks.length;
    const t = d3.select(this).append("text").attr("dy", "0.35em");
    if (isSource) t.attr("x", d.x0 - 8).attr("y", (d.y0 + d.y1) / 2).attr("text-anchor", "end");
    else if (isSink) t.attr("x", d.x1 + 8).attr("y", (d.y0 + d.y1) / 2).attr("text-anchor", "start");
    else t.attr("x", (d.x0 + d.x1) / 2).attr("y", d.y0 - 7).attr("text-anchor", "middle").attr("dy", null);
    t.text(trunc(d.name));
    t.append("tspan").attr("class", "amt").text("  " + fmt(d.value));
  });
}

// ----- dual-mandate reading (data-driven from the sector file) -----
async function renderDual() {
  const years = yearsFor("detailed");
  const dfy = years.includes(FY) ? FY : years[years.length - 1];
  if (!dfy) { document.getElementById("flow-dual").style.display = "none"; return; }
  const sec = await (await fetch(fileFor("detailed", dfy))).json();
  const d = sec.meta.dual;
  if (!d) { document.getElementById("flow-dual").style.display = "none"; return; }
  const st = esc(sec.meta.state);
  const debt = d.interest + d.repayment;
  const maxv = Math.max(d.interest, d.repayment, d.health, d.water, 1);
  const bar = (label, val, color) =>
    `<div class="dual-row"><span class="dual-lab">${label}</span>` +
    `<span class="dual-bar" style="width:${Math.max(4, val / maxv * 100)}%;background:${color}"></span>` +
    `<span class="dual-val">${fmt(val)}</span></div>`;

  document.getElementById("dual-lede").innerHTML =
    `Melinda Cooper's <em>Counterrevolution</em> argues that the neoliberal fiscal order runs a double ` +
    `standard: <strong>austerity</strong> for the social wage, <strong>extravagance</strong> for asset ` +
    `holders and creditors. The real extravagance — tax breaks, capital-gains preferences, asset-price ` +
    `support — is exercised <em>upstream</em> by the Union and the RBI; ${cap(st)}'s budget is the ` +
    `austerity terminal of that system. What it <em>does</em> show is the one place the extravagance pole ` +
    `reaches in: the creditor's claim, paid first and in full.`;

  document.getElementById("dual-bars").innerHTML =
    bar("Interest paid to creditors", d.interest, "#b03a3a") +
    bar("+ Public-debt repayment", d.repayment, "#9a5b8f") +
    bar("Public health", d.health, "#2e7d5b") +
    bar("Water supply & sanitation", d.water, "#2e7d5b");

  const cmp = d.interest > d.health
    ? `pays <strong>more in interest to bondholders (${fmt(d.interest)})</strong> than it spends running its ` +
      `<strong>entire public-health system (${fmt(d.health)})</strong>`
    : `spends <strong>${fmt(d.health)} on public health</strong> against <strong>${fmt(d.interest)} in interest ` +
      `to bondholders</strong>`;
  document.getElementById("dual-punch").innerHTML =
    `${cap(st)} ${cmp}. Counting repayment, debt service to creditors (${fmt(debt)}) is the protected claim; ` +
    `the social wage is the disciplined one. The borrowing that generates that interest is itself <em>capped</em> ` +
    `by statute, while the interest on it is not — discipline for the borrower, an assured return for the rentier.`;
  document.getElementById("dual-caveat").textContent =
    `A reading, not an accounting category. Sector figures: ${st} ${sec.meta.basis || ""} ${dfy}. ` +
    `The larger extravagance (Union tax expenditures, asset supports) is not in any state budget.`;
  document.getElementById("flow-dual").style.display = "";
}

// ----- boot -----
document.getElementById("methlink").addEventListener("click", (e) => {
  e.preventDefault(); location.href = "./#about";
});
document.querySelectorAll(".toc button[data-target]").forEach((b) =>
  b.addEventListener("click", () => { document.getElementById(b.dataset.target).scrollIntoView({ behavior: "smooth", block: "start" }); }));
const toTop = document.getElementById("to-top");
toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
window.addEventListener("scroll", () => toTop.classList.toggle("show", window.scrollY > 500));

(async () => {
  MANIFEST = await (await fetch("sankey_manifest.json")).json();
  stateEntry = MANIFEST.states.find((s) => s.state === STATE) || MANIFEST.states[0];
  STATE = stateEntry.state;
  // resolve view + fy against what exists for this state
  if (!stateEntry.views[VIEW]) VIEW = stateEntry.views.balance ? "balance" : "detailed";
  const years = yearsFor(VIEW);
  if (!years.includes(FY)) FY = years[years.length - 1];
  // hide the balance toggle if this state has no balance view
  const balBtn = document.querySelector('.flow-toggle button[data-view="balance"]');
  if (balBtn) balBtn.style.display = stateEntry.views.balance ? "" : "none";

  buildPicker();
  bindToggle();
  await render();
  await renderDual();
})();

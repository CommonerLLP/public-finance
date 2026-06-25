/* LMMHA money-flow Sankey. Two views, toggled:
   - balance  : sources -> exchequer -> functional sectors (RBI, balanced)
   - detailed : exchequer -> sector -> sub-sector (CivicDataLab, uses only)
   d3 + d3-sankey. */

const fmt = (v) => "₹" + d3.format(",.0f")(v) + " cr";
const trunc = (s) => (s.length > 42 ? s.slice(0, 41) + "…" : s);

const VIEWS = {
  balance: { file: "sankey_assam_balance.json", title: "Where Assam's money comes from, and goes" },
  detailed: { file: "sankey_assam.json", title: "Where Assam's money goes — by sector" },
};

let current = "balance";

function bindToggle() {
  document.querySelectorAll(".flow-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      current = b.dataset.view;
      document.querySelectorAll(".flow-toggle button").forEach((x) =>
        x.classList.toggle("active", x.dataset.view === current));
      render();
    }));
}

async function render() {
  const data = await (await fetch(VIEWS[current].file)).json();
  const m = data.meta;

  document.getElementById("title").textContent = VIEWS[current].title + " — " + m.fy;
  document.getElementById("subtitle").textContent = m.headline || m.classification || "";
  document.getElementById("total").textContent =
    `Total ${fmt(m.total_cr)} (${m.unit}). Source: ${m.source}.`;
  document.getElementById("caveat").textContent = m.caveat;
  document.getElementById("legend").innerHTML = (m.legend || []).map((s) =>
    `<span><i class="swatch" style="background:${s.color}"></i> ${s.label}</span>`).join("");

  // keep the diagram legible: never lay out below ~680px — the .sankey-scroll
  // container scrolls horizontally instead of letting the Sankey collapse
  const avail = document.querySelector(".flow-wrap").clientWidth;
  const width = Math.max(680, Math.min(1120, avail));
  const leafCount = data.links.length;
  const height = Math.max(480, leafCount * 30 + 60);
  const M = Math.min(200, width * 0.27);  // side margins for source/sink labels, scaled to width

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
  // colour each link by its non-pool endpoint, so a sector keeps one colour
  const linkColor = (d) => colorOf(d.source.kind === "pool" ? d.target : d.source);

  svg.append("g").selectAll("path")
    .data(graph.links).join("path")
    .attr("class", "link")
    .attr("d", d3.sankeyLinkHorizontal())
    .attr("stroke", linkColor)
    .attr("stroke-width", (d) => Math.max(1, d.width))
    .append("title").text((d) => `${d.source.name} → ${d.target.name}\n${fmt(d.value)}`);

  const node = svg.append("g").selectAll("g")
    .data(graph.nodes).join("g").attr("class", "node");

  node.append("rect")
    .attr("x", (d) => d.x0).attr("y", (d) => d.y0)
    .attr("height", (d) => Math.max(1, d.y1 - d.y0))
    .attr("width", (d) => d.x1 - d.x0)
    .attr("fill", colorOf)
    .append("title").text((d) => `${d.name}\n${fmt(d.value)}`);

  // label placement by role: pure source -> left; pure sink -> right; junction -> above
  node.each(function (d) {
    const isSource = !d.targetLinks.length;
    const isSink = !d.sourceLinks.length;
    const t = d3.select(this).append("text").attr("dy", "0.35em");
    if (isSource) {
      t.attr("x", d.x0 - 8).attr("y", (d.y0 + d.y1) / 2).attr("text-anchor", "end");
    } else if (isSink) {
      t.attr("x", d.x1 + 8).attr("y", (d.y0 + d.y1) / 2).attr("text-anchor", "start");
    } else {  // junction (the exchequer / a sector with children)
      t.attr("x", (d.x0 + d.x1) / 2).attr("y", d.y0 - 7).attr("text-anchor", "middle").attr("dy", null);
    }
    t.text(trunc(d.name));
    t.append("tspan").attr("class", "amt").text("  " + fmt(d.value));
  });
}

document.getElementById("methlink").addEventListener("click", (e) => {
  e.preventDefault(); location.href = "./#about";
});

// in-page jump nav + back-to-top
document.querySelectorAll(".toc button[data-target]").forEach((b) =>
  b.addEventListener("click", () => {
    const el = document.getElementById(b.dataset.target);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
const toTop = document.getElementById("to-top");
toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
window.addEventListener("scroll", () => toTop.classList.toggle("show", window.scrollY > 500));

bindToggle();
render();

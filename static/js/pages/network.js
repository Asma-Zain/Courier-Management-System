(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const msg = ui.$("#msg");
  const [branches, network] = await Promise.all([api.get("/api/branches"), api.get("/api/graph/network")]);
  const from = ui.$("#from"), to = ui.$("#to"), hub = ui.$("#hub");
  ui.fill(from, branches, "name", "name"); ui.fill(to, branches, "name", "name"); ui.fill(hub, branches, "name", "name");
  const params = new URLSearchParams(location.search);
  from.selectedIndex = Math.max(0, branches.findIndex(b => b.name === "Hyderabad Hub"));
  to.selectedIndex = Math.max(0, branches.findIndex(b => b.name === "Coimbatore Hub"));
  hub.value = params.get("hub") && branches.some(b => b.name === params.get("hub")) ? params.get("hub") : "Chennai Hub";

  // ---- one shared map
  const sizes = Object.fromEntries(network.nodes.map(n => [n.id, n.group === "HUB" ? 22 : 16]));
  const net = ui.graph(ui.$("#graph"), { nodes: network.nodes.map(n => ({ ...n, size: sizes[n.id] })),
    edges: network.edges.map(e => ({ ...e, arrows: "", font: { size: 12, strokeWidth: 5, strokeColor: ui.cssVar("--c-bg"), color: ui.cssVar("--c-text-2"), align: "middle" } })) },
    { physics: { solver: "forceAtlas2Based", forceAtlas2Based: { springLength: 230, gravitationalConstant: -90, avoidOverlap: 1 } } });
  const idOf = (name) => (network.nodes.find(n => n.label === name) || {}).id;

  function highlight(route) {
    if (!net) return;
    const nodes = net.body.data.nodes, edges = net.body.data.edges;
    const set = new Set(route || []);
    const pairs = (route || []).slice(1).map((n, i) => [idOf(route[i]), idOf(n)]);
    nodes.update(network.nodes.map(n => ({ id: n.id, borderWidth: set.has(n.label) ? 5 : 1, size: sizes[n.id] + (set.has(n.label) ? 6 : 0) })));
    edges.update(edges.get().map(e => {
      const on = pairs.some(([a, b]) => (e.from === a && e.to === b) || (e.from === b && e.to === a));
      return { id: e.id, width: on ? 5 : 2, color: { color: on ? ui.cssVar("--c-coral") : ui.cssVar("--c-border") } };
    }));
  }

  // ---- tabs
  let tab = params.get("tab") === "impact" ? "impact" : "routes";
  const tabs = ui.tabs(ui.$("#tabs"), [{ id: "routes", label: "Routes" }, { id: "impact", label: "Hub impact" }], (t) => {
    tab = t;
    history.replaceState(null, "", `/network?tab=${t}${t === "impact" ? "&hub=" + encodeURIComponent(hub.value) : ""}`);
    if (t === "impact") loadImpact(); else findRoutes();
  }, tab);

  // ---- routes (run automatically on change)
  let selected = null;
  const chips = (route) => ui.el("div", { class: "path" }, route.flatMap((n, i) => i ? [ui.icon("arrow"), ui.el("span", { class: "stop-chip" }, n)] : [ui.el("span", { class: "stop-chip" }, n)]));
  function card(kind, r) {
    const b = ui.el("button", { type: "button", class: "result-card", "aria-pressed": "false",
      onclick: () => { ui.$$(".result-card").forEach(x => x.setAttribute("aria-pressed", "false")); b.setAttribute("aria-pressed", "true"); highlight(r.route); } },
      ui.el("span", { class: "kind" }, kind), chips(r.route),
      ui.el("strong", {}, `${r.hops} ${r.hops === 1 ? "hop" : "hops"} · ${ui.fmtNum(r.km)} km`));
    return b;
  }
  async function findRoutes() {
    const out = ui.$("#results"), box = ui.$("#route-error");
    ui.formError(box, ""); ui.setError(to, "");
    if (from.value === to.value) { ui.clear(out); ui.setError(to, "Choose two different locations."); highlight([]); return; }
    ui.skeleton(out, 2);
    try {
      const p = { from: from.value, to: to.value };
      const [hops, kms] = await Promise.all([api.get("/api/routes/fewest-hops", p), api.get("/api/routes/fewest-km", p)]);
      ui.clear(out).removeAttribute("aria-busy");
      if (!hops.route.length) { out.append(ui.el("p", { class: "empty" }, "No route between these locations.")); highlight([]); return; }
      out.append(ui.el("h2", {}, "Fewest hops"), card("Fewest hops", hops), ui.el("h2", {}, "Fewest kilometres (top 3)"),
        ...kms.map((r, i) => card(i === 0 ? "Shortest distance" : `Option ${i + 1}`, r)));
      ui.$(".result-card", out).click();
    } catch (err) { ui.clear(out); ui.formError(box, err.message); }
  }
  from.addEventListener("change", findRoutes); to.addEventListener("change", findRoutes);
  ui.$("#swap").prepend(ui.icon("swap"), " ");
  ui.$("#swap").addEventListener("click", () => { [from.value, to.value] = [to.value, from.value]; findRoutes(); });

  // ---- hub impact (dropdown or click on the map)
  async function loadImpact() {
    const out = ui.$("#impact");
    highlight([hub.value]);
    history.replaceState(null, "", `/network?tab=impact&hub=${encodeURIComponent(hub.value)}`);
    ui.skeleton(out, 2);
    try {
      const rows = await api.get(`/api/hubs/${encodeURIComponent(hub.value)}/impact`);
      ui.table(out, [
        { key: "shipment", label: "Shipment", render: r => ui.el("a", { href: `/shipments/${r.shipment}` }, `#${r.shipment}`) },
        { key: "status", label: "Status", render: r => ui.badge(r.status) },
        { key: "receiver", label: "Receiver waiting" },
        { key: "phone", label: "Phone", render: r => ui.el("a", { href: `tel:${r.phone}` }, r.phone) },
      ], rows, { empty: `No shipments are waiting at ${hub.value}.` });
    } catch (err) { ui.errorState(out, err.message, loadImpact); }
  }
  hub.addEventListener("change", loadImpact);

  if (net) net.on("click", (p) => {
    if (!p.nodes.length) return;
    const name = network.nodes.find(n => n.id === p.nodes[0]).label;
    if (tab === "impact") { hub.value = name; loadImpact(); }
    else if (from.value !== name) { to.value = name === from.value ? to.value : name; findRoutes(); }
  });
})();

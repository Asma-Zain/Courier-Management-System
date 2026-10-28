(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const staff = user.role === "STAFF";
  const msg = ui.$("#msg"), list = ui.$("#list");
  ui.$("#title").textContent = staff ? "Shipments" : "My parcels";

  const CHIPS = [["ALL", "All"], ["ACTIVE", "Active"], ["BOOKED", "Booked"], ["IN_TRANSIT", "In transit"],
                 ["OUT_FOR_DELIVERY", "Out for delivery"], ["DELIVERED", "Delivered"], ["DELAYED", "Delayed"], ["CANCELLED", "Cancelled"]];
  const state = { q: ui.qs("q") || "", status: ui.qs("status") || "ALL", sort: ui.qs("sort") || "newest",
                  page: parseInt(ui.qs("page") || "1", 10), payment: ui.qs("payment") || "" };
  const q = ui.$("#q"), sort = ui.$("#sort");
  q.value = state.q; sort.value = state.sort;

  function syncUrl() {
    const p = new URLSearchParams();
    if (state.q) p.set("q", state.q);
    if (state.status !== "ALL") p.set("status", state.status);
    if (state.sort !== "newest") p.set("sort", state.sort);
    if (state.payment) p.set("payment", state.payment);
    if (state.page > 1) p.set("page", state.page);
    history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p : ""));
  }

  function drawChips(counts) {
    ui.clear(ui.$("#chips")).append(...CHIPS.map(([key, label]) =>
      ui.el("button", { class: "chip", type: "button", "aria-pressed": String(state.status === key),
        onclick: () => { state.status = key; state.page = 1; load(); } },
        label, " ", ui.el("span", { class: "n" }, `(${counts[key] ?? 0})`))));
    const pf = ui.clear(ui.$("#pay-filter"));
    if (state.payment) pf.append(ui.el("button", { class: "chip", type: "button", "aria-pressed": "true",
      onclick: () => { state.payment = ""; state.page = 1; load(); } }, `${state.payment.toLowerCase()} only ✕`));
  }

  async function load() {
    syncUrl();
    ui.message(msg, "");
    ui.skeleton(list, 4);
    try {
      const r = await api.get("/api/shipments", { q: state.q, status: state.status === "ALL" ? "" : state.status,
        payment: state.payment, sort: state.sort, page: state.page, pageSize: 20 });
      drawChips(r.counts);
      if (!r.items.length) {
        const filtered = state.q || state.status !== "ALL" || state.payment;
        ui.emptyState(list, filtered ? "No shipments match" : "No shipments yet",
          filtered ? "Try a different search or filter." : (staff ? "Book the first shipment to get started." : "Send your first parcel."),
          filtered ? null : { href: "/shipments/new", label: staff ? "New shipment" : "Send a parcel" });
      } else if (staff) {
        ui.table(list, ui.shipmentColumns(), r.items, { href: (row) => `/shipments/${row.shipmentId}` });
        list.classList.add("card");
      } else {
        list.classList.remove("card");
        ui.clear(list).removeAttribute("aria-busy");
        list.append(ui.el("div", { class: "parcel-list" }, r.items.map(ui.parcelCard)));
      }
      ui.pager(ui.$("#pager"), r, (p) => { state.page = p; load(); window.scrollTo({ top: 0 }); });
    } catch (err) {
      ui.errorState(list, err.message, load);
    }
  }

  q.addEventListener("input", ui.debounce(() => { state.q = q.value.trim(); state.page = 1; load(); }, 350));
  sort.addEventListener("change", () => { state.sort = sort.value; state.page = 1; load(); });
  load();
})();

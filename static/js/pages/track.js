(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");
  const staff = user.role === "STAFF";
  let currentId = null;

  const { form, input } = ui.searchBar({ onSubmit: (id) => load(id) });
  ui.$("#search-slot").append(form, ui.el("p", { class: "try-line", id: "try" }));
  ui.tryLine(ui.$("#try"), (id) => `/track.html?id=${id}`);
  ui.$("#copy-id").append(ui.icon("copy"));
  ui.$("#share").append(ui.icon("share"));

  async function load(id) {
    ui.message(msg, "");
    ui.$("#result").hidden = true;
    try {
      const [ship, journey, graph] = await Promise.all([
        api.get(`/api/shipments/${id}`),
        api.get(`/api/shipments/${id}/track`),
        api.get(`/api/graph/shipment/${id}`),
      ]);
      currentId = ship.shipmentId;
      input.value = currentId;
      history.replaceState(null, "", `?id=${currentId}`);

      ui.$("#d-id").textContent = `#${ship.shipmentId}`;
      const route = ui.clear(ui.$("#d-route"));
      route.append(ship.sender.city, ui.icon("arrow"), ship.receiver.city);
      ui.$("#d-sub").textContent = `${ship.shipmentType} · Booked ${ship.bookingDate} at ${ship.bookedAt}`;
      ui.clear(ui.$("#d-status")).append(ui.badge(ship.status || "BOOKED"));

      ui.timeline(ui.$("#timeline"), journey, ship.status);
      ui.routeMap(ui.$("#map"), ui.mapData(ship, journey));
      ui.etaCard(ui.$("#eta"), ship);
      ui.$("#map-link").href = `/live.html?id=${currentId}`;

      const dl = ui.clear(ui.$("#details"));
      for (const [k, v] of [
        ["Sender", `${ship.sender.firstName} ${ship.sender.lastName} (${ship.sender.city})`],
        ["Receiver", `${ship.receiver.firstName} ${ship.receiver.lastName} (${ship.receiver.city})`],
        ["Weight", `${ship.weightKg} kg`], ["Amount", String(ship.totalAmount)],
        ["Payment", ship.payment ? `${ship.payment.amount} ${ship.payment.mode} · ${ship.payment.status}` : "No payment recorded"],
      ]) dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));

      ui.table(ui.$("#packages"), [
        { key: "packageId", label: "Id" }, { key: "description", label: "Description" },
        { key: "packageType", label: "Type" }, { key: "weightKg", label: "Kg" },
      ], ship.packages, "No packages.");

      ui.$("#delivered-link").hidden = ship.status !== "DELIVERED";
      ui.$("#delivered-a").href = `/delivered.html?id=${currentId}`;

      ui.$("#result").hidden = false;
      ui.graph(ui.clear(ui.$("#graph")), graph, { layout: { hierarchical: { direction: "LR", sortMethod: "directed", levelSeparation: 160 } }, physics: false });

      if (staff) {
        ui.$("#staff-forms").hidden = false;
        ui.$("#pay-form").hidden = !!ship.payment;
        ui.$("#pay-amount").value = ship.totalAmount;
      }
    } catch (err) {
      ui.message(msg, err.message);
    }
  }

  ui.$("#copy-id").addEventListener("click", () => ui.copy(String(currentId)));
  ui.$("#share").addEventListener("click", () => ui.copy(`${location.origin}/track.html?id=${currentId}`));

  if (staff) {
    const branches = await api.get("/api/branches");
    ui.fill(ui.$("#ev-branch"), branches, "name", "name");
    for (const s of ["BOOKED", "PICKED_UP", "IN_TRANSIT", "AT_BRANCH", "OUT_FOR_DELIVERY", "DELIVERED", "DELAYED", "CANCELLED"]) {
      ui.$("#ev-status").append(ui.el("option", { value: s }, ui.label(s)));
    }
    for (const m of ["UPI", "CARD", "NETBANKING", "CASH"]) ui.$("#pay-mode").append(ui.el("option", { value: m }, m));
    for (const s of ["PAID", "PENDING"]) ui.$("#pay-status").append(ui.el("option", { value: s }, s));

    ui.$("#event-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await api.post(`/api/shipments/${currentId}/events`, { status: ui.$("#ev-status").value, branch: ui.$("#ev-branch").value });
        await load(currentId);
        ui.message(msg, `Added event ${r.eventId}: ${ui.label(r.status)} at ${r.place}.`, "ok");
      } catch (err) { ui.message(msg, err.message); }
    });
    ui.$("#pay-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api.post(`/api/shipments/${currentId}/payment`, {
          amount: parseFloat(ui.$("#pay-amount").value), mode: ui.$("#pay-mode").value, status: ui.$("#pay-status").value });
        await load(currentId);
        ui.message(msg, "Payment recorded.", "ok");
      } catch (err) { ui.message(msg, err.message); }
    });
  }

  const initial = ui.qs("id");
  if (initial) load(initial);
})();

(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");
  const staff = user.role === "STAFF";
  let currentId = null;

  async function load(id) {
    ui.message(msg, "");
    ui.$("#result").hidden = true;
    try {
      const [ship, journey, graph] = await Promise.all([
        api.get(`/api/shipments/${id}`),
        api.get(`/api/shipments/${id}/track`),
        api.get(`/api/graph/shipment/${id}`),
      ]);
      currentId = id;
      history.replaceState(null, "", `?id=${id}`);
      ui.$("#d-id").textContent = `#${ship.shipmentId}`;
      ui.clear(ui.$("#d-status")).append(ui.badge(ship.status));
      const dl = ui.clear(ui.$("#details"));
      const rows = [
        ["Type", ship.shipmentType], ["Booked", `${ship.bookingDate} at ${ship.bookedAt}`],
        ["Sender", `${ship.sender.firstName} ${ship.sender.lastName} (${ship.sender.city})`],
        ["Receiver", `${ship.receiver.firstName} ${ship.receiver.lastName} (${ship.receiver.city})`],
        ["Weight", `${ship.weightKg} kg`], ["Amount", String(ship.totalAmount)],
        ["Now at", ship.place ? `${ship.place} (since ${ship.since})` : "No events yet"],
        ["Payment", ship.payment ? `${ship.payment.amount} ${ship.payment.mode} · ${ship.payment.status}` : "No payment recorded"],
      ];
      for (const [k, v] of rows) dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));

      const tl = ui.clear(ui.$("#timeline"));
      for (const j of journey) {
        tl.append(ui.el("li", {}, ui.badge(j.status), ` ${j.place}`, ui.el("div", { class: "muted small" }, j.time)));
      }
      if (!journey.length) tl.append(ui.el("li", { class: "muted" }, "No tracking events yet."));

      ui.table(ui.$("#packages"), [
        { key: "packageId", label: "Id" }, { key: "description", label: "Description" },
        { key: "packageType", label: "Type" }, { key: "dimensions", label: "Dimensions" },
        { key: "weightKg", label: "Kg" },
      ], ship.packages, "No packages.");

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

  ui.$("#track-form").addEventListener("submit", (e) => { e.preventDefault(); load(ui.$("#sid").value); });

  if (staff) {
    const [branches] = await Promise.all([api.get("/api/branches")]);
    ui.fill(ui.$("#ev-branch"), branches, "name", "name");
    for (const s of ["BOOKED", "PICKED_UP", "IN_TRANSIT", "AT_BRANCH", "OUT_FOR_DELIVERY", "DELIVERED", "DELAYED", "CANCELLED"]) {
      ui.$("#ev-status").append(ui.el("option", { value: s }, s));
    }
    for (const m of ["UPI", "CARD", "NETBANKING", "CASH"]) ui.$("#pay-mode").append(ui.el("option", { value: m }, m));
    for (const s of ["PAID", "PENDING"]) ui.$("#pay-status").append(ui.el("option", { value: s }, s));

    ui.$("#event-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await api.post(`/api/shipments/${currentId}/events`, { status: ui.$("#ev-status").value, branch: ui.$("#ev-branch").value });
        await load(currentId);
        ui.message(msg, `Added event ${r.eventId}: ${r.status} at ${r.place}.`, "ok");
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
  if (initial) { ui.$("#sid").value = initial; load(initial); }
})();

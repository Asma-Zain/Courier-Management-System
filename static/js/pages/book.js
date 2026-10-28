(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");
  const staff = user.role === "STAFF";

  const [branches] = await Promise.all([api.get("/api/branches")]);
  ui.fill(ui.$("#branch"), branches.filter(b => b.kind === "BRANCH").concat(branches.filter(b => b.kind !== "BRANCH")), "branchId", "name");
  for (const t of ["STANDARD", "EXPRESS", "OVERNIGHT"]) ui.$("#stype").append(ui.el("option", { value: t }, t));

  if (staff) {
    const customers = await api.get("/api/customers");
    ui.fill(ui.$("#sender"), customers.map(c => ({ id: c.customerId, label: `${c.firstName} ${c.lastName} (${c.email})` })), "id", "label");
  } else {
    ui.$("#sender-wrap").hidden = true;
    ui.$("#receiver-hint").textContent = `You are booking as ${user.name}.`;
  }

  let count = 0;
  function addPackage() {
    count += 1;
    const row = ui.el("div", { class: "package-row" },
      ui.el("div", { class: "form-grid" },
        ui.el("label", {}, "Description", ui.el("input", { class: "p-desc", required: true, maxlength: 120 })),
        ui.el("label", {}, "Dimensions", ui.el("input", { class: "p-dim", required: true, placeholder: "30x20x10 cm" })),
        ui.el("label", {}, "Type", ui.el("select", { class: "p-type" }, ["Box", "Envelope", "Parcel"].map(t => ui.el("option", { value: t }, t)))),
        ui.el("label", {}, "Weight (kg)", ui.el("input", { class: "p-kg", type: "number", step: "0.01", min: "0.01", required: true }))),
      ui.el("button", { type: "button", class: "link", onclick: () => { if (ui.$("#packages").children.length > 1) row.remove(); } }, "Remove this package"));
    ui.$("#packages").append(row);
  }
  addPackage();
  ui.$("#add-pkg").addEventListener("click", addPackage);

  ui.$("#book-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    ui.message(msg, "");
    try {
      const receiver = await api.get("/api/customers/lookup", { email: ui.$("#receiver-email").value });
      const packages = [...document.querySelectorAll(".package-row")].map(r => ({
        description: ui.$(".p-desc", r).value, dimensions: ui.$(".p-dim", r).value,
        packageType: ui.$(".p-type", r).value, weightKg: parseFloat(ui.$(".p-kg", r).value),
      }));
      const body = { receiver: receiver.customerId, branchId: parseInt(ui.$("#branch").value, 10),
                     shipmentType: ui.$("#stype").value, packages };
      if (staff) body.sender = parseInt(ui.$("#sender").value, 10);
      const amount = ui.$("#amount").value;
      if (amount) body.totalAmount = parseFloat(amount);
      const r = await api.post("/api/shipments", body);
      ui.message(msg, `Booked shipment ${r.shipmentId} to ${receiver.name}: ${r.packages} package(s), ${r.weightKg} kg, amount ${r.totalAmount}.`, "ok");
      ui.$("#msg").append(" ", ui.el("a", { href: `/track.html?id=${r.shipmentId}` }, "Track it"));
      ui.$("#book-form").reset();
      ui.clear(ui.$("#packages")); addPackage();
    } catch (err) { ui.message(msg, err.message); }
  });
})();

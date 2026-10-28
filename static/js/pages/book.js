(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const staff = user.role === "STAFF";
  const flow = ui.$("#flow");

  const [branches, rates, customers] = await Promise.all([
    api.get("/api/branches"), api.get("/api/shipments/rates"), staff ? api.get("/api/customers") : Promise.resolve([])]);
  const DIMS = /^\d+(\.\d+)?\s*[x×]\s*\d+(\.\d+)?\s*[x×]\s*\d+(\.\d+)?\s*(cm)?$/i;
  const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  const TYPES = { STANDARD: "Standard", EXPRESS: "Express", OVERNIGHT: "Overnight" };

  const state = {
    step: 1, sender: staff ? (customers[0] || {}).customerId : user.id, receiverEmail: "", receiver: null /* lookup result */,
    packages: [{ description: "", dimensions: "", packageType: "Box", weightKg: "" }],
    shipmentType: "STANDARD", branchId: (branches.find(b => b.kind === "BRANCH") || branches[0]).branchId,
    payNow: false, payMode: "UPI", payStatus: "PAID",
  };

  const totalKg = () => Math.round(state.packages.reduce((t, p) => t + (parseFloat(p.weightKg) || 0), 0) * 100) / 100;
  const price = () => { const r = rates[state.shipmentType]; return Math.round((r.base + r.perKg * totalKg()) * 100) / 100; };

  // ---------------- stepper ----------------
  function stepper() {
    const names = ["Parties", "Packages", "Review and pay"];
    return ui.el("ol", { class: "stepper", "aria-label": "Booking steps" }, names.map((n, i) =>
      ui.el("li", { class: state.step > i + 1 ? "done" : "", "aria-current": state.step === i + 1 ? "step" : false },
        ui.el("span", { class: "n" }, state.step > i + 1 ? ui.icon("check") : String(i + 1)), ui.el("span", { class: "t" }, n))));
  }
  function screen(...content) {
    ui.clear(flow).append(stepper(), ...content);
    const h = ui.$("h2", flow); if (h) { h.setAttribute("tabindex", "-1"); }
  }

  // ---------------- step 1: parties ----------------
  async function lookup(email, out) {
    state.receiver = null;
    ui.clear(out);
    if (!EMAIL.test(email)) return;
    const mySeq = (lookup.seq = (lookup.seq || 0) + 1);
    out.append(ui.el("span", { class: "hint" }, "Checking…"));
    try {
      const r = await api.get("/api/customers/lookup", { email });
      if (mySeq !== lookup.seq) return;
      ui.clear(out);
      state.receiver = r;
      if (r.exists) {
        out.append(ui.el("span", { class: "chip-ok" }, ui.icon("check"), r.name ? `${r.name}, ${r.city}` : r.displayName));
      } else {
        out.append(ui.el("span", { class: "chip-ok chip-bad" }, ui.icon("alert"), "No customer with this email."));
        if (staff) out.append(" ", ui.el("button", { type: "button", class: "link", onclick: () =>
          CustomerForm.open({ email, onSaved: () => lookup(email, out) }) }, "Add this customer"));
      }
    } catch (err) { ui.clear(out).append(ui.el("span", { class: "chip-ok chip-bad" }, err.status === 429 ? "Too many checks, wait a moment." : err.message)); }
  }

  function step1(serverError) {
    state.step = 1;
    const err = ui.el("div", { class: "form-error", role: "alert", hidden: !serverError }, serverError || "");
    const email = ui.el("input", { type: "email", value: state.receiverEmail, placeholder: "priya@example.com", autocomplete: "off", "aria-label": "Receiver email" });
    const out = ui.el("div", { class: "row" });
    const senderSel = ui.el("select", {});
    if (staff) {
      ui.fill(senderSel, customers.map(c => ({ id: c.customerId, l: `${c.firstName} ${c.lastName} (${c.email})` })), "id", "l");
      senderSel.value = state.sender;
    }
    const doLookup = ui.debounce(() => { state.receiverEmail = email.value.trim(); lookup(state.receiverEmail, out); }, 450);
    email.addEventListener("input", doLookup);
    const next = ui.el("button", { type: "button" }, "Next: packages");
    next.addEventListener("click", async () => {
      state.receiverEmail = email.value.trim();
      if (staff) state.sender = parseInt(senderSel.value, 10);
      if (!ui.check([[email, (v) => !EMAIL.test(v) ? "Enter the receiver’s email address."
        : (!staff && v.toLowerCase() === (user.email || "").toLowerCase() ? "You cannot send a parcel to yourself." : null)]])) return;
      if (!state.receiver || state.receiver.exists === undefined) await lookup(state.receiverEmail, out);
      if (!state.receiver || !state.receiver.exists) { ui.setError(email, "No customer with this email."); email.focus(); return; }
      step2();
    });
    screen(ui.el("section", { class: "card" }, ui.el("h2", {}, "Who is sending to whom?"),
      ui.el("div", { class: "form-grid" },
        staff ? ui.field("Sender", senderSel, { required: true })
              : ui.el("div", { class: "label" }, "Sender", ui.el("strong", {}, `${user.name}${user.lastName ? " " + user.lastName : ""} (you)`)),
        ui.field("Receiver email", email, { required: true })),
      out, err, ui.el("p", {}, next)));
    if (state.receiverEmail) lookup(state.receiverEmail, out);
    if (serverError) ui.formError(err, serverError);
  }

  // ---------------- step 2: packages ----------------
  function step2() {
    state.step = 2;
    const list = ui.el("div", {});
    const totalEl = ui.el("div", { class: "total-line" });
    const err = ui.el("div", { class: "form-error", role: "alert", hidden: true });
    const controls = [];

    function sync() { totalEl.replaceChildren(ui.el("span", {}, `Total weight (${state.packages.length} package${state.packages.length > 1 ? "s" : ""})`), ui.el("span", {}, `${totalKg()} kg`)); }
    function draw() {
      ui.clear(list); controls.length = 0;
      state.packages.forEach((p, i) => {
        const desc = ui.el("input", { value: p.description, maxlength: 120, placeholder: "Gift box" });
        const dim = ui.el("input", { value: p.dimensions, placeholder: "30x20x10 cm" });
        const type = ui.el("select", {}, ["Box", "Envelope", "Parcel"].map(t => ui.el("option", { value: t, selected: t === p.packageType }, t)));
        const kg = ui.el("input", { type: "number", step: "0.01", min: "0.01", value: p.weightKg, inputmode: "decimal" });
        desc.addEventListener("input", () => { p.description = desc.value; });
        dim.addEventListener("input", () => { p.dimensions = dim.value; });
        type.addEventListener("change", () => { p.packageType = type.value; });
        kg.addEventListener("input", () => { p.weightKg = kg.value; sync(); });
        controls.push([desc, (v) => v ? null : "Describe what is inside."],
                      [dim, (v) => DIMS.test(v) ? null : "Use length x width x height, for example 30x20x10 cm."],
                      [kg, (v) => parseFloat(v) >= 0.01 ? null : "Weight must be at least 0.01 kg."]);
        list.append(ui.el("div", { class: "package-card" },
          ui.el("div", { class: "card-head" }, ui.el("strong", {}, `Package ${i + 1}`),
            state.packages.length > 1 ? ui.el("button", { type: "button", class: "link", onclick: () => { state.packages.splice(i, 1); draw(); } }, "Remove") : ""),
          ui.el("div", { class: "form-grid" }, ui.field("Description", desc, { required: true }), ui.field("Dimensions", dim, { required: true }),
            ui.field("Type", type, { required: true }), ui.field("Weight (kg)", kg, { required: true }))));
      });
      sync();
    }
    draw();
    screen(ui.el("section", { class: "card" }, ui.el("h2", {}, "What are you sending?"), list,
      ui.el("button", { type: "button", class: "secondary", onclick: () => { state.packages.push({ description: "", dimensions: "", packageType: "Box", weightKg: "" }); draw(); } }, ui.icon("plus"), "Add another package"),
      totalEl, err,
      ui.el("div", { class: "row" }, ui.el("button", { type: "button", class: "secondary", onclick: () => step1() }, "Back"),
        ui.el("button", { type: "button", onclick: () => { if (ui.check(controls)) step3(); } }, "Next: review"))));
  }

  // ---------------- step 3: review and pay ----------------
  function step3() {
    state.step = 3;
    const err = ui.el("div", { class: "form-error", role: "alert", hidden: true });
    const type = ui.el("select", {}, Object.entries(TYPES).map(([v, l]) => ui.el("option", { value: v, selected: v === state.shipmentType }, l)));
    const branch = ui.el("select", {});
    ui.fill(branch, branches, "branchId", "name"); branch.value = state.branchId;
    const priceEl = ui.el("div", {}), submit = ui.el("button", { type: "button" }, "Book shipment");
    const mode = ui.el("select", {}, ["UPI", "CARD", "NETBANKING", "CASH"].map(m => ui.el("option", { value: m, selected: m === state.payMode }, m)));
    const pstatus = ui.el("select", {}, [["PAID", "Paid"], ["PENDING", "Pending"]].map(([v, l]) => ui.el("option", { value: v, selected: v === state.payStatus }, l)));
    const payNow = ui.el("input", { type: "checkbox", checked: state.payNow });
    const payFields = ui.el("div", { class: "form-grid", hidden: !state.payNow }, ui.field("Payment mode", mode), ui.field("Payment status", pstatus));

    function preview() {
      state.shipmentType = type.value; state.branchId = parseInt(branch.value, 10);
      const r = rates[state.shipmentType];
      priceEl.replaceChildren(ui.el("div", { class: "small muted" }, "Price (demo rate card)"),
        ui.el("div", { class: "price" }, ui.fmtMoney(price())),
        ui.el("div", { class: "small muted" }, `${ui.fmtMoney(r.base)} base + ${totalKg()} kg × ${ui.fmtMoney(r.perKg)}/kg`));
    }
    type.addEventListener("change", preview); branch.addEventListener("change", preview); preview();
    payNow.addEventListener("change", () => { state.payNow = payNow.checked; payFields.hidden = !payNow.checked; });
    mode.addEventListener("change", () => { state.payMode = mode.value; });
    pstatus.addEventListener("change", () => { state.payStatus = pstatus.value; });

    const senderName = staff ? (customers.find(c => c.customerId === state.sender) || {}).firstName + " " + (customers.find(c => c.customerId === state.sender) || {}).lastName : `${user.name} (you)`;
    const receiverName = state.receiver.name ? `${state.receiver.name}, ${state.receiver.city}` : state.receiver.displayName;
    const summary = ui.el("dl", { class: "facts" },
      ui.el("dt", {}, "From"), ui.el("dd", {}, senderName), ui.el("dt", {}, "To"), ui.el("dd", {}, `${receiverName} (${state.receiverEmail})`),
      ui.el("dt", {}, "Packages"), ui.el("dd", {}, state.packages.map(p => `${p.description} (${p.packageType}, ${p.weightKg} kg)`).join("; ")),
      ui.el("dt", {}, "Total weight"), ui.el("dd", {}, `${totalKg()} kg`));

    submit.addEventListener("click", async () => {
      ui.formError(err, ""); submit.disabled = true;
      const body = { receiverEmail: state.receiverEmail, branchId: state.branchId, shipmentType: state.shipmentType,
        packages: state.packages.map(p => ({ description: p.description.trim(), dimensions: p.dimensions.trim(), packageType: p.packageType, weightKg: parseFloat(p.weightKg) })) };
      if (staff) { body.sender = state.sender; if (state.payNow) body.payment = { mode: state.payMode, status: state.payStatus }; }
      try { success(await api.post("/api/shipments", body)); }
      catch (e) {
        submit.disabled = false;
        if (e.code === "RECEIVER_NOT_FOUND") step1(e.message); else ui.formError(err, e.message);
      }
    });
    screen(ui.el("section", { class: "card" }, ui.el("h2", {}, "Review and pay"),
      ui.el("div", { class: "form-grid" }, ui.field("Shipment type", type, { required: true }), ui.field("Booking branch", branch, { required: true })),
      priceEl, ui.el("hr"), summary,
      staff ? ui.el("div", {}, ui.el("label", { class: "row" }, payNow, "Record the payment now"), payFields) : "",
      err, ui.el("div", { class: "row" }, ui.el("button", { type: "button", class: "secondary", onclick: step2 }, "Back"), submit)));
  }

  function success(r) {
    const url = `${location.origin}/shipments/${r.shipmentId}`;
    ui.clear(flow).append(ui.el("div", { class: "success" },
      ui.el("img", { src: "/img/mascot-happy.svg", alt: "Happy cardboard parcel celebrating" }),
      ui.el("h1", {}, "Booked!"),
      ui.el("p", {}, `Shipment #${r.shipmentId} is booked: ${r.packages} package${r.packages > 1 ? "s" : ""}, ${r.weightKg} kg, ${ui.fmtMoney(r.totalAmount)}${r.paid ? " (payment recorded)" : ""}.`),
      ui.el("div", { class: "row" },
        ui.el("a", { class: "button", href: `/shipments/${r.shipmentId}` }, "Track it"),
        ui.el("button", { type: "button", class: "secondary", onclick: () => ui.copy(url) }, ui.icon("copy"), "Copy link"),
        ui.el("a", { class: "button secondary", href: "/shipments/new" }, "Book another"))));
    ui.$("h1", flow).setAttribute("tabindex", "-1"); ui.$("h1", flow).focus();
  }

  step1();
})();

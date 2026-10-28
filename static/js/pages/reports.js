(async function () {
  const user = await ui.init({ staffOnly: true });
  if (!user) return;
  const msg = ui.$("#msg");

  const reports = [
    ["busiest-locations", "G7 · Busiest locations", "Tracking events per branch or hub."],
    ["customer-network", "G8 · Customer network", "Who a customer can reach in two hops (sent to someone who sent to someone)."],
    ["delayed", "G9 · Delayed shipments", "Shipments whose current status is DELAYED."],
    ["branch-performance", "G10 · Branch performance", "Shipments booked and their value, per branch."],
    ["employee-activity", "G11 · Employee activity", "Tracking events logged per employee."],
    ["payments", "G12 · Payments and outstanding", "Total, paid (PAID only) and outstanding per shipment."],
    ["packages-per-shipment", "G13 · Packages per shipment", "Package count, total and heaviest package."],
    ["heavier-than-average", "G14 · Heavier than average", "Shipments above the average weight."],
    ["customer-activity", "G15 · Sent and received per customer", "Counts of shipments sent and received."],
    ["tracking-duration", "G16 · Hours tracked", "Time between first and latest tracking event."],
  ];
  const select = ui.$("#report");
  for (const [key, label] of reports) select.append(ui.el("option", { value: key }, label));

  const wrap = ui.$("#cust-wrap");
  select.addEventListener("change", () => { wrap.hidden = select.value !== "customer-network"; });

  async function run() {
    ui.message(msg, "");
    const [key, label, desc] = reports.find(r => r[0] === select.value);
    ui.$("#report-title").textContent = label;
    ui.$("#report-desc").textContent = desc;
    try {
      const params = key === "customer-network" ? { customer_id: ui.$("#cust").value } : undefined;
      ui.autoTable(ui.$("#result"), await api.get(`/api/reports/${key}`, params), "No rows for this report.");
    } catch (err) { ui.message(msg, err.message); }
  }
  ui.$("#report-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
  run();
})();

(async function () {
  const box = ui.$("#form-error");
  const email = ui.$("#email");

  try {
    const cfg = await api.get("/api/auth/config");
    if (cfg.docs) ui.$("#docs-link").hidden = false;
    if (cfg.demoLogins) {
      ui.$("#demo").hidden = false;
      for (const [addr, role] of [["divya@courier.com", "Staff"], ["naveen@courier.com", "Staff"], ["karthik@courier.com", "Staff"],
                                  ["arun@example.com", "Customer"], ["priya@example.com", "Customer"],
                                  ["rahul@example.com", "Customer"], ["meera@example.com", "Customer"]]) {
        ui.$("#samples").append(ui.el("button", { type: "button", class: "chip", onclick: () => { email.value = addr; ui.$("#login-form").requestSubmit(); } }, `${addr} (${role})`));
      }
    }
  } catch (e) { /* the form still works without the optional hints */ }

  ui.$("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    ui.formError(box, "");
    if (!ui.check([[email, (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? null : "Enter your email address."]])) return;
    try {
      await api.post("/api/auth/login", { email: email.value });
      const next = ui.qs("next");
      location.href = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
    } catch (err) {
      ui.formError(box, err.status === 401 ? "No account with that email." : err.message);
    }
  });
})();

(async function () {
  ui.$("#go-back").addEventListener("click", () => { if (history.length > 1) history.back(); else location.href = "/"; });
  try {
    const me = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (me.ok) {                               // signed in: show the normal navigation so they can move on
      await Layout.boot();
      const plain = ui.$(".site-header.minimal");
      if (plain) plain.remove();
    }
  } catch (e) { /* stay with the plain header */ }
})();

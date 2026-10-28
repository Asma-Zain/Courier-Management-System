/* One fetch wrapper for the whole app. */
class ApiError extends Error {
  constructor(status, message, data) { super(message); this.status = status; this.data = data || {}; this.code = this.data.code; }
}

const api = {
  async call(method, path, body) {
    const opts = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(path, opts);
    } catch (e) {
      throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
    }
    if (res.status === 401 && path !== "/api/auth/login") {
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
      throw new ApiError(401, "Please log in.");
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw new ApiError(res.status, (data && data.detail) || `Request failed (${res.status}).`, data);
    return data;
  },
  get(path, params) {
    const clean = Object.fromEntries(Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ""));
    const q = Object.keys(clean).length ? "?" + new URLSearchParams(clean).toString() : "";
    return this.call("GET", path + q);
  },
  post(path, body) { return this.call("POST", path, body === undefined ? {} : body); },
  patch(path, body) { return this.call("PATCH", path, body); },
  del(path) { return this.call("DELETE", path); },
};

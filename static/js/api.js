/* One fetch wrapper for the whole app. */
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
      throw new ApiError(0, "Cannot reach the server.");
    }
    if (res.status === 401 && !location.pathname.endsWith("login.html") && path !== "/api/auth/login") {
      location.href = "/login.html";
      throw new ApiError(401, "Please log in.");
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw new ApiError(res.status, (data && data.detail) || `Request failed (${res.status}).`);
    return data;
  },
  get(path, params) {
    const q = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.call("GET", path + q);
  },
  post(path, body) { return this.call("POST", path, body === undefined ? {} : body); },
  patch(path, body) { return this.call("PATCH", path, body); },
  del(path) { return this.call("DELETE", path); },
};

class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

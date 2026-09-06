const API = {
  async request(path, options = {}) {
    const headers = Object.assign({ "X-User": "analyst" }, options.headers || {});
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, { ...options, headers });
    const isJson = (response.headers.get("content-type") || "").includes("application/json");
    const payload = isJson ? await response.json() : await response.blob();
    if (!response.ok) {
      const message = payload?.error?.message || "Request failed";
      const error = new Error(message);
      error.payload = payload;
      throw error;
    }
    return payload;
  },
  get(path) {
    return this.request(path);
  },
  post(path, body) {
    return this.request(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body) });
  },
  patch(path, body) {
    return this.request(path, { method: "PATCH", body: JSON.stringify(body) });
  },
  delete(path) {
    return this.request(path, { method: "DELETE" });
  },
  qs(params) {
    const search = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") search.set(key, value);
    });
    const text = search.toString();
    return text ? `?${text}` : "";
  },
  download(path) {
    window.location.href = path;
  },
};

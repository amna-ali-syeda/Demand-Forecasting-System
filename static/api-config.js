window.API_CONFIG = {
  BASE_URL: "http://localhost:5008"
};

window.resolveApiUrl = function resolveApiUrl(endpoint) {
  const base = String(window.API_CONFIG.BASE_URL || "").replace(/\/$/, "");
  const path = String(endpoint || "");

  if (!base) return path;
  if (/^https?:\/\//i.test(path)) return path;

  return base + (path.startsWith("/") ? path : "/" + path);
};

window.apiFetch = function apiFetch(endpoint, options) {
  return fetch(window.resolveApiUrl(endpoint), options);
};

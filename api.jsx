// Lightweight backend API bridge for the prototype frontend.
const VT_API_BASE = localStorage.getItem("vt_api_base") || "http://127.0.0.1:8000";

function vtAuthHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function vtRequest(path, { method = "GET", token, body } = {}) {
  const res = await fetch(`${VT_API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...vtAuthHeaders(token),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error?.message || data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

const VT_API = {
  base: VT_API_BASE,

  async signup(payload) {
    return vtRequest("/v1/auth/signup", { method: "POST", body: payload });
  },

  async login(payload) {
    return vtRequest("/v1/auth/login", { method: "POST", body: payload });
  },

  async refresh(refreshToken) {
    return vtRequest("/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
  },

  async createJob(token, payload) {
    return vtRequest("/v1/jobs", { method: "POST", token, body: payload });
  },

  async getJobEvents(token, jobId) {
    return vtRequest(`/v1/jobs/${jobId}/events`, { method: "GET", token });
  },
};

window.VT_API = VT_API;

const { useState: useStateApi, useEffect: useEffectApi, useMemo: useMemoApi, useCallback: useCallbackApi } = React;

function getApiBase() {
  if (window.VT_API_BASE) return window.VT_API_BASE;
  const fromStorage = localStorage.getItem("vt_api_base");
  if (fromStorage) return fromStorage;
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return window.location.origin;
}

const VT_API_BASE = getApiBase();

async function request(path, init) {
  const controller = new AbortController();
  const timeoutMs = Number(localStorage.getItem("vt_api_timeout_ms") || 30000);
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${VT_API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      ...init,
      signal: controller.signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error(`API timeout after ${timeoutMs}ms at ${VT_API_BASE}`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const payload = await res.json();
      detail = payload?.detail || payload?.message || detail;
    } catch (err) {
      // Keep generic detail when body is not JSON.
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

const Api = {
  base: VT_API_BASE,
  getClients: () => request("/v1/clients"),
  getJobs: () => request("/v1/jobs"),
  getJob: (jobId) => request(`/v1/jobs/${jobId}`),
  getEvents: (jobId) => request(`/v1/jobs/${jobId}/events`),
  getJobClips: (jobId) => request(`/v1/jobs/${jobId}/clips`),
  getClientAssets: (clientSlug) => request(`/v1/clients/${clientSlug}/assets`),
  uploadClientAsset: async (clientSlug, assetType, file) => {
    const form = new FormData();
    form.append("asset_type", assetType);
    form.append("file", file);
    const controller = new AbortController();
    const timeoutMs = Number(localStorage.getItem("vt_api_timeout_ms") || 30000);
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${VT_API_BASE}/v1/clients/${clientSlug}/assets/upload`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const payload = await res.json();
          detail = payload?.detail || payload?.message || detail;
        } catch (err) {}
        throw new Error(detail);
      }
      return res.json();
    } catch (err) {
      if (err?.name === "AbortError") {
        throw new Error(`API timeout after ${timeoutMs}ms at ${VT_API_BASE}`);
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  },
  deleteClientAsset: async (clientSlug, assetType, fileName = "") => {
    const params = new URLSearchParams({ asset_type: assetType });
    if (fileName) params.set("file_name", fileName);
    return request(`/v1/clients/${clientSlug}/assets?${params.toString()}`, { method: "DELETE" });
  },
  createJob: (payload) =>
    request("/v1/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveClip: (jobId, approved, note = "") =>
    request(`/v1/jobs/${jobId}/approval`, {
      method: "POST",
      body: JSON.stringify({ approved, note }),
    }),
  regenerateClip1: (jobId) =>
    request(`/v1/jobs/${jobId}/regenerate-clip-1`, {
      method: "POST",
    }),
  stopJob: (jobId) =>
    request(`/v1/jobs/${jobId}/stop`, {
      method: "POST",
    }),
  assembleJob: (jobId, endCardId = null) =>
    request(`/v1/jobs/${jobId}/assemble`, {
      method: "POST",
      body: JSON.stringify({ end_card_id: endCardId }),
    }),
};

function normalizeClient(client, fallback = {}) {
  return { ...fallback, ...client };
}

function normalizeJob(job) {
  return {
    ...job,
    createdAt: job.createdAt || job.created_at || "just now",
    template: job.template || "Custom / Freeform",
    cost: Number(job.cost || 0),
    costProjected: Number(job.costProjected || 0),
    clipsDone: Number(job.clipsDone || 0),
    clipsTotal: Number(job.clipsTotal || 2),
    thumb: job.thumb || "#9B5CF6",
  };
}

function useOperatorData(pollMs = 5000) {
  const [clients, setClients] = useStateApi(() => window.CLIENTS || []);
  const [jobs, setJobs] = useStateApi(() => window.JOBS || []);
  const [loading, setLoading] = useStateApi(true);
  const [error, setError] = useStateApi(null);
  const [connected, setConnected] = useStateApi(false);
  const [creatingJob, setCreatingJob] = useStateApi(false);
  const [actingOnJob, setActingOnJob] = useStateApi(false);

  const refresh = useCallbackApi(async () => {
    try {
      const [nextClients, nextJobs] = await Promise.all([Api.getClients(), Api.getJobs()]);
      const fallbackBySlug = new Map((window.CLIENTS || []).map((c) => [c.slug, c]));
      setClients(nextClients.map((c) => normalizeClient(c, fallbackBySlug.get(c.slug) || {})));
      setJobs(nextJobs.map(normalizeJob));
      setConnected(true);
      setError(null);
    } catch (err) {
      setConnected(false);
      setError(err.message || "Failed to connect to API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffectApi(() => {
    refresh();
    if (!pollMs || pollMs <= 0) return undefined;
    const id = setInterval(refresh, pollMs);
    return () => clearInterval(id);
  }, [pollMs, refresh]);

  const createJob = useCallbackApi(async (payload) => {
    setCreatingJob(true);
    try {
      const job = normalizeJob(await Api.createJob(payload));
      setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)]);
      setConnected(true);
      return job;
    } finally {
      setCreatingJob(false);
    }
  }, []);

  const approveJob = useCallbackApi(async (jobId, approved, note = "") => {
    setActingOnJob(true);
    try {
      const updated = normalizeJob(await Api.approveClip(jobId, approved, note));
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
      setConnected(true);
      return updated;
    } finally {
      setActingOnJob(false);
    }
  }, []);

  const regenerateClip1 = useCallbackApi(async (jobId) => {
    setActingOnJob(true);
    try {
      const updated = normalizeJob(await Api.regenerateClip1(jobId));
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
      setConnected(true);
      return updated;
    } finally {
      setActingOnJob(false);
    }
  }, []);

  const stopJob = useCallbackApi(async (jobId) => {
    setActingOnJob(true);
    try {
      const updated = normalizeJob(await Api.stopJob(jobId));
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
      setConnected(true);
      return updated;
    } finally {
      setActingOnJob(false);
    }
  }, []);

  const assembleJob = useCallbackApi(async (jobId, endCardId = null) => {
    setActingOnJob(true);
    try {
      const updated = normalizeJob(await Api.assembleJob(jobId, endCardId));
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
      setConnected(true);
      return updated;
    } finally {
      setActingOnJob(false);
    }
  }, []);

  const value = useMemoApi(
    () => ({
      clients,
      jobs,
      loading,
      error,
      connected,
      creatingJob,
      actingOnJob,
      refresh,
      createJob,
      approveJob,
      regenerateClip1,
      stopJob,
      assembleJob,
      fetchJob: Api.getJob,
      fetchEvents: Api.getEvents,
      fetchJobClips: Api.getJobClips,
      apiBase: Api.base,
    }),
    [clients, jobs, loading, error, connected, creatingJob, actingOnJob, refresh, createJob, approveJob, regenerateClip1, stopJob, assembleJob]
  );

  return value;
}

Object.assign(window, { VTApi: { Api, useOperatorData } });

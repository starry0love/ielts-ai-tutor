const API_PORT = window.location.protocol === "file:" ? 18765 : 8000;
const API_BASE = `http://127.0.0.1:${API_PORT}/api`;
const BACKEND_RECOVERY_TIMEOUT_MS = 8000;
const BACKEND_RETRY_INTERVAL_MS = 400;

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });
  } catch (error) {
    error.isNetworkError = true;
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`请求失败：${response.status}`);
    error.status = response.status;
    try {
      error.body = await response.text();
    } catch {
      error.body = "";
    }
    throw error;
  }

  return response.json();
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function waitForBackend(timeoutMs = BACKEND_RECOVERY_TIMEOUT_MS) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
      if (response.ok) {
        return true;
      }
    } catch {
      // Packaged backend may still be starting.
    }
    await delay(BACKEND_RETRY_INTERVAL_MS);
  }
  return false;
}

async function withFallback(remoteCall, fallbackCall) {
  try {
    return await remoteCall();
  } catch (error) {
    if (error.status) {
      throw error;
    }
    if (await waitForBackend()) {
      try {
        return await remoteCall();
      } catch (retryError) {
        if (retryError.status) {
          throw retryError;
        }
      }
    }
    throw new Error("本地学习服务没有启动成功，请重新打开应用。");
  }
}

export const api = {
  getProfile: () => withFallback(() => request("/profile")),
  updateProfile: (payload) =>
    withFallback(
      () => request("/profile", { method: "PUT", body: JSON.stringify(payload) })
    ),
  getAiStatus: () => withFallback(() => request("/profile/ai-status")),
  updateAiConfig: (payload) =>
    withFallback(
      () => request("/profile/ai-config", { method: "PUT", body: JSON.stringify(payload) })
    ),
  testAiConfig: (payload) =>
    withFallback(
      () => request("/profile/ai-test", { method: "POST", body: JSON.stringify(payload) })
    ),

  getTodayPlan: () => withFallback(() => request("/plans/today")),
  generatePlan: () =>
    withFallback(
      () => request("/plans/generate", { method: "POST" })
    ),
  getPlanDiscussion: () =>
    withFallback(
      () => request("/plans/discussion", { method: "POST" })
    ),
  regeneratePlan: (payload) =>
    withFallback(
      () => request("/plans/regenerate", { method: "POST", body: JSON.stringify(payload) })
    ),
  updateTask: (taskId, payload) =>
    withFallback(
      () => request(`/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(payload) })
    ),

  reviewWriting: (payload) =>
    withFallback(
      () => request("/writing/review", { method: "POST", body: JSON.stringify(payload) })
    ),
  listWritingHistory: () => withFallback(() => request("/writing/history")),

  submitDailyReview: (payload) =>
    withFallback(
      () => request("/reviews/daily", { method: "POST", body: JSON.stringify(payload) })
    ),
  listRecentReviews: () => withFallback(() => request("/reviews/recent")),

  getProgress: () => withFallback(() => request("/progress/summary")),
  getReports: () => withFallback(() => request("/reports/summary")),

  getDimensions: () => withFallback(() => request("/mentor/dimensions"))
};


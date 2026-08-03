/* Cliente API con resolución de backend configurable y respaldo local si no hay conexión. */
const RadarAPI = (() => {
  function backendBase() {
    const configured = document.getElementById("backendUrl")?.value?.trim();
    return configured ? configured.replace(/\/$/, "") : "/api";
  }

  async function getJSON(path, params = {}) {
    const base = backendBase();
    const url = new URL(base + path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
    const response = await fetch(url.toString(), { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status} en ${path}`);
    return response.json();
  }

  async function getDashboard(country, periodDays) {
    return getJSON("/dashboard", { country, period_days: periodDays });
  }

  async function getHistory(symbol, periodDays) {
    return getJSON(`/markets/history/${encodeURIComponent(symbol)}`, { period_days: periodDays });
  }

  async function getLocalDemoFallback() {
    const response = await fetch("/static/data/demo_dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Respaldo local no disponible");
    return response.json();
  }

  return { getDashboard, getHistory, getLocalDemoFallback, backendBase };
})();

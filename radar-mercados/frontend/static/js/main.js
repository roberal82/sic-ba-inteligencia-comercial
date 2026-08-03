/* Orquestación del panel: carga de datos, filtros, renderizado y auto-actualización. */
(() => {
  const KPI_SYMBOLS = ["IBOV", "IBVPASA", "MERV", "USDBRL", "USDPYG", "USDARS_OFICIAL", "RIESGO_PAIS", "SELIC", "TPM", "GOLD", "BRENT", "BTC", "VIX", "US10Y"];
  const COUNTRY_SUMMARIES = {
    regional: "Visión comparada: Brasil aporta profundidad de mercado, Paraguay estabilidad relativa con menor liquidez bursátil, y Argentina mayor volatilidad y potencial táctico.",
    brasil: "Brasil mantiene la mayor profundidad bursátil de la región. Energía, bancos y materias primas dominan el índice. Selic y el real son los factores de mayor sensibilidad.",
    paraguay: "Paraguay presenta menor liquidez bursátil pero estabilidad macroeconómica relativa. Prioriza renta fija, tipo de cambio, agronegocios e infraestructura.",
    argentina: "Argentina ofrece mayor volatilidad y potencial táctico. Riesgo país, brecha cambiaria, regulación y liquidez siguen siendo variables críticas.",
    global: "El entorno global combina renta variable firme con riesgos geopolíticos en energía y transporte. Tasas largas, dólar, petróleo y oro son indicadores de control.",
  };

  let currentCountry = "regional";
  let currentPeriod = 7;
  let autoRefreshTimer = null;
  let lastDashboard = null;

  function setStatus(text, kind) {
    const dot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    if (dot) dot.className = `dot ${kind === "warn" ? "warn" : kind === "err" ? "err" : ""}`;
    if (statusText) statusText.textContent = text;
  }

  function renderEventsTable(events) {
    const body = document.getElementById("eventsBody");
    if (!body) return;
    body.innerHTML = events
      .slice(0, 30)
      .map(
        (e) => `<tr>
        <td>${e.title}</td>
        <td>${e.region || e.country}</td>
        <td>${(e.sectors_affected || []).join(", ") || "s/d"}</td>
        <td>${(e.assets_affected || []).join(", ") || "s/d"}</td>
        <td><span class="badge ${e.severity}">${e.severity === "high" ? "ALTO" : e.severity === "medium" ? "MEDIO" : "BAJO"}</span></td>
        <td>${e.source_url ? `<a href="${e.source_url}" target="_blank" rel="noopener">${e.source}</a>` : e.source}</td>
      </tr>`
      )
      .join("");
  }

  function renderAnalysis(analysisList) {
    const container = document.getElementById("analysis");
    if (!container) return;
    container.innerHTML = analysisList
      .map(
        (a) => `<div class="analysis-box">
        <strong>${a.title}</strong>
        <p>${a.summary}</p>
        ${a.positive_factors?.length ? `<div><b>Factores positivos:</b> ${a.positive_factors.join(", ")}</div>` : ""}
        ${a.negative_factors?.length ? `<div><b>Factores negativos:</b> ${a.negative_factors.join(", ")}</div>` : ""}
        ${a.risks?.length ? `<div><b>Riesgos:</b> ${a.risks.join(", ")}</div>` : ""}
        <div class="tag-row"><span class="tag">Horizonte: ${a.time_horizon}</span><span class="tag">Confianza: ${Math.round((a.confidence || 0) * 100)}%</span></div>
        <div class="disclaimer">${a.disclaimer || ""}</div>
      </div>`
      )
      .join("");
  }

  function renderSources(sources) {
    const body = document.getElementById("sourcesBody");
    if (!body) return;
    body.innerHTML = sources
      .map(
        (s) => `<tr><td>${s.name}</td><td>${s.country}</td><td>${s.category}</td>
        <td><span class="badge status-${s.status}">${s.status.replace("_", " ")}</span></td><td>${s.notes}</td></tr>`
      )
      .join("");
  }

  function renderRiskSemaphore(indicators) {
    const container = document.getElementById("riskSemaphore");
    if (!container) return;
    const countries = ["brasil", "paraguay", "argentina"];
    container.innerHTML = countries
      .map((c) => {
        const r = RadarCharts.riskComponents(indicators, c);
        const avg = (r.politico + r.volatilidadFx + r.liquidez + r.inflacion + r.riesgoExterno) / 5;
        const level = avg > 55 ? "high" : avg > 32 ? "medium" : "low";
        return `<div class="metric-row"><span class="metric-name">${c[0].toUpperCase() + c.slice(1)}</span>
          <span class="badge ${level}">${level === "high" ? "ALTO" : level === "medium" ? "MEDIO" : "BAJO"}</span></div>`;
      })
      .join("");
  }

  function renderCountrySummary(country) {
    const container = document.getElementById("countrySummary");
    if (!container) return;
    container.innerHTML = `<div class="analysis-box"><strong>${country[0].toUpperCase() + country.slice(1)}</strong><p>${COUNTRY_SUMMARIES[country] || ""}</p></div>`;
  }

  async function loadScenarioProfile(profile) {
    try {
      const scenarios = await fetch(`${RadarAPI.backendBase()}/scenarios`).then((r) => r.json());
      const chosen = scenarios.find((s) => s.profile === profile) || scenarios[0];
      RadarCharts.renderAllocationChart(chosen);
    } catch (err) {
      console.warn("No se pudieron cargar los escenarios:", err);
    }
  }

  /** Ejecuta una seccion de renderizado de forma aislada: si una falla (por ejemplo, una
   * libreria de graficos no disponible), el resto del panel sigue funcionando. */
  function safe(label, fn) {
    try {
      const result = fn();
      if (result && typeof result.catch === "function") {
        result.catch((err) => console.warn(`Fallo no bloqueante en "${label}":`, err));
      }
    } catch (err) {
      console.warn(`Fallo no bloqueante en "${label}":`, err);
    }
  }

  async function renderAll(dashboard) {
    lastDashboard = dashboard;
    const modeBadge = document.getElementById("modeBadge");
    if (modeBadge) {
      modeBadge.textContent = dashboard.mode === "demo" ? "MODO DEMO" : "PRODUCCIÓN";
      modeBadge.className = `badge-mode ${dashboard.mode}`;
    }
    document.getElementById("updatedText").textContent = `Actualizado: ${new Date(dashboard.generated_at).toLocaleString("es-PY")}`;
    document.getElementById("apiText").textContent = `API: ${RadarAPI.backendBase()}`;

    safe("kpis", () => RadarCharts.renderKPIs(dashboard.indicators, KPI_SYMBOLS));
    safe("perfChart", () => RadarCharts.renderPerfChart(dashboard.indicators));
    safe("fxChart", () => RadarCharts.renderFxChart(dashboard.indicators));
    safe("ratesChart", () => RadarCharts.renderRatesChart(dashboard.indicators));
    safe("riskRadar", () => RadarCharts.renderRiskRadar(dashboard.indicators));
    safe("commoditiesChart", () => RadarCharts.renderCommoditiesChart(dashboard.indicators));
    safe("btcNasdaqChart", () => RadarCharts.renderBtcNasdaqChart(dashboard.indicators));
    safe("heatmap", () => RadarCharts.renderHeatmap(dashboard.indicators));
    safe("countryDistChart", () => RadarCharts.renderCountryDistChart(dashboard.indicators));
    safe("assetDistChart", () => RadarCharts.renderAssetDistChart(dashboard.indicators));
    safe("volatility", () => RadarCharts.renderVolatility(dashboard.indicators));
    safe("correlation", () => RadarCharts.renderCorrelationPlaceholder());
    safe("macroTable", () => RadarCharts.renderMacroTable(dashboard.indicators));
    safe("goldDxyChart", () =>
      RadarCharts.renderHistoryLine("goldDxyChart", "goldDxyContainer", [
        { symbol: "GOLD", label: "Oro" }, { symbol: "DXY", label: "Índice dólar (DXY)" },
      ], currentPeriod)
    );
    safe("oilChart", () =>
      RadarCharts.renderHistoryLine("oilChart", "oilEventsContainer", [
        { symbol: "BRENT", label: "Brent" }, { symbol: "WTI", label: "WTI" },
      ], currentPeriod)
    );

    safe("eventsTable", () => renderEventsTable(dashboard.events));
    safe("analysis", () => renderAnalysis(dashboard.analysis));
    safe("sources", () => renderSources(dashboard.sources));
    safe("riskSemaphore", () => renderRiskSemaphore(dashboard.indicators));
    safe("countrySummary", () => renderCountrySummary(currentCountry === "regional" ? "regional" : currentCountry));
    safe("map", () => RadarMap.setEvents(dashboard.events));

    const profile = document.getElementById("scenarioProfile")?.value || "moderado";
    safe("scenario", () => loadScenarioProfile(profile));
    safe("exportButtons", () => RadarExport.wireButtons(RadarCharts.chartRegistry));
  }

  async function loadDashboard() {
    setStatus("Actualizando…");
    try {
      const dashboard = await RadarAPI.getDashboard(currentCountry, currentPeriod);
      await renderAll(dashboard);
      setStatus(dashboard.mode === "demo" ? "Panel operativo — modo demo (datos ilustrativos)" : "Panel operativo — datos en vivo con respaldo automático");
    } catch (err) {
      console.warn("Fallo al conectar con la API, usando respaldo local:", err);
      try {
        const local = await RadarAPI.getLocalDemoFallback();
        await renderAll(local);
        setStatus("Sin conexión al backend: usando respaldo local de demostración", "warn");
      } catch (err2) {
        setStatus("No se pudo cargar el panel ni el respaldo local", "err");
        console.error(err2);
      }
    }
  }

  function wireControls() {
    document.querySelectorAll(".country-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".country-tab").forEach((x) => x.classList.remove("active"));
        btn.classList.add("active");
        currentCountry = btn.dataset.country;
        renderCountrySummary(currentCountry);
        loadDashboard();
      });
    });

    document.getElementById("period")?.addEventListener("change", (e) => {
      currentPeriod = Number(e.target.value);
      loadDashboard();
    });

    document.getElementById("refreshBtn")?.addEventListener("click", loadDashboard);

    document.getElementById("scenarioProfile")?.addEventListener("change", (e) => loadScenarioProfile(e.target.value));

    document.getElementById("exportEventsCsv")?.addEventListener("click", () => {
      if (!lastDashboard) return;
      const rows = [["title", "region", "severity", "sectors", "assets", "source", "published_at"]];
      lastDashboard.events.forEach((e) =>
        rows.push([e.title, e.region, e.severity, (e.sectors_affected || []).join("; "), (e.assets_affected || []).join("; "), e.source, e.published_at])
      );
      RadarExport.downloadCSV("eventos.csv", rows);
    });

    document.getElementById("refreshMinutes")?.addEventListener("change", (e) => {
      const minutes = Number(e.target.value) || 15;
      if (autoRefreshTimer) clearInterval(autoRefreshTimer);
      autoRefreshTimer = setInterval(loadDashboard, minutes * 60 * 1000);
    });

    RadarMap.wireFilters(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireControls();
    loadDashboard();
    autoRefreshTimer = setInterval(loadDashboard, 15 * 60 * 1000);
  });
})();

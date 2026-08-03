/* Construcción de todos los gráficos del panel a partir de datos reales/demo del backend. */
const RadarCharts = (() => {
  const chartRegistry = {};
  const palette = ["#4ca4ff", "#f0a535", "#26c281", "#ff6472", "#f1cf59", "#9b8cff", "#5fd3d9"];

  function makeChart(id, type, data, options = {}) {
    const el = document.getElementById(id);
    if (!el) return null;
    if (chartRegistry[id]) chartRegistry[id].destroy();
    chartRegistry[id] = new Chart(el, {
      type,
      data,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: "#dce5ed", boxWidth: 12 } }, tooltip: { mode: "index", intersect: false } },
        scales: type === "doughnut" || type === "radar" ? {} : {
          x: { ticks: { color: "#a9b5c0" }, grid: { color: "#1b2c3c" } },
          y: { ticks: { color: "#91a0af" }, grid: { color: "#1b2c3c" } },
        },
        ...options,
      },
    });
    return chartRegistry[id];
  }

  function statusChipClass(status) {
    return `status-${status || "demo"}`;
  }

  function fmt(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(value)) return "—";
    return Number(value).toLocaleString("es-PY", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  }

  const KPI_LABELS = {
    IBOV: "Ibovespa", IBVPASA: "BVPASA", MERV: "S&P Merval", USDBRL: "USD/BRL", USDPYG: "USD/PYG",
    USDARS_OFICIAL: "USD/ARS oficial", RIESGO_PAIS: "Riesgo país (AR)", SELIC: "Tasa Selic", TPM: "Tasa BCP",
    GOLD: "Oro", BRENT: "Brent", BTC: "Bitcoin", VIX: "VIX", US10Y: "Treasury 10Y",
  };

  function renderKPIs(indicators, symbols) {
    const container = document.getElementById("kpis");
    if (!container) return;
    const bySymbol = Object.fromEntries(indicators.map((i) => [i.symbol, i]));
    container.innerHTML = symbols
      .map((symbol) => {
        const item = bySymbol[symbol];
        if (!item) return "";
        const dir = (item.change_percent || 0) > 0 ? "up" : (item.change_percent || 0) < 0 ? "down" : "neutral";
        return `<div class="kpi">
          <div class="label">${KPI_LABELS[symbol] || item.name}</div>
          <div class="value ${dir}">${fmt(item.value)} ${item.unit || item.currency || ""}</div>
          <div class="delta ${dir}">${item.change_percent != null ? (item.change_percent > 0 ? "+" : "") + fmt(item.change_percent) + "%" : "s/d"}</div>
          <span class="status-chip ${statusChipClass(item.data_status)}">${item.data_status}</span>
        </div>`;
      })
      .join("");
  }

  function renderPerfChart(indicators) {
    const symbols = ["IBOV", "IBVPASA", "MERV", "SPX"];
    const items = symbols.map((s) => indicators.find((i) => i.symbol === s)).filter(Boolean);
    makeChart(
      "perfChart", "bar",
      {
        labels: items.map((i) => i.name),
        datasets: [{ label: "Variación de la sesión (%)", data: items.map((i) => i.change_percent ?? 0),
          backgroundColor: items.map((i) => ((i.change_percent || 0) >= 0 ? "rgba(38,194,129,.72)" : "rgba(255,100,114,.72)")) }],
      },
      { plugins: { legend: { display: false } } }
    );
    const meta = document.getElementById("perfMeta");
    if (meta) meta.textContent = items.map((i) => `${i.name}: ${i.source}`).join(" · ");
  }

  function renderFxChart(indicators) {
    const symbols = ["USDBRL", "USDPYG", "USDARS_OFICIAL", "USDARS_MEP", "USDARS_CCL"];
    const items = symbols.map((s) => indicators.find((i) => i.symbol === s)).filter(Boolean);
    makeChart(
      "fxChart", "bar",
      { labels: items.map((i) => i.name), datasets: [{ label: "Valor actual", data: items.map((i) => i.value), backgroundColor: palette[0] }] },
      { plugins: { legend: { display: false } } }
    );
  }

  function renderRatesChart(indicators) {
    const rateSymbols = { brasil: "SELIC", paraguay: "TPM", argentina: "TASA_REF" };
    const inflationSymbols = { brasil: "IPCA", paraguay: "IPC", argentina: "INFLACION" };
    const countries = ["brasil", "paraguay", "argentina"];
    const rates = countries.map((c) => indicators.find((i) => i.symbol === rateSymbols[c])?.value ?? null);
    const inflation = countries.map((c) => indicators.find((i) => i.symbol === inflationSymbols[c])?.value ?? null);
    makeChart("ratesChart", "bar", {
      labels: countries.map((c) => c[0].toUpperCase() + c.slice(1)),
      datasets: [
        { label: "Tasa de referencia (%)", data: rates, backgroundColor: palette[0] },
        { label: "Inflación (%)", data: inflation, backgroundColor: palette[1] },
      ],
    });
  }

  function riskComponents(indicators, country) {
    const riesgoPais = indicators.find((i) => i.symbol === "RIESGO_PAIS")?.value;
    const inflationBySymbol = { brasil: "IPCA", paraguay: "IPC", argentina: "INFLACION" };
    const inflacion = indicators.find((i) => i.symbol === inflationBySymbol[country])?.value ?? 0;
    const fxSymbol = { brasil: "USDBRL", paraguay: "USDPYG", argentina: "USDARS_OFICIAL" }[country];
    const fxVolatility = Math.abs(indicators.find((i) => i.symbol === fxSymbol)?.change_percent ?? 0) * 10;
    const politico = country === "argentina" ? (riesgoPais ? Math.min(100, riesgoPais / 6) : 60) : country === "paraguay" ? 25 : 35;
    return {
      politico,
      volatilidadFx: Math.min(100, fxVolatility),
      liquidez: country === "brasil" ? 25 : country === "paraguay" ? 60 : 45,
      inflacion: Math.min(100, inflacion * 8),
      riesgoExterno: country === "argentina" ? 60 : country === "brasil" ? 50 : 40,
    };
  }

  function renderRiskRadar(indicators) {
    const countries = ["brasil", "paraguay", "argentina"];
    const labels = ["Riesgo político", "Volatilidad FX", "Liquidez", "Inflación", "Riesgo externo"];
    const datasets = countries.map((c, idx) => {
      const r = riskComponents(indicators, c);
      return {
        label: c[0].toUpperCase() + c.slice(1),
        data: [r.politico, r.volatilidadFx, r.liquidez, r.inflacion, r.riesgoExterno],
        borderColor: palette[idx], backgroundColor: palette[idx] + "33",
      };
    });
    makeChart("riskRadar", "radar", { labels, datasets }, {
      scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: "#31475b" }, angleLines: { color: "#31475b" }, pointLabels: { color: "#cbd4dd" } } },
    });
  }

  function renderCommoditiesChart(indicators) {
    const symbols = ["GOLD", "SILVER", "WTI", "BRENT", "COPPER", "SOYBEAN"];
    const items = symbols.map((s) => indicators.find((i) => i.symbol === s)).filter(Boolean);
    makeChart("commoditiesChart", "bar", {
      labels: items.map((i) => i.name),
      datasets: [{ label: "Variación (%)", data: items.map((i) => i.change_percent ?? 0),
        backgroundColor: items.map((i) => ((i.change_percent || 0) >= 0 ? "rgba(76,164,255,.72)" : "rgba(255,100,114,.72)")) }],
    }, { plugins: { legend: { display: false } } });
  }

  function renderBtcNasdaqChart(indicators) {
    const items = [indicators.find((i) => i.symbol === "BTC"), indicators.find((i) => i.symbol === "IXIC")].filter(Boolean);
    makeChart("btcNasdaqChart", "bar", {
      labels: items.map((i) => i.name),
      datasets: [{ label: "Variación de la sesión (%)", data: items.map((i) => i.change_percent ?? 0), backgroundColor: [palette[5], palette[0]] }],
    }, { plugins: { legend: { display: false } } });
  }

  function renderHeatmap(indicators) {
    const categories = [...new Set(indicators.map((i) => i.category))];
    const countries = [...new Set(indicators.map((i) => i.country))];
    const head = document.getElementById("heatmapHead");
    const body = document.getElementById("heatmapBody");
    if (!head || !body) return;
    head.innerHTML = `<th>Categoría \\ País</th>` + countries.map((c) => `<th>${c}</th>`).join("");
    body.innerHTML = categories
      .map((cat) => {
        const cells = countries
          .map((country) => {
            const subset = indicators.filter((i) => i.category === cat && i.country === country);
            if (!subset.length) return `<td style="color:#4b5b6b">—</td>`;
            const avg = subset.reduce((sum, i) => sum + (i.change_percent || 0), 0) / subset.length;
            const color = avg > 0.3 ? "rgba(38,194,129,.35)" : avg < -0.3 ? "rgba(255,100,114,.35)" : "rgba(241,207,89,.22)";
            return `<td style="background:${color}">${avg.toFixed(2)}%</td>`;
          })
          .join("");
        return `<tr><td>${cat}</td>${cells}</tr>`;
      })
      .join("");
  }

  function renderCountryDistChart(indicators) {
    const countries = [...new Set(indicators.map((i) => i.country))];
    const counts = countries.map((c) => indicators.filter((i) => i.country === c).length);
    makeChart("countryDistChart", "doughnut", {
      labels: countries, datasets: [{ data: counts, borderColor: "#0d1722", borderWidth: 3, backgroundColor: palette }],
    }, { plugins: { legend: { position: "bottom", labels: { color: "#dce5ed", boxWidth: 10 } } } });
  }

  function renderAssetDistChart(indicators) {
    const categories = [...new Set(indicators.map((i) => i.category))];
    const counts = categories.map((c) => indicators.filter((i) => i.category === c).length);
    makeChart("assetDistChart", "doughnut", {
      labels: categories, datasets: [{ data: counts, borderColor: "#0d1722", borderWidth: 3, backgroundColor: palette }],
    }, { plugins: { legend: { position: "bottom", labels: { color: "#dce5ed", boxWidth: 10 } } } });
  }

  function renderAllocationChart(scenario) {
    if (!scenario) return;
    const labels = ["Liquidez", "Renta fija", "Oro", "Renta variable global", "Brasil", "Paraguay", "Argentina", "Commodities", "Cripto"];
    const data = [scenario.liquidity, scenario.fixed_income, scenario.gold, scenario.global_equities, scenario.brazil, scenario.paraguay, scenario.argentina, scenario.commodities, scenario.crypto];
    makeChart("allocationChart", "doughnut", {
      labels, datasets: [{ data, borderColor: "#0d1722", borderWidth: 3, backgroundColor: palette.concat(["#e07a5f", "#3d5a80"]) }],
    }, { plugins: { legend: { position: "right", labels: { color: "#dce5ed", boxWidth: 10 } } } });
    const explanation = document.getElementById("scenarioExplanation");
    if (explanation) explanation.textContent = `${scenario.explanation} ${explanation.dataset.disclaimer || ""}`;
  }

  function renderVolatility(indicators) {
    const container = document.getElementById("volatilityContainer");
    if (!container) return;
    const vix = indicators.find((i) => i.symbol === "VIX");
    if (!vix) {
      container.innerHTML = `<div class="empty-state">VIX no disponible en esta consulta.</div>`;
      return;
    }
    const level = vix.value < 15 ? "Baja" : vix.value < 25 ? "Moderada" : "Alta";
    container.innerHTML = `
      <div class="metric-row"><span class="metric-name">VIX actual</span><span class="metric-value">${fmt(vix.value)}</span></div>
      <div class="metric-row"><span class="metric-name">Nivel de volatilidad implícita</span><span class="metric-value">${level}</span></div>
      <div class="metric-row"><span class="metric-name">Fuente</span><span class="metric-value">${vix.source}</span></div>
      <div class="disclaimer">La volatilidad histórica real (desviación estándar de retornos) requiere una serie temporal acumulada por las tareas programadas. Se muestra el VIX en vivo como proxy de referencia mientras se acumula historial.</div>`;
  }

  function renderCorrelationPlaceholder() {
    const container = document.getElementById("correlationContainer");
    if (!container) return;
    container.textContent = "No disponible aún: la matriz de correlación entre activos requiere una serie histórica acumulada (mínimo ~30 puntos por activo). Se habilitará automáticamente a medida que las tareas programadas acumulen datos en /api/markets/history/{symbol}.";
  }

  function renderMacroTable(indicators) {
    const body = document.getElementById("macroBody");
    if (!body) return;
    const macroCategories = ["tasa", "inflacion", "reservas", "riesgo_pais"];
    const rows = indicators.filter((i) => macroCategories.includes(i.category));
    body.innerHTML = rows
      .map((i) => `<tr><td>${i.country}</td><td>${i.name}</td><td>${fmt(i.value)} ${i.unit}</td><td><span class="badge status-${i.data_status}">${i.data_status}</span></td></tr>`)
      .join("");
  }

  async function renderHistoryLine(canvasId, containerId, seriesSpecs, periodDays) {
    const container = document.getElementById(containerId);
    const results = await Promise.all(
      seriesSpecs.map(async (spec) => {
        try {
          const history = await RadarAPI.getHistory(spec.symbol, periodDays);
          return { ...spec, history };
        } catch {
          return { ...spec, history: { points: [], sufficient_history: false } };
        }
      })
    );
    const anySufficient = results.some((r) => r.history.sufficient_history);
    if (!anySufficient) {
      if (container) {
        container.innerHTML = `<div class="empty-state">Historial insuficiente todavía para graficar la evolución temporal. Se acumula automáticamente con cada ejecución de las tareas programadas (cada 15 minutos por defecto). No se muestran cifras inventadas.</div>`;
      }
      return;
    }
    if (container) container.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    const labels = results.find((r) => r.history.sufficient_history).history.points.map((p) => new Date(p.timestamp).toLocaleString("es-PY"));
    makeChart(canvasId, "line", {
      labels,
      datasets: results.map((r, idx) => ({
        label: r.label,
        data: r.history.points.map((p) => p.value),
        borderColor: palette[idx],
        tension: 0.3,
      })),
    });
  }

  return {
    chartRegistry,
    fmt,
    renderKPIs,
    renderPerfChart,
    renderFxChart,
    renderRatesChart,
    renderRiskRadar,
    riskComponents,
    renderCommoditiesChart,
    renderBtcNasdaqChart,
    renderHeatmap,
    renderCountryDistChart,
    renderAssetDistChart,
    renderAllocationChart,
    renderVolatility,
    renderCorrelationPlaceholder,
    renderMacroTable,
    renderHistoryLine,
  };
})();

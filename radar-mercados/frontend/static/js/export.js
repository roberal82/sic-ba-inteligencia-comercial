/* Exportación de gráficos a PNG y de tablas/series a CSV. */
const RadarExport = (() => {
  function chartToPNG(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `${canvasId}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function rowsToCSV(rows) {
    return rows
      .map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(","))
      .join("\n");
  }

  function downloadCSV(filename, rows) {
    const csv = rowsToCSV(rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function chartDataToCSV(canvasId, chartRegistry) {
    const chart = chartRegistry[canvasId];
    if (!chart) return;
    const labels = chart.data.labels || [];
    const rows = [["label", ...chart.data.datasets.map((d) => d.label || "serie")]];
    labels.forEach((label, idx) => {
      rows.push([label, ...chart.data.datasets.map((d) => d.data[idx])]);
    });
    downloadCSV(`${canvasId}.csv`, rows);
  }

  function wireButtons(chartRegistry) {
    document.querySelectorAll("[data-export-png]").forEach((btn) => {
      btn.addEventListener("click", () => chartToPNG(btn.dataset.exportPng));
    });
    document.querySelectorAll("[data-export-csv]").forEach((btn) => {
      btn.addEventListener("click", () => chartDataToCSV(btn.dataset.exportCsv, chartRegistry));
    });
  }

  return { downloadCSV, chartToPNG, wireButtons };
})();

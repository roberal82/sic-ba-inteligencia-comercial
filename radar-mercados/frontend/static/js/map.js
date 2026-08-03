/* Mapa interactivo de eventos geopolíticos con filtros por país, severidad y tipo. */
const RadarMap = (() => {
  let map = null;
  let markers = [];
  let allEvents = [];

  function severityColor(severity) {
    return severity === "high" ? "#ff6472" : severity === "medium" ? "#f1cf59" : "#26c281";
  }

  function init() {
    if (map) return;
    map = L.map("map", { worldCopyJump: true }).setView([-15, -55], 3);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(map);
  }

  function popupHTML(event) {
    const assets = (event.assets_affected || []).join(", ") || "s/d";
    const sectors = (event.sectors_affected || []).join(", ") || "s/d";
    const date = event.published_at ? new Date(event.published_at).toLocaleString("es-PY") : "s/d";
    const link = event.source_url ? `<br><a href="${event.source_url}" target="_blank" rel="noopener">Ver fuente</a>` : "";
    return `<b>${event.title}</b><br>
      <span style="color:#91a0af">${date} · ${event.source}</span><br>
      ${event.summary || ""}<br>
      <b>Severidad:</b> ${event.severity} · <b>Probabilidad:</b> ${Math.round((event.probability || 0) * 100)}%<br>
      <b>Activos:</b> ${assets}<br>
      <b>Sectores:</b> ${sectors}<br>
      <b>Confianza:</b> ${Math.round((event.confidence || 0) * 100)}%${link}`;
  }

  function renderMarkers(events) {
    init();
    markers.forEach((m) => map.removeLayer(m));
    markers = events.map((event) => {
      const color = severityColor(event.severity);
      const marker = L.circleMarker([event.latitude, event.longitude], {
        radius: event.severity === "high" ? 11 : event.severity === "medium" ? 8 : 6,
        color,
        fillColor: color,
        fillOpacity: 0.78,
        weight: 2,
      }).addTo(map);
      marker.bindPopup(popupHTML(event));
      return marker;
    });
  }

  function populateFilterOptions(events) {
    const countrySelect = document.getElementById("filterCountryMap");
    const typeSelect = document.getElementById("filterType");
    if (countrySelect && countrySelect.options.length <= 1) {
      [...new Set(events.map((e) => e.country))].forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c; opt.textContent = c;
        countrySelect.appendChild(opt);
      });
    }
    if (typeSelect && typeSelect.options.length <= 1) {
      [...new Set(events.map((e) => e.event_type))].forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t; opt.textContent = t;
        typeSelect.appendChild(opt);
      });
    }
  }

  function applyFilters() {
    const severity = document.getElementById("filterSeverity")?.value;
    const country = document.getElementById("filterCountryMap")?.value;
    const type = document.getElementById("filterType")?.value;
    let filtered = allEvents;
    if (severity) filtered = filtered.filter((e) => e.severity === severity);
    if (country) filtered = filtered.filter((e) => e.country === country);
    if (type) filtered = filtered.filter((e) => e.event_type === type);
    renderMarkers(filtered);
    return filtered;
  }

  function setEvents(events) {
    allEvents = events;
    populateFilterOptions(events);
    return applyFilters();
  }

  function wireFilters(onChange) {
    ["filterSeverity", "filterCountryMap", "filterType"].forEach((id) => {
      document.getElementById(id)?.addEventListener("change", () => onChange(applyFilters()));
    });
  }

  return { setEvents, wireFilters, applyFilters };
})();

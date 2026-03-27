(function () {
  var fallback = {
    pending_total: 6,
    alerts: [
      { priority: "red", title: "Admin Request Baru", time: "10:41 PM", desc: "User hantar request payment verification dalam Bot Admin. Perlu semakan segera." },
      { priority: "amber", title: "Daftar Webinar", time: "10:39 PM", desc: "Sophia Norezuan daftar S1 - Pelanggan Baru. API PASS." },
      { priority: "blue", title: "eVideo Reminder", time: "10:32 PM", desc: "Intermediate Topik 10 available on 2026-03-10." },
      { priority: "amber", title: "Upcoming Event", time: "10:28 PM", desc: "Webinar FULLFLOW SIRI 1 Sesi 1 bermula 07 Apr 2026 09:00 PM MYT." }
    ],
    queue: [
      { priority: "red", label: "Group Admin", title: "Pending Approval", count: 3, items: ["1 x NEXTexclusive", "1 x eVideo", "1 x webinar"] },
      { priority: "amber", label: "Upcoming Event", title: "Reminder Queue", count: 2, items: ["Webinar FULLFLOW SIRI 1", "eVideo available on 2026-03-10"] }
    ],
    system: {
      pulse: "Stable",
      ram: "1.8 / 7.8 GB",
      storage: "19 / 145 GB",
      services: [
        { name: "mmhelper-sidebot", status: "active", dot: "green" },
        { name: "mmhelper-video-bot", status: "active", dot: "green" },
        { name: "next-event-bot", status: "active", dot: "green" },
        { name: "AMarkets API", status: "1 warning", dot: "amber" }
      ]
    },
    ticker: [
      { time: "10:41 PM", date: "27 Mar 2026", pill: "Admin", pill_class: "red", text: "Request payment baru diterima dari ReezoAdmin_Bot." },
      { time: "10:39 PM", date: "27 Mar 2026", pill: "Webinar", pill_class: "amber", text: "Sophia Norezuan daftar Webinar FULLFLOW SIRI 1." },
      { time: "10:32 PM", date: "27 Mar 2026", pill: "eVideo", pill_class: "blue", text: "Intermediate topik 10 available on 2026-03-10." },
      { time: "10:28 PM", date: "27 Mar 2026", pill: "Event", pill_class: "green", text: "Webinar FULLFLOW SIRI 1 pada 07 Apr 2026 09:00 PM MYT." }
    ]
  };

  function apiUrl() {
    var params = new URLSearchParams(window.location.search || "");
    var explicit = params.get("opsApi");
    if (explicit) return explicit;
    if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
      return "http://127.0.0.1:8765/api/ops-hud";
    }
    return "/api/ops-hud";
  }

  function cardHtml(item) {
    return (
      '<article class="alert-card priority-' + escapeHtml(item.priority || "blue") + '">' +
      '<div class="card-top">' +
      '<h3 class="card-title">' + escapeHtml(item.title || "-") + '</h3>' +
      '<span class="card-time">' + escapeHtml(item.time || "-") + '</span>' +
      '</div>' +
      '<div class="card-desc">' + escapeHtml(item.desc || "-") + '</div>' +
      '</article>'
    );
  }

  function queueHtml(item) {
    var items = Array.isArray(item.items) ? item.items : [];
    return (
      '<article class="queue-card priority-' + escapeHtml(item.priority || "blue") + '">' +
      '<div class="queue-metric">' +
      '<div><div class="metric-label">' + escapeHtml(item.label || "-") + '</div>' +
      '<div class="card-title">' + escapeHtml(item.title || "-") + '</div></div>' +
      '<strong>' + escapeHtml(String(item.count || 0)) + '</strong>' +
      '</div>' +
      '<ul class="queue-list">' + items.map(function (row) { return "<li>" + escapeHtml(row) + "</li>"; }).join("") + '</ul>' +
      '</article>'
    );
  }

  function serviceHtml(item) {
    return (
      '<div class="status-row">' +
      '<span class="dot ' + escapeHtml(item.dot || "blue") + '"></span>' +
      '<span>' + escapeHtml(item.name || "-") + '</span>' +
      '<span class="card-tag">' + escapeHtml(item.status || "-") + '</span>' +
      '</div>'
    );
  }

  function tickerHtml(item) {
    return (
      '<span class="ticker-item">' +
      '<span class="ticker-timewrap">' +
      '<span class="ticker-time">' + escapeHtml(item.time || "-") + '</span>' +
      '<span class="ticker-date">' + escapeHtml(item.date || "-") + '</span>' +
      '</span>' +
      '<span class="pill ' + escapeHtml(item.pill_class || "blue") + '">' + escapeHtml(item.pill || "-") + '</span>' +
      '<span>' + escapeHtml(item.text || "-") + '</span>' +
      '</span>'
    );
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function render(data) {
    data = data && typeof data === "object" ? data : fallback;

    var alertsEl = document.getElementById("alertsStack");
    var queueEl = document.getElementById("queueStack");
    var systemPulseEl = document.getElementById("systemPulse");
    var systemPulseSubEl = document.getElementById("systemPulseSub");
    var ramEl = document.getElementById("ramValue");
    var storageEl = document.getElementById("storageValue");
    var servicesEl = document.getElementById("servicesList");
    var tickerEl = document.getElementById("tickerTrack");

    alertsEl.innerHTML = (Array.isArray(data.alerts) ? data.alerts : fallback.alerts).slice(0, 4).map(cardHtml).join("");
    queueEl.innerHTML = (Array.isArray(data.queue) ? data.queue : fallback.queue).slice(0, 2).map(queueHtml).join("");

    var system = data.system || fallback.system;
    systemPulseEl.textContent = system.pulse || fallback.system.pulse;
    systemPulseSubEl.textContent = "Live snapshot from VPS";
    ramEl.textContent = system.ram || fallback.system.ram;
    storageEl.textContent = system.storage || fallback.system.storage;
    servicesEl.innerHTML = (Array.isArray(system.services) ? system.services : fallback.system.services).map(serviceHtml).join("");

    var ticker = Array.isArray(data.ticker) && data.ticker.length ? data.ticker : fallback.ticker;
    var joined = ticker.concat(ticker).map(tickerHtml).join("");
    tickerEl.innerHTML = joined;
  }

  async function load() {
    try {
      var response = await fetch(apiUrl(), { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      var payload = await response.json();
      if (!payload || payload.ok === false) throw new Error(payload && payload.error ? payload.error : "invalid_payload");
      render(payload);
    } catch (err) {
      render(fallback);
    }
  }

  window.MMHUD = { load: load };
  document.addEventListener("DOMContentLoaded", function () {
    load();
    setInterval(load, 60000);
  });
})();

(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var params = new URLSearchParams(window.location.search);
  var statusEl = document.getElementById("formStatus");
  var txListEl = document.getElementById("txList");
  var tab7Btn = document.getElementById("tab7");
  var tab30Btn = document.getElementById("tab30");

  function safeParseArray(value) {
    if (!value) return [];
    try {
      var parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function formatAmount(value) {
    var n = Number(value || 0);
    if (n > 0) {
      return { text: "+USD " + n.toFixed(2), className: "amount-positive" };
    }
    if (n < 0) {
      return { text: "-USD " + Math.abs(n).toFixed(2), className: "amount-negative" };
    }
    return { text: "USD 0.00", className: "" };
  }

  var records7 = safeParseArray(params.get("records_7d"));
  var records30 = safeParseArray(params.get("records_30d"));

  document.getElementById("summaryName").textContent = params.get("name") || "-";
  document.getElementById("summaryDate").textContent = params.get("saved_date") || "-";

  function renderRows(rows) {
    txListEl.innerHTML = "";
    if (!rows.length) {
      var emptyEl = document.createElement("p");
      emptyEl.className = "empty";
      emptyEl.textContent = "Belum ada transaksi untuk tempoh ini.";
      txListEl.appendChild(emptyEl);
      return;
    }

    rows.forEach(function (row) {
      var line = document.createElement("div");
      line.className = "tx-row";

      var dateCell = document.createElement("span");
      dateCell.textContent = (row.date || "-") + " " + (row.time || "-");

      var typeCell = document.createElement("span");
      var sourceBadge = document.createElement("span");
      sourceBadge.className = "source";
      sourceBadge.textContent = row.label || "Transaction";
      typeCell.appendChild(sourceBadge);

      var modeCell = document.createElement("span");
      modeCell.textContent = row.mode ? String(row.mode).replace(/_/g, " ") : "-";

      var amountCell = document.createElement("span");
      var amountView = formatAmount(row.amount_usd);
      amountCell.textContent = amountView.text;
      if (amountView.className) {
        amountCell.classList.add(amountView.className);
      }

      line.appendChild(dateCell);
      line.appendChild(typeCell);
      line.appendChild(modeCell);
      line.appendChild(amountCell);
      txListEl.appendChild(line);
    });
  }

  function setActiveTab(tab) {
    var is7 = tab === "7";
    tab7Btn.classList.toggle("active", is7);
    tab30Btn.classList.toggle("active", !is7);
    renderRows(is7 ? records7 : records30);
  }

  function backToRecordsReports() {
    var payload = { type: "records_reports_back_to_menu" };
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
      return;
    }
    statusEl.textContent = "Preview mode: buka dari Telegram untuk kembali ke menu.";
  }

  tab7Btn.addEventListener("click", function () {
    setActiveTab("7");
  });

  tab30Btn.addEventListener("click", function () {
    setActiveTab("30");
  });

  document.getElementById("topBackBtn").addEventListener("click", backToRecordsReports);
  document.getElementById("backToReportsBtn").addEventListener("click", backToRecordsReports);

  setActiveTab("7");
})();

(function () {
  var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  var tabs = [
    { btn: document.getElementById("tabBasic"), panel: document.getElementById("panelBasic") },
    { btn: document.getElementById("tabIntermediate"), panel: document.getElementById("panelIntermediate") },
    { btn: document.getElementById("tabAdvanced"), panel: document.getElementById("panelAdvanced") },
  ];

  function activate(index) {
    tabs.forEach(function (t, i) {
      var active = i === index;
      t.btn.classList.toggle("active", active);
      t.panel.classList.toggle("active", active);
    });
  }

  tabs.forEach(function (t, i) {
    t.btn.addEventListener("click", function () {
      activate(i);
    });
  });
})();


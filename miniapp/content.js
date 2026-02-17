window.MMHELPER_CONTENT = {
  withdrawalReasons: [
    "Take profit sikit",
    "Emergency / komitmen",
    "Pindah modal ke akaun lain",
    "Simpan sebagai cash reserve"
  ],

  getWithdrawalIntro: function (profitUsdFormatted) {
    return [
      "Berapa kau withdraw tadi?",
      "",
      "Minggu ni flow kau tengah hijau " + profitUsdFormatted + ". Nak ambil untung takde hal, asalkan modal trade kau tak lari dari plan."
    ].join("\n");
  },

  getWithdrawalIntroLoss: function (lossUsdFormatted) {
    return [
      "Berapa kau withdraw tadi?",
      "",
      "Minggu ni akaun tengah merah " + lossUsdFormatted + ". Kalau boleh, jaga dulu flow modal trade kau sebelum withdraw besar-besar."
    ].join("\n");
  },

  withdrawalReasonPrompt: "pilih sebab apa kau withdraw . aku simpan dalam rekod",
  withdrawalAmountPrompt: "Masukkan jumlah yang kau withdraw. jangan salah sebab tak boleh ubah",
  withdrawalFinalPrompt: "Cek semua kalau dah betul , tekan submit",

  depositReasons: [
    "Top up modal trading",
    "Tambah reserve account",
    "Simpan hasil payout",
    "Kumpul modal untuk setup baru"
  ],

  getDepositIntro: function (profitUsdFormatted) {
    return [
      "Berapa kau deposit tadi?",
      "",
      "Minggu ni flow kau tengah hijau " + profitUsdFormatted + ". Kalau nak top up modal, nice. Pastikan jumlah masuk tu memang ikut plan, bukan ikut emosi."
    ].join("\n");
  },

  getDepositIntroLoss: function (lossUsdFormatted) {
    return [
      "Berapa kau deposit tadi?",
      "",
      "Minggu ni akaun tengah merah " + lossUsdFormatted + ". Kalau nak top up boleh, tapi biar untuk stabilkan setup, bukan sebab nak cover rugi laju-laju."
    ].join("\n");
  },

  depositReasonPrompt: "pilih sebab apa kau deposit . aku simpan dalam rekod",
  depositAmountPrompt: "Masukkan jumlah yang kau deposit. check betul-betul sebab tak boleh ubah",
  depositFinalPrompt: "Cek semua kalau dah betul , tekan submit",
  accountActivityBackBtn: "⬅️ Back to Account Activity",

  tradingIntro: [
    "Kita buat cepat tapi tepat.",
    "Profit ke loss, update terus kat sini.",
    "",
    "Lepas pilih mode, kau terus nampak impact kiraan live sebelum submit.",
    "Senang nak double-check, takde main agak-agak."
  ].join("\n"),

  getTradingModePrompt: function (mode) {
    if (mode === "profit") {
      return "Masukkan jumlah profit yang baru kau lock. Kita simpan untuk kiraan seterusnya.";
    }
    return "Masukkan jumlah loss yang kena tadi. Kita rekod terus supaya kiraan tak lari.";
  },

  getTradingAmountPrompt: function (mode) {
    if (mode === "profit") {
      return "Jumlah profit (USD)";
    }
    return "Jumlah loss (USD)";
  },

  getTradingFinalPrompt: function (mode) {
    if (mode === "loss") {
      return [
        "Cek semua kalau dah betul, tekan submit.",
        "",
        "Loss ni waktu paling sesuai untuk kau upgrade skill. Kalau nak naikkan lagi level trading, boleh cari Reezo."
      ].join("\n");
    }

    if (mode === "profit") {
      return [
        "Cek semua kalau dah betul, tekan submit.",
        "",
        "Waktu profit ni kena extra hati-hati, ujian memang banyak. Pastikan duit withdraw kau betul-betul masuk. Kalau nak proses laju dan clear, boleh cuba broker AMarkets."
      ].join("\n");
    }

    return "Cek semua kalau dah betul, tekan submit.";
  },

  setNewGoalIntro: [
    "Project Grow ni bukan sekadar letak angka dan berharap magic jadi.",
    "Kau set sasaran, kita lock tempoh, lepas tu kita jalan ikut plan.",
    "",
    "Lepas ni akan ada Mission khas untuk bantu kau kekal konsisten.",
    "So masa isi goal ni, isi betul-betul ikut target yang kau nak capai."
  ].join("\n"),

  setNewGoalPrompt: "Target Capital (USD) yang kau nak capai",
  setNewGoalBalanceHintPrefix: "Current Balance kau sekarang",
  setNewGoalMinTargetPrefix: "Minimum target yang dibenarkan",
  setNewGoalGrowTargetPrefix: "Grow Target kau adalah",
  setNewGoalCurrentTabungStartPrefix: "Tarikh mula tabung",
  setNewGoalMissionStatusPrefix: "Mission status",
  setNewGoalTargetPrompt: "Target masa untuk capai sasaran",
  setNewGoalUnlockPrompt: "Unlock Mission (minimum USD 10, optional). Jumlah ni akan ditolak terus dari Current Balance bila kau unlock.",
  setNewGoalFinalPrompt: "Bila dah yakin, submit. Lepas ni kita sambung flow mission.",
  setNewGoalBackToMenuBtn: "⬅️ Back to Project Grow",
  setNewGoalResetBtn: "Reset New Goal",
  setNewGoalResetConfirmText: "Reset New Goal sekarang? Semua setting goal dan progress mission akan dipadam.",
  setNewGoalResetInfoText: "Reset ni akan padam Target Capital, grow target, dan progress mission semasa.",
  setNewGoalResetCancelledText: "Reset New Goal dibatalkan.",
  setNewGoalResetPreviewText: "Preview mode: reset hanya berfungsi bila buka dari Telegram.",
  setNewGoalConfiguredTitle: "Target Capital dah diset ✅",
  setNewGoalConfiguredHint: "Kalau nak tukar setup, reset dulu kemudian set semula.",
  setNewGoalReachedIntro: [
    "Nice, target semasa kau dah lepas.",
    "Kau boleh lock momentum ni dan terus set objective baru ikut pace account terkini."
  ].join("\n"),
  setNewGoalReachedTitle: "Goal semasa dah capai 🎯",
  setNewGoalReachedInfoText: "Bila ready, tekan Set New Goal untuk sambung fasa seterusnya tanpa reset flow lama.",
  setNewGoalReachedBtn: "🎯 Set New Goal",

  missionLockedText: "Mission belum boleh dibuka. Set New Goal dulu, kemudian pastikan balance tabung minimum USD 10.",
  missionBeforeStartIntro: [
    "Project Grow datang sekali dengan Mission.",
    "Kau kena maintain prestasi dan disiplin untuk complete mission satu per satu.",
    "",
    "Pilih mode dulu, lepas tu start mission."
  ].join("\n"),
  missionRunningIntro: "Mission tengah berjalan. Fokus maintain consistency sampai complete.",

  missionNormalLabel: "Normal Mode",
  missionAdvancedLabel: "Advanced Mode",
  missionStartNormalBtn: "🚀 Start Mission (Normal)",
  missionStartAdvancedBtn: "🚀 Start Mission (Advanced)",
  missionRunningBadge: "Mission Active",
  missionBackToMenuBtn: "⬅️ Back to Project Grow",
  missionCurrentTabungStartPrefix: "Tarikh mula tabung",
  missionStatusPrefix: "Mission status",
  missionResetConfirmText: "Reset mission sekarang? Progress mission semasa akan dipadam.",
  missionResetCancelledText: "Reset mission dibatalkan.",
  missionResetPreviewText: "Preview mode: reset mission hanya berfungsi bila buka dari Telegram.",

  missionLevel1Title: "Level 1",
  missionLevel2Title: "Level 2 (Akan Datang)",
  missionLevel3Title: "Level 3 (Akan Datang)",

  missionLevel1Items: [
    {
      title: "Mission 1 : Honest Log",
      desc: "Untuk 14 hari berturut, kau wajib update MM Helper setiap hari termasuk hari tak trade. Kalau ada sehari tak update, mission ni jatuh fail."
    },
    {
      title: "Mission 2 : Honest Grow",
      desc: "Selama minimum 14 hari berturut, update aktiviti trading setiap hari termasuk no-trade day, dan dalam tempoh sama pastikan ada sekurang-kurangnya 2 transaksi tabung."
    },
    {
      title: "Mission 3 : Respect Max Loss",
      desc: "Kau kena jaga disiplin supaya tak langgar had daily max loss selama 30 hari berturut. Had ni ikut setting yang kau isi masa Initial Setup."
    },
    {
      title: "Mission 4 : Double UP",
      desc: "Capai pertumbuhan 100% daripada jarak target grow yang kau set masa Set New Goal. Fokus konsisten, bukan pecut tanpa plan."
    }
  ],

  missionLevelComingSoonText: "Bahagian ni kita lock dulu. Nanti kita buka lepas Level 1 settle."
};

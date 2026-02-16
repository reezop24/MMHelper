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

  setNewGoalPrompt: "Target account (USD) yang kau nak capai",
  setNewGoalBalanceHintPrefix: "Baki semasa kau sekarang",
  setNewGoalMinTargetPrefix: "Minimum target yang dibenarkan",
  setNewGoalTargetPrompt: "Target masa untuk capai sasaran",
  setNewGoalUnlockPrompt: "Unlock Mission & Tabung (minimum USD 10)",
  setNewGoalFinalPrompt: "Bila dah yakin, submit. Lepas ni kita sambung flow mission.",

  missionLockedText: "Mission boleh dibuka bila goal dah set dan balance tabung minimum USD 10.",
  missionBeforeStartIntro: [
    "Project Grow datang sekali dengan Mission.",
    "Kau kena maintain prestasi dan disiplin untuk complete mission satu per satu.",
    "",
    "Pilih mode dulu, lepas tu start mission."
  ].join("\\n"),
  missionRunningIntro: "Mission tengah berjalan. Fokus maintain consistency sampai complete.",

  missionNormalLabel: "Normal Mode",
  missionAdvancedLabel: "Advanced Mode",
  missionStartNormalBtn: "🚀 Start Mission (Normal)",
  missionStartAdvancedBtn: "🚀 Start Mission (Advanced)",
  missionRunningBadge: "Mission Active",

  missionLevel1Title: "Level 1",
  missionLevel2Title: "Level 2 (Akan Datang)",
  missionLevel3Title: "Level 3 (Akan Datang)",

  missionLevel1Items: [
    {
      title: "Mission 1 : Honest Log",
      desc: "User wajib kemaskini aktiviti dalam MM Helper selama 14 hari berturut termasuk hari tiada trade. Kalau ada hari tak update, kira gagal."
    },
    {
      title: "Mission 2 : Honest Grow",
      desc: "User wajib kemaskini aktiviti trading setiap hari minimum 14 hari berturut termasuk hari tiada trade dan wajib ada transaksi tabung minimum 2 kali dalam tempoh ni."
    },
    {
      title: "Mission 3 : Respect Max Loss",
      desc: "Tak langgar daily max loss limit selama 30 hari berturut. Daily max loss ikut nilai yang user isi masa Initial Setup."
    },
    {
      title: "Mission 4 : Double UP",
      desc: "Capai ROI 100% dari grow target yang user pilih masa Set New Goal."
    }
  ],

  missionLevelComingSoonText: "Bahagian ni kita lock dulu. Nanti kita buka lepas Level 1 settle."
};

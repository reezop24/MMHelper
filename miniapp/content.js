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
    "Untung kau bangga cerita.",
    "Rugi kau senyap simpan?",
    "",
    "Kat sini tak ada tempat sorok,",
    "memang kau sorang je tengok",
    "",
    "Pilih je apa yang nak kau update"
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

  tradingFinalPrompt: "Cek semua kalau dah betul , tekan submit"
};

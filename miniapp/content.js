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
      "Aku cek tadi untuk keseluruhan kau tengah untung " + profitUsdFormatted + ", nak ambil untung tak da hal , tapi jangan sampai modal trade kau lari"
    ].join("\n");
  },

  getWithdrawalIntroLoss: function (lossUsdFormatted) {
    return [
      "Berapa kau withdraw tadi?",
      "",
      "Aku cek tadi untuk keseluruhan kau tengah rugi " + lossUsdFormatted + ". Kalau boleh, jaga dulu flow modal trade kau sebelum withdraw besar-besar."
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
      "Aku cek tadi keseluruhan kau tengah untung " + profitUsdFormatted + ". Bagus kalau nak top up modal, cuma pastikan jumlah masuk tu memang ikut plan." 
    ].join("\n");
  },

  getDepositIntroLoss: function (lossUsdFormatted) {
    return [
      "Berapa kau deposit tadi?",
      "",
      "Aku cek tadi keseluruhan kau tengah rugi " + lossUsdFormatted + ". Kalau nak top up, pastikan ni untuk stabilkan plan, bukan revenge trade." 
    ].join("\n");
  },

  depositReasonPrompt: "pilih sebab apa kau deposit . aku simpan dalam rekod",
  depositAmountPrompt: "Masukkan jumlah yang kau deposit. check betul-betul sebab tak boleh ubah",
  depositFinalPrompt: "Cek semua kalau dah betul , tekan submit"
};

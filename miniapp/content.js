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

  withdrawalFinalPrompt: "Cek semua kalau dah betul , tekan submit"
};

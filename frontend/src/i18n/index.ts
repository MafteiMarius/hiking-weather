import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import ro from "./ro.json";
import en from "./en.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { ro: { translation: ro }, en: { translation: en } },
    fallbackLng: "ro",
    supportedLngs: ["ro", "en"],
    detection: {
      // Only honour an explicit stored choice; do NOT auto-detect the browser
      // language. HikeCast serves the Romanian Carpathians, so a first-time
      // visitor gets Romanian (fallbackLng) unless they've picked otherwise.
      order: ["localStorage"],
      lookupLocalStorage: "hikecast_lang",
      caches: ["localStorage"],
    },
    interpolation: { escapeValue: false },
  });

export default i18n;

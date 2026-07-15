import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

const LANGS = ["ro", "en"] as const;

/**
 * Compact RO/EN segmented switch for the header. Changing the language:
 *  - persists to localStorage (i18next LanguageDetector caches:["localStorage"]),
 *  - flips i18n.language, which re-renders every useTranslation consumer, and
 *  - changes the language segment of the forecast/climatology/recommendation
 *    query keys, so React Query refetches those in the new language.
 */
export function LanguageToggle() {
  const { i18n, t } = useTranslation();
  const active = i18n.language?.startsWith("en") ? "en" : "ro";

  return (
    <div
      role="group"
      aria-label={t("language.label")}
      className="flex overflow-hidden rounded-md border border-stone-300"
    >
      {LANGS.map((lang) => (
        <button
          key={lang}
          onClick={() => i18n.changeLanguage(lang)}
          aria-pressed={active === lang}
          title={t("language.switchTo", { lang: lang.toUpperCase() })}
          className={cn(
            "px-2 py-1 text-xs font-semibold uppercase transition-colors",
            active === lang
              ? "bg-green-700 text-white"
              : "bg-white text-stone-500 hover:bg-stone-100",
          )}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

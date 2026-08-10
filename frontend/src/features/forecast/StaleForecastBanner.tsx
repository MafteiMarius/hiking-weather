import { CloudOff } from "lucide-react";
import { useTranslation } from "react-i18next";

interface StaleForecastBannerProps {
  /** From ForecastResponse.stale — upstream refused, this is an old payload. */
  stale: boolean;
  /** From ForecastResponse.fetched_at — ISO timestamp of the real fetch. */
  fetchedAt: string | null;
}

/**
 * Shown when the backend served an EXPIRED forecast because the weather API
 * rejected it (Open-Meteo rate-limits by IP, and shared hosting IPs get
 * refused regardless of our own traffic).
 *
 * This banner is not optional politeness. People use this app to decide
 * whether to walk up a mountain, so presenting yesterday's numbers as today's
 * would be actively unsafe — an honest "this data is old" beats both a silent
 * lie and a blank error page.
 */
export function StaleForecastBanner({ stale, fetchedAt }: StaleForecastBannerProps) {
  const { t, i18n } = useTranslation();

  if (!stale) return null;

  // Formatted in the active locale, same approach as the weekday names.
  const when = fetchedAt
    ? new Intl.DateTimeFormat(i18n.language, {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(fetchedAt))
    : null;

  return (
    <div className="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2">
      <CloudOff size={14} className="mt-0.5 shrink-0 text-amber-600" />
      <div className="text-xs leading-snug text-amber-900">
        <span className="font-semibold">{t("stale.title")}</span>{" "}
        {when ? t("stale.since", { when }) : t("stale.unknown")}
      </div>
    </div>
  );
}

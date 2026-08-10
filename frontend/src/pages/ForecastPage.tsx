import { useState, useCallback, useEffect, lazy, Suspense } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import { useTranslation } from "react-i18next";
import L from "leaflet";
import {
  Backpack,
  ChevronDown,
  ChevronUp,
  Compass,
  Home,
  Loader2,
  Mountain,
  Navigation2,
  UserCog,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useForecast } from "@/features/forecast/useForecast";
import { DayCard } from "@/features/forecast/DayCard";
import { InstabilityBanner } from "@/features/forecast/InstabilityBanner";
import { StaleForecastBanner } from "@/features/forecast/StaleForecastBanner";
import { PackingPanel } from "@/features/forecast/PackingPanel";
import { ProfileDialog } from "@/features/profile/ProfileDialog";
import { RecommendPanel } from "@/features/trails/RecommendPanel";
import { TrailsPanel } from "@/features/trails/TrailsPanel";

// Lazy: recharts is ~400 kB minified and only needed once a day card is
// clicked — no reason to ship it on first paint.
const HourlyChart = lazy(() =>
  import("@/features/forecast/HourlyChart").then((m) => ({ default: m.HourlyChart })),
);
import { SavedPanel } from "@/features/saved/SavedPanel";
import { useMe } from "@/features/auth/useAuth";
import { SearchBox } from "@/components/SearchBox";
import type { GeocodeResult, SavedLocation, Trail } from "@/types/api";

// Default: Bucegi massif — icon Carpathian location
// Make the default location the USER's set HOME location -- MARIUS
const DEFAULT_LAT = 45.36;
const DEFAULT_LNG = 25.46;

// Custom map pin as an SVG divIcon — avoids the Vite/leaflet image-loading issue
const mapPin = L.divIcon({
  html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="28" height="42">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24S24 21 24 12C24 5.37 18.63 0 12 0z"
      fill="#15803d" stroke="white" stroke-width="1.5"/>
    <circle cx="12" cy="12" r="4" fill="white"/>
  </svg>`,
  className: "",
  iconSize: [28, 42],
  iconAnchor: [14, 42],
  popupAnchor: [0, -42],
});

// Component that handles map click to move the pin
function MapClickHandler({ onMove }: { onMove: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onMove(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Component that flies the map to a new center (called when user picks a geocode result)
function FlyToController({ target }: { target: [number, number] | null }) {
  const map = useMap();
  if (target) {
    map.flyTo(target, 12, { duration: 1.2 });
  }
  return null;
}

export function ForecastPage() {
  const [lat, setLat] = useState(DEFAULT_LAT);
  const [lng, setLng] = useState(DEFAULT_LNG);
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null);
  // null = hourly chart collapsed; a number = that day's chart is open
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  // Whole bottom bar folded down to a slim header so the map fills the screen
  const [stripCollapsed, setStripCollapsed] = useState(false);
  const [packingOpen, setPackingOpen] = useState(false);
  const [recsOpen, setRecsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  // Home-picking mode: the profile dialog hides itself and the next map
  // click becomes the home location instead of moving the forecast pin.
  const [pickingHome, setPickingHome] = useState(false);
  const [pickedHome, setPickedHome] = useState<{ lat: number; lng: number } | null>(null);
  // Last picked place name — prefills the "save spot" form
  const [placeName, setPlaceName] = useState("");

  const { t } = useTranslation();
  const { data: me } = useMe();
  const { data: forecast, isLoading, isError } = useForecast(lat, lng);

  const handleMapClick = useCallback(
    (newLat: number, newLng: number) => {
      if (pickingHome) {
        // One-shot: capture the click for the profile form and return to it.
        // Deliberately does NOT move the forecast pin — home is usually a
        // city, not the spot being forecast.
        setPickedHome({ lat: newLat, lng: newLng });
        setPickingHome(false);
        return;
      }
      setLat(newLat);
      setLng(newLng);
      setFlyTarget(null); // clear so FlyToController doesn't re-trigger
      setSelectedDay(null);
      setPlaceName("");
    },
    [pickingHome],
  );

  // Escape backs out of home-picking; the Dialog's own Escape handler is
  // suspended while hidden, so the two never fight over the key.
  useEffect(() => {
    if (!pickingHome) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPickingHome(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pickingHome]);

  const handleGeocodeSelect = useCallback((result: GeocodeResult) => {
    setLat(result.lat);
    setLng(result.lng);
    setFlyTarget([result.lat, result.lng]);
    setSelectedDay(null);
    setPlaceName(result.name);
  }, []);

  const handleSavedSelect = useCallback((loc: SavedLocation) => {
    setLat(loc.lat);
    setLng(loc.lng);
    setFlyTarget([loc.lat, loc.lng]);
    setSelectedDay(null);
    setPlaceName(loc.name);
  }, []);

  const handleTrailSelect = useCallback((trail: Trail) => {
    setLat(trail.start_lat);
    setLng(trail.start_lng);
    setFlyTarget([trail.start_lat, trail.start_lng]);
    setSelectedDay(null);
    setPlaceName(trail.name);
  }, []);

  const locationLabel = forecast
    ? `${forecast.lat.toFixed(2)}°N, ${forecast.lng.toFixed(2)}°E · ${Math.round(forecast.elevation_m)} m`
    : `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E`;

  const openDay =
    forecast && selectedDay !== null ? forecast.days[selectedDay] : null;

  // Recommendations rank the selected day, or today when nothing is open
  const recsDate = openDay?.date ?? forecast?.days[0]?.date;

  return (
    <div className="flex h-full flex-col">
      {/* ── Map area ─────────────────────────────────────────────────────── */}
      <div className="relative flex-1">
        <MapContainer
          center={[DEFAULT_LAT, DEFAULT_LNG]}
          zoom={11}
          className="h-full w-full"
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            attribution='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors, <a href="https://opentopomap.org">OpenTopoMap</a>'
            maxZoom={17}
          />
          <Marker position={[lat, lng]} icon={mapPin} />
          <MapClickHandler onMove={handleMapClick} />
          <FlyToController target={flyTarget} />
        </MapContainer>

        {/* Search + trails overlays — sit above the map */}
        <div className="absolute top-3 left-3 z-[500] flex flex-col gap-2">
          <SearchBox onSelect={handleGeocodeSelect} />
          <TrailsPanel onSelect={handleTrailSelect} />
        </div>

        {/* Profile + saved locations overlay — signed-in users only.
            The profile trigger lives on the map (not the header) because the
            dialog's "Use map pin" home picker needs the current pin. */}
        {me && (
          <div className="absolute top-3 right-3 z-[500] flex items-start gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setProfileOpen(true)}
              title={t("forecast.profileTitle")}
            >
              <UserCog size={14} />
              <span className="hidden sm:inline">{t("forecast.profile")}</span>
            </Button>
            <SavedPanel
              lat={lat}
              lng={lng}
              elevationM={forecast?.elevation_m ?? null}
              suggestedName={placeName || locationLabel}
              onSelect={handleSavedSelect}
            />
          </div>
        )}

        {/* Home-picking hint — replaces nothing, just floats above the map
            while the profile dialog is hidden and waiting for a click */}
        {pickingHome && (
          <div className="absolute top-3 left-1/2 z-[600] -translate-x-1/2">
            <div className="flex items-center gap-2 rounded-full border border-green-700 bg-white px-4 py-1.5 shadow-lg">
              <Home size={13} className="text-green-700" />
              <span className="text-sm text-stone-700">{t("forecast.setHomeHint")}</span>
              <button
                onClick={() => setPickingHome(false)}
                className="text-xs font-medium text-stone-400 hover:text-stone-700"
              >
                {t("common.cancel")}
              </button>
            </div>
          </div>
        )}

        {/* Location label overlay */}
        <div className="absolute bottom-3 left-1/2 z-[500] -translate-x-1/2">
          <div className="flex items-center gap-1.5 rounded-full border border-stone-300 bg-white/95 px-3 py-1 shadow-md">
            <Navigation2 size={11} className="text-green-700" />
            <span className="text-xs text-stone-600">{locationLabel}</span>
          </div>
        </div>
      </div>

      {/* ── 7-day strip ──────────────────────────────────────────────────── */}
      <div className="shrink-0 border-t border-stone-200 bg-stone-50">
        {/* Safety notices stay visible even when the strip is collapsed —
            they shouldn't fold away with the convenience UI. */}
        <StaleForecastBanner
          stale={forecast?.stale ?? false}
          fetchedAt={forecast?.fetched_at ?? null}
        />
        <InstabilityBanner lat={lat} lng={lng} />
        <div className="flex items-center gap-2 px-4 py-2">
          <Mountain size={14} className="text-green-700" />
          <span className="text-xs font-semibold uppercase tracking-widest text-stone-500">
            {t("forecast.title")}
          </span>
          {me && recsDate && !stripCollapsed && (
            <button
              onClick={() => setRecsOpen(true)}
              className="flex items-center gap-1 rounded-md border border-stone-300 bg-white px-2 py-0.5 text-xs font-medium text-stone-700 hover:bg-stone-100 transition-colors"
            >
              <Compass size={12} className="text-green-700" />
              {t("forecast.bestTrails")}
            </button>
          )}
          {!stripCollapsed && openDay && (
            <>
              <span className="text-xs text-stone-400">
                {t("forecast.hourlyFor", { date: openDay.date })}
              </span>
              {me && (
                <button
                  onClick={() => setPackingOpen(true)}
                  className="flex items-center gap-1 rounded-md border border-stone-300 bg-white px-2 py-0.5 text-xs font-medium text-stone-700 hover:bg-stone-100 transition-colors"
                >
                  <Backpack size={12} className="text-green-700" />
                  {t("forecast.whatToPack")}
                </button>
              )}
            </>
          )}
          {forecast?.cached && !stripCollapsed && (
            <span className="ml-auto text-xs text-stone-400">{t("forecast.cached")}</span>
          )}
          <button
            onClick={() => setStripCollapsed(!stripCollapsed)}
            className={cnStripToggle(forecast?.cached && !stripCollapsed)}
            aria-label={stripCollapsed ? t("forecast.expand") : t("forecast.collapse")}
          >
            {stripCollapsed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {!stripCollapsed && (
          // Cap the expandable area at ~45% of the viewport so the map always
          // keeps the majority of the screen; overflow scrolls inside the strip.
          <div className="max-h-[45vh] overflow-y-auto overscroll-contain">
            {/* Hourly drill-down — opens when a day card is clicked */}
            {forecast && openDay && (
              <div className="border-b border-stone-200 px-4 pb-2">
                <Suspense
                  fallback={
                    <div className="flex h-44 items-center justify-center">
                      <Loader2 size={20} className="animate-spin text-stone-400" />
                    </div>
                  }
                >
                  <HourlyChart hours={forecast.hours} date={openDay.date} />
                </Suspense>
              </div>
            )}

            {isLoading && (
              <div className="flex h-44 items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-green-700 border-t-transparent" />
              </div>
            )}

            {isError && (
              <div className="flex h-44 items-center justify-center text-sm text-stone-500">
                {t("forecast.loadError")}
              </div>
            )}

            {forecast && (
              <div className="flex gap-2 overflow-x-auto px-4 pb-4 pt-2">
                {forecast.days.map((day, i) => (
                  <DayCard
                    key={day.date}
                    day={day}
                    isSelected={i === selectedDay}
                    onClick={() =>
                      setSelectedDay(selectedDay === i ? null : i)
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Hiking profile editor — feeds the recommendation ranking */}
      {me && (
        <ProfileDialog
          open={profileOpen}
          onClose={() => {
            setProfileOpen(false);
            // Forget an unsaved pick so reopening starts from server truth
            setPickedHome(null);
          }}
          hidden={pickingHome}
          pickedHome={pickedHome}
          onPickOnMap={() => setPickingHome(true)}
        />
      )}

      {/* Personalised trail ranking for the selected (or first) day */}
      {recsDate && (
        <RecommendPanel
          date={recsDate}
          open={recsOpen}
          onClose={() => setRecsOpen(false)}
          onSelect={handleTrailSelect}
        />
      )}

      {/* AI packing advice — remounts per day so each opens fresh */}
      {openDay && (
        <PackingPanel
          key={openDay.date}
          lat={lat}
          lng={lng}
          date={openDay.date}
          open={packingOpen}
          onClose={() => setPackingOpen(false)}
        />
      )}
    </div>
  );
}

// The chevron hugs the right edge; when the "cached" hint is showing it
// already claimed ml-auto, so only add it ourselves when absent.
function cnStripToggle(cachedShown: boolean | undefined): string {
  return [
    "rounded p-1 text-stone-400 hover:bg-stone-200 hover:text-stone-700 transition-colors",
    cachedShown ? "" : "ml-auto",
  ].join(" ");
}

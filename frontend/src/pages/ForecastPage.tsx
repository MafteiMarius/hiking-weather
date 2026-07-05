import { useState, useCallback, lazy, Suspense } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import { Loader2, Mountain, Navigation2 } from "lucide-react";
import { useForecast } from "@/features/forecast/useForecast";
import { DayCard } from "@/features/forecast/DayCard";

// Lazy: recharts is ~400 kB minified and only needed once a day card is
// clicked — no reason to ship it on first paint.
const HourlyChart = lazy(() =>
  import("@/features/forecast/HourlyChart").then((m) => ({ default: m.HourlyChart })),
);
import { SavedPanel } from "@/features/saved/SavedPanel";
import { useMe } from "@/features/auth/useAuth";
import { SearchBox } from "@/components/SearchBox";
import type { GeocodeResult, SavedLocation } from "@/types/api";

// Default: Bucegi massif — icon Carpathian location
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
  // Last picked place name — prefills the "save spot" form
  const [placeName, setPlaceName] = useState("");

  const { data: me } = useMe();
  const { data: forecast, isLoading, isError } = useForecast(lat, lng);

  const handleMapClick = useCallback((newLat: number, newLng: number) => {
    setLat(newLat);
    setLng(newLng);
    setFlyTarget(null); // clear so FlyToController doesn't re-trigger
    setSelectedDay(null);
    setPlaceName("");
  }, []);

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

  const locationLabel = forecast
    ? `${forecast.lat.toFixed(2)}°N, ${forecast.lng.toFixed(2)}°E · ${Math.round(forecast.elevation_m)} m`
    : `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E`;

  const openDay =
    forecast && selectedDay !== null ? forecast.days[selectedDay] : null;

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

        {/* Search box overlay — sits above the map */}
        <div className="absolute top-3 left-3 z-[500]">
          <SearchBox onSelect={handleGeocodeSelect} />
        </div>

        {/* Saved locations overlay — signed-in users only */}
        {me && (
          <div className="absolute top-3 right-3 z-[500]">
            <SavedPanel
              lat={lat}
              lng={lng}
              elevationM={forecast?.elevation_m ?? null}
              suggestedName={placeName || locationLabel}
              onSelect={handleSavedSelect}
            />
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
        <div className="flex items-center gap-2 px-4 pt-3 pb-1">
          <Mountain size={14} className="text-green-700" />
          <span className="text-xs font-semibold uppercase tracking-widest text-stone-500">
            7-Day Forecast
          </span>
          {openDay && (
            <span className="text-xs text-stone-400">
              — hourly for {openDay.date}
            </span>
          )}
          {forecast?.cached && (
            <span className="ml-auto text-xs text-stone-400">cached</span>
          )}
        </div>

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
            Could not load forecast — check your connection.
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
    </div>
  );
}

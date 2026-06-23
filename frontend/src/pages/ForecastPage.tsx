import { useState, useCallback } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import { Mountain, Navigation2 } from "lucide-react";
import { useForecast } from "@/features/forecast/useForecast";
import { DayCard } from "@/features/forecast/DayCard";
import { SearchBox } from "@/components/SearchBox";
import type { GeocodeResult } from "@/types/api";

// Default: Bucegi massif — icon Carpathian location
const DEFAULT_LAT = 45.36;
const DEFAULT_LNG = 25.46;

// Custom map pin as an SVG divIcon — avoids the Vite/leaflet image-loading issue
const mapPin = L.divIcon({
  html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="28" height="42">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24S24 21 24 12C24 5.37 18.63 0 12 0z"
      fill="#0ea5e9" stroke="white" stroke-width="1.5"/>
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
  const [selectedDay, setSelectedDay] = useState(0);

  const { data: forecast, isLoading, isError } = useForecast(lat, lng);

  const handleMapClick = useCallback((newLat: number, newLng: number) => {
    setLat(newLat);
    setLng(newLng);
    setFlyTarget(null); // clear so FlyToController doesn't re-trigger
    setSelectedDay(0);
  }, []);

  const handleGeocodeSelect = useCallback((result: GeocodeResult) => {
    setLat(result.lat);
    setLng(result.lng);
    setFlyTarget([result.lat, result.lng]);
    setSelectedDay(0);
  }, []);

  const locationLabel = forecast
    ? `${forecast.lat.toFixed(2)}°N, ${forecast.lng.toFixed(2)}°E · ${Math.round(forecast.elevation_m)} m`
    : `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E`;

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

        {/* Location label overlay */}
        <div className="absolute bottom-3 left-1/2 z-[500] -translate-x-1/2">
          <div className="flex items-center gap-1.5 rounded-full border border-slate-600/60 bg-slate-900/80 px-3 py-1 backdrop-blur-sm">
            <Navigation2 size={11} className="text-sky-400" />
            <span className="text-xs text-slate-300">{locationLabel}</span>
          </div>
        </div>
      </div>

      {/* ── 7-day strip ──────────────────────────────────────────────────── */}
      <div className="shrink-0 border-t border-slate-700 bg-slate-900">
        <div className="flex items-center gap-2 px-4 pt-3 pb-1">
          <Mountain size={14} className="text-sky-400" />
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            7-Day Forecast
          </span>
          {forecast?.cached && (
            <span className="ml-auto text-xs text-slate-600">cached</span>
          )}
        </div>

        {isLoading && (
          <div className="flex h-44 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
          </div>
        )}

        {isError && (
          <div className="flex h-44 items-center justify-center text-sm text-slate-500">
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
                onClick={() => setSelectedDay(i)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

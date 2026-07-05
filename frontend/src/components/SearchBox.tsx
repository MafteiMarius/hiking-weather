import { useState, useRef, useEffect } from "react";
import { Search, MapPin, Loader2 } from "lucide-react";
import { useGeocode } from "@/features/forecast/useForecast";
import { cn } from "@/lib/utils";
import type { GeocodeResult } from "@/types/api";

interface SearchBoxProps {
  onSelect: (result: GeocodeResult) => void;
  className?: string;
}

export function SearchBox({ onSelect, className }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounce: wait 400ms after last keystroke before fetching
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 400);
    return () => clearTimeout(t);
  }, [query]);

  const { data, isFetching } = useGeocode(debouncedQuery);
  const results = data?.results ?? [];

  // Close dropdown when clicking outside
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function handleSelect(result: GeocodeResult) {
    setQuery(result.name);
    setOpen(false);
    onSelect(result);
  }

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
        />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search location…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className={cn(
            // Narrower on phones so it doesn't collide with the saved-spots
            // buttons in the opposite corner
            "h-9 w-44 rounded-lg border border-stone-300 bg-white py-2 pl-8 pr-8 shadow-md sm:w-64",
            "text-sm text-stone-900 placeholder:text-stone-400",
            "focus:border-green-600 focus:outline-none focus:ring-1 focus:ring-green-600",
          )}
        />
        {isFetching && (
          <Loader2
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-stone-400"
          />
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="absolute top-full left-0 mt-1 w-64 overflow-hidden rounded-lg border border-stone-200 bg-white shadow-xl sm:w-72">
          {results.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => handleSelect(r)}
                className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-stone-50 transition-colors"
              >
                <MapPin size={14} className="mt-0.5 shrink-0 text-green-700" />
                <div>
                  <p className="text-sm font-medium text-stone-900">{r.name}</p>
                  <p className="text-xs text-stone-500">
                    {r.country}
                    {r.elevation_m != null && ` · ${Math.round(r.elevation_m)} m`}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

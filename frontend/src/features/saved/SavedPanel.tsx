import { useState } from "react";
import { Bookmark, Loader2, MapPin, Trash2, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useDeleteLocation,
  useSavedLocations,
  useSaveLocation,
} from "@/features/saved/useSavedLocations";
import { cn } from "@/lib/utils";
import type { SavedLocation } from "@/types/api";

interface SavedPanelProps {
  lat: number;
  lng: number;
  elevationM: number | null;
  /** Prefill for the save form — last searched place name or a coord label */
  suggestedName: string;
  onSelect: (loc: SavedLocation) => void;
}

/**
 * Map overlay (top-right): a "Save spot" action for the current pin and a
 * dropdown list of previously saved locations. Rendered only when logged in.
 */
export function SavedPanel({ lat, lng, elevationM, suggestedName, onSelect }: SavedPanelProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");

  const { data: locations, isLoading } = useSavedLocations(true);
  const save = useSaveLocation();
  const remove = useDeleteLocation();

  function startSaving() {
    setName(suggestedName);
    setSaving(true);
    setOpen(false);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await save.mutateAsync({
      name: name.trim(),
      lat,
      lng,
      elevation_m: elevationM != null ? Math.round(elevationM) : null,
    });
    setSaving(false);
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={startSaving} title={t("saved.saveThisSpot")}>
          <Bookmark size={14} />
          <span className="hidden sm:inline">{t("saved.saveSpot")}</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setOpen(!open);
            setSaving(false);
          }}
          className={cn(open && "bg-stone-100")}
          title={t("saved.savedTitle")}
        >
          <Bookmark size={14} className="fill-current sm:hidden" />
          <span className="hidden sm:inline">{t("saved.saved")}</span>
          {locations && locations.length > 0 && (
            <span className="rounded-full bg-green-700 px-1.5 text-xs text-white">
              {locations.length}
            </span>
          )}
        </Button>
      </div>

      {/* Save form */}
      {saving && (
        <form
          onSubmit={handleSave}
          className="flex w-72 flex-col gap-2 rounded-lg border border-stone-200 bg-white p-3 shadow-xl"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-stone-600">
              {t("saved.saveHeading", {
                coords: `${lat.toFixed(3)}°N, ${lng.toFixed(3)}°E`,
              })}
            </span>
            <button
              type="button"
              onClick={() => setSaving(false)}
              className="rounded p-0.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
              aria-label={t("common.cancel")}
            >
              <X size={14} />
            </button>
          </div>
          <Input
            autoFocus
            maxLength={160}
            placeholder={t("saved.namePlaceholder")}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          {save.isError && (
            <p className="text-xs text-red-600">{t("saved.saveError")}</p>
          )}
          <Button type="submit" size="sm" disabled={save.isPending || !name.trim()}>
            {save.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </form>
      )}

      {/* Saved list */}
      {open && (
        <div className="w-72 overflow-hidden rounded-lg border border-stone-200 bg-white shadow-xl">
          {isLoading && (
            <div className="flex h-16 items-center justify-center">
              <Loader2 size={16} className="animate-spin text-stone-400" />
            </div>
          )}
          {locations && locations.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-stone-400">
              {t("saved.empty")}
            </p>
          )}
          {locations && locations.length > 0 && (
            <ul className="max-h-64 divide-y divide-stone-100 overflow-y-auto">
              {locations.map((loc) => (
                <li key={loc.id} className="flex items-center hover:bg-stone-50">
                  <button
                    onClick={() => {
                      onSelect(loc);
                      setOpen(false);
                    }}
                    className="flex flex-1 items-start gap-2 px-3 py-2 text-left"
                  >
                    <MapPin size={14} className="mt-0.5 shrink-0 text-green-700" />
                    <span>
                      <span className="block text-sm font-medium text-stone-900">
                        {loc.name}
                      </span>
                      <span className="block text-xs text-stone-500">
                        {loc.lat.toFixed(3)}°N, {loc.lng.toFixed(3)}°E
                        {loc.elevation_m != null && ` · ${loc.elevation_m} m`}
                      </span>
                    </span>
                  </button>
                  <button
                    onClick={() => remove.mutate(loc.id)}
                    disabled={remove.isPending}
                    className="mr-2 rounded p-1.5 text-stone-300 hover:bg-red-50 hover:text-red-600"
                    aria-label={t("saved.deleteAria", { name: loc.name })}
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

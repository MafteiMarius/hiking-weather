import { useEffect, useState } from "react";
import { Home, Loader2, MapPin, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useProfile, useUpdateProfile } from "@/features/profile/useProfile";
import { cn } from "@/lib/utils";
import type { Profile } from "@/types/api";

interface ProfileDialogProps {
  open: boolean;
  onClose: () => void;
  /**
   * Home picking happens ON the page's map, so the page owns the mode:
   * `onPickOnMap` asks it to hide this dialog and arm a one-shot map click;
   * the picked point comes back through `pickedHome`; `hidden` is true while
   * the user is out there clicking (the form stays mounted, edits survive).
   */
  hidden: boolean;
  pickedHome: { lat: number; lng: number } | null;
  onPickOnMap: () => void;
}

// Same 1–5 scale the trail catalogue uses (see DifficultyDots in TrailsPanel);
// words instead of dots here because the user is choosing, not scanning.
const EXPERIENCE_LABELS = ["Beginner", "Occasional", "Regular", "Experienced", "Expert"];
const DIFFICULTY_LABELS = ["Easy walks", "Easy", "Moderate", "Hard", "Very hard / exposed"];

/** Row of 1–5 toggle buttons with the selected level named beside them. */
function LevelPicker({
  value,
  onChange,
  labels,
  name,
}: {
  value: number;
  onChange: (level: number) => void;
  labels: string[];
  name: string;
}) {
  return (
    <div className="flex items-center gap-1" role="radiogroup" aria-label={name}>
      {[1, 2, 3, 4, 5].map((level) => (
        <button
          key={level}
          type="button"
          role="radio"
          aria-checked={level === value}
          onClick={() => onChange(level)}
          className={cn(
            "h-8 w-8 rounded-lg border text-sm font-medium transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600",
            level === value
              ? "border-green-700 bg-green-700 text-white"
              : "border-stone-300 bg-white text-stone-600 hover:bg-stone-50",
          )}
        >
          {level}
        </button>
      ))}
      <span className="ml-2 text-xs text-stone-500">{labels[value - 1]}</span>
    </div>
  );
}

/**
 * Edit the hiking profile that drives "Best trails": experience level and
 * difficulty cap (penalty/filter), home location and max distance (distance
 * penalty/filter). Backend: PATCH /api/v1/profile — see DECISIONS 014 for how
 * each field enters the ranking.
 */
export function ProfileDialog({
  open,
  onClose,
  hidden,
  pickedHome,
  onPickOnMap,
}: ProfileDialogProps) {
  const { data: profile, isPending, isError } = useProfile(open);

  return (
    <Dialog open={open} onClose={onClose} hidden={hidden} title="Hiking profile">
      {isPending && (
        <div className="flex h-40 items-center justify-center">
          <Loader2 size={20} className="animate-spin text-stone-400" />
        </div>
      )}
      {isError && (
        <p className="py-4 text-sm text-red-600">
          Could not load your profile — try again in a moment.
        </p>
      )}
      {/* Form is a child component so its useState initialisers run only once
          the profile exists — no effect needed to sync fetched data in. */}
      {profile && (
        <ProfileForm
          profile={profile}
          pickedHome={pickedHome}
          onPickOnMap={onPickOnMap}
          onClose={onClose}
        />
      )}
    </Dialog>
  );
}

function ProfileForm({
  profile,
  pickedHome,
  onPickOnMap,
  onClose,
}: {
  profile: Profile;
  pickedHome: { lat: number; lng: number } | null;
  onPickOnMap: () => void;
  onClose: () => void;
}) {
  const [displayName, setDisplayName] = useState(profile.display_name ?? "");
  const [experience, setExperience] = useState(profile.experience_level);
  const [maxDifficulty, setMaxDifficulty] = useState(profile.max_difficulty);
  const [maxDistance, setMaxDistance] = useState(String(profile.max_distance_km));
  const [home, setHome] = useState(
    profile.home_lat != null && profile.home_lng != null
      ? { lat: profile.home_lat, lng: profile.home_lng }
      : null,
  );
  const update = useUpdateProfile();

  // Adopt the point picked on the map. An effect (not an initialiser)
  // because the form stays mounted while the user is out on the map — the
  // pick arrives as a prop change on a live component.
  useEffect(() => {
    if (pickedHome) setHome(pickedHome);
  }, [pickedHome]);

  const distanceKm = Number.parseInt(maxDistance, 10);
  const distanceValid = Number.isInteger(distanceKm) && distanceKm >= 1 && distanceKm <= 5000;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!distanceValid) return;
    update.mutate(
      {
        display_name: displayName.trim() || null,
        experience_level: experience,
        max_difficulty: maxDifficulty,
        max_distance_km: distanceKm,
        // Explicit null clears home on the backend (PATCH treats a present
        // null as "set to null", an absent field as "leave alone").
        home_lat: home?.lat ?? null,
        home_lng: home?.lng ?? null,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <p className="text-xs text-stone-500">
        “Best trails” uses this to filter and rank recommendations for you.
      </p>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-stone-600">Display name (optional)</span>
        <Input
          maxLength={80}
          placeholder="How should we call you?"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
      </label>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-stone-600">Experience level</span>
        <LevelPicker
          value={experience}
          onChange={setExperience}
          labels={EXPERIENCE_LABELS}
          name="Experience level"
        />
        <span className="text-xs text-stone-400">
          Trails harder than this rank lower, but still show.
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-stone-600">Maximum difficulty</span>
        <LevelPicker
          value={maxDifficulty}
          onChange={setMaxDifficulty}
          labels={DIFFICULTY_LABELS}
          name="Maximum difficulty"
        />
        <span className="text-xs text-stone-400">Trails above this are hidden entirely.</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-stone-600">Home location</span>
        <div className="flex items-center gap-2">
          <Home size={14} className="shrink-0 text-green-700" />
          {home ? (
            <>
              <span className="text-sm text-stone-700">
                {home.lat.toFixed(3)}°N, {home.lng.toFixed(3)}°E
              </span>
              <button
                type="button"
                onClick={() => setHome(null)}
                className="rounded p-0.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
                aria-label="Clear home location"
              >
                <X size={14} />
              </button>
            </>
          ) : (
            <span className="text-sm text-stone-400">Not set</span>
          )}
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="ml-auto"
            onClick={onPickOnMap}
          >
            <MapPin size={14} />
            Choose on map
          </Button>
        </div>
        <span className="text-xs text-stone-400">
          “Choose on map” hides this window — click your home on the map and
          you’ll be brought back. Without a home, distance is ignored.
        </span>
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-stone-600">Maximum distance from home</span>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={1}
            max={5000}
            className="w-28"
            value={maxDistance}
            onChange={(e) => setMaxDistance(e.target.value)}
          />
          <span className="text-sm text-stone-500">km</span>
        </div>
        {!distanceValid && (
          <span className="text-xs text-red-600">Enter a distance between 1 and 5000 km.</span>
        )}
      </label>

      {update.isError && (
        <p className="text-xs text-red-600">Could not save — try again.</p>
      )}

      <Button type="submit" disabled={update.isPending || !distanceValid}>
        {update.isPending ? "Saving…" : "Save profile"}
      </Button>
    </form>
  );
}

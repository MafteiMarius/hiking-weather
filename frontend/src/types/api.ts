export type ScoreLabel = "Excellent" | "Good" | "Fair" | "Poor" | "Dangerous";

export interface DayForecast {
  date: string;
  weather_code: number;
  weather_description: string;
  temp_max_c: number;
  temp_min_c: number;
  precipitation_sum_mm: number;
  precipitation_probability_max: number;
  wind_speed_max_kmh: number;
  wind_gusts_max_kmh: number;
  score: number;
  score_label: ScoreLabel;
  score_reason: string;
}

export interface HourForecast {
  time: string; // "2026-06-23T14:00" (location-local)
  temp_c: number;
  precipitation_mm: number;
  precipitation_probability: number;
  wind_gusts_kmh: number;
  weather_code: number;
}

export interface ForecastResponse {
  lat: number;
  lng: number;
  elevation_m: number;
  timezone: string;
  days: DayForecast[];
  hours: HourForecast[];
  cached: boolean;
}

export interface ClimatologyResponse {
  lat: number;
  lng: number;
  iso_week: number;
  years_analyzed: number;
  precip_day_frequency_pct: number | null;
  thunderstorm_pct: number | null;
  temp_avg_max_c: number | null;
  temp_avg_min_c: number | null;
  wind_gust_p90_kmh: number | null;
  volatility_index: number | null;
  unstable: boolean;
  reasons: string[];
  cached: boolean;
}

export interface SavedLocation {
  id: string;
  name: string;
  lat: number;
  lng: number;
  elevation_m: number | null;
  notes: string | null;
  created_at: string;
}

export interface SavedLocationCreate {
  name: string;
  lat: number;
  lng: number;
  elevation_m?: number | null;
  notes?: string | null;
}

export interface GeocodeResult {
  id: number;
  name: string;
  country: string;
  country_code: string;
  lat: number;
  lng: number;
  elevation_m?: number;
}

export interface GeocodeResponse {
  results: GeocodeResult[];
}

export interface Trail {
  id: string;
  slug: string;
  name: string;
  region: string;
  difficulty: number; // 1 walk … 5 exposed/very hard
  duration_minutes: number;
  distance_m: number;
  elevation_gain_m: number;
  start_lat: number;
  start_lng: number;
  summit_lat: number | null;
  summit_lng: number | null;
  summit_elev_m: number | null;
  description: string | null;
}

export interface EquipmentItem {
  name: string;
  reason: string;
  essential: boolean;
}

export interface EquipmentPlan {
  date: string;
  summary: string;
  items: EquipmentItem[];
  warnings: string[];
}

export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

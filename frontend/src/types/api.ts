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

export interface ForecastResponse {
  lat: number;
  lng: number;
  elevation_m: number;
  timezone: string;
  days: DayForecast[];
  cached: boolean;
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

export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

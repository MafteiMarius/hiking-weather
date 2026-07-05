import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HourForecast } from "@/types/api";

interface HourlyChartProps {
  /** All hours from the forecast; the chart filters to one day. */
  hours: HourForecast[];
  /** "2026-06-23" — the selected day */
  date: string;
}

interface ChartPoint {
  hour: string; // "14"
  temp: number;
  precip: number;
  gusts: number;
}

export function HourlyChart({ hours, date }: HourlyChartProps) {
  // hours can be missing when the service worker replays a response cached
  // before hourly support — degrade to the empty state, never crash.
  const points: ChartPoint[] = (hours ?? [])
    .filter((h) => h.time.startsWith(date))
    .map((h) => ({
      hour: h.time.slice(11, 13),
      temp: Math.round(h.temp_c * 10) / 10,
      precip: Math.round(h.precipitation_mm * 10) / 10,
      gusts: Math.round(h.wind_gusts_kmh),
    }));

  if (points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-stone-400">
        No hourly data for this day.
      </div>
    );
  }

  return (
    <div className="h-32 w-full sm:h-36 lg:h-44">
      <ResponsiveContainer>
        <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid stroke="#e7e5e4" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="hour"
            tick={{ fontSize: 11, fill: "#78716c" }}
            tickLine={false}
            axisLine={{ stroke: "#d6d3d1" }}
            interval={2}
          />
          {/* Left axis: °C and km/h share a scale — both are "small numbers" */}
          <YAxis
            yAxisId="main"
            tick={{ fontSize: 11, fill: "#78716c" }}
            tickLine={false}
            axisLine={false}
          />
          {/* Right axis: precipitation in mm */}
          <YAxis
            yAxisId="precip"
            orientation="right"
            tick={{ fontSize: 11, fill: "#78716c" }}
            tickLine={false}
            axisLine={false}
            width={32}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e7e5e4",
              boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
            }}
            formatter={(value, name) => {
              if (name === "Temp") return [`${value} °C`, name];
              if (name === "Rain") return [`${value} mm`, name];
              return [`${value} km/h`, name];
            }}
            labelFormatter={(hour) => `${hour}:00`}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} iconSize={10} />
          <Bar
            yAxisId="precip"
            dataKey="precip"
            name="Rain"
            fill="#93c5fd"
            radius={[2, 2, 0, 0]}
          />
          <Line
            yAxisId="main"
            type="monotone"
            dataKey="temp"
            name="Temp"
            stroke="#ea580c"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="main"
            type="monotone"
            dataKey="gusts"
            name="Gusts"
            stroke="#78716c"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

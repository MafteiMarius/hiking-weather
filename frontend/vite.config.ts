import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "HikeCast",
        short_name: "HikeCast",
        description: "Hiker-tuned 7-day forecasts for the Carpathians",
        theme_color: "#0f172a", // Tailwind slate-900
        background_color: "#0f172a",
        display: "standalone",
        icons: [
          { src: "icons.svg", sizes: "any", type: "image/svg+xml" },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            // Forecast API — stale-while-revalidate, max 60 minutes
            urlPattern: /\/api\/v1\/forecast/,
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "forecast-cache",
              expiration: { maxAgeSeconds: 60 * 60 },
            },
          },
          {
            // OpenTopoMap tiles — cache-first, keep 200 tiles
            urlPattern: /^https:\/\/[abc]\.tile\.opentopomap\.org\//,
            handler: "CacheFirst",
            options: {
              cacheName: "map-tiles",
              expiration: { maxEntries: 200, maxAgeSeconds: 7 * 24 * 60 * 60 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});

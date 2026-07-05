import path from "path";
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
        theme_color: "#15803d", // Tailwind green-700
        background_color: "#f5f5f4", // Tailwind stone-100
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
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split the heavyweights into parallel-loadable, independently-cached
        // chunks — the app code changes often, leaflet/recharts almost never.
        manualChunks: {
          "react-vendor": [
            "react",
            "react-dom",
            "react-router-dom",
            "@tanstack/react-query",
            "axios",
          ],
          leaflet: ["leaflet", "react-leaflet"],
          recharts: ["recharts"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});

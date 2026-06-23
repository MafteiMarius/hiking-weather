import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { ForecastPage } from "@/pages/ForecastPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/forecast" replace />} />
        <Route path="/forecast" element={<ForecastPage />} />
        {/* Remaining pages — to be built in later days */}
        <Route path="*" element={<Navigate to="/forecast" replace />} />
      </Routes>
    </AppShell>
  );
}

import { Routes, Route } from "react-router-dom";
import { useTranslation } from "react-i18next";

// Pages are stubs — implemented per phase
function Placeholder({ title }: { title: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-900 text-white">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-slate-400">{t("app.tagline")}</p>
      <p className="text-xs text-slate-500">{t("footer.attribution")}</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Placeholder title="HikeCast" />} />
      <Route path="/explore" element={<Placeholder title="Explore" />} />
      <Route path="/forecast" element={<Placeholder title="Forecast" />} />
      <Route path="/recommendations" element={<Placeholder title="Recommendations" />} />
      <Route path="/saved" element={<Placeholder title="Saved" />} />
      <Route path="/login" element={<Placeholder title="Login" />} />
      <Route path="/signup" element={<Placeholder title="Sign Up" />} />
    </Routes>
  );
}

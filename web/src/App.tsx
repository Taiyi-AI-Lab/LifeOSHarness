import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { loadApiKey } from "./lib/storage";
import { Overview } from "./pages/Overview";
import { Packs } from "./pages/Packs";
import { RuntimeInspector } from "./pages/RuntimeInspector";
import { WorldDetail } from "./pages/WorldDetail";
import { Worlds } from "./pages/Worlds";

export function App() {
  const [apiKey, setApiKey] = useState(() => loadApiKey());

  return (
    <Layout apiKey={apiKey} onApiKeyChange={setApiKey}>
      <Routes>
        <Route path="/" element={<Overview apiKey={apiKey} />} />
        <Route path="/worlds" element={<Worlds apiKey={apiKey} />} />
        <Route path="/worlds/:worldId" element={<WorldDetail apiKey={apiKey} />} />
        <Route path="/packs" element={<Packs apiKey={apiKey} />} />
        <Route path="/inspector" element={<RuntimeInspector apiKey={apiKey} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

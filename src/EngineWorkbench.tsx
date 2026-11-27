import { useCallback, useEffect, useState } from "react";
import "./engine-workbench.css";

type EngineStatus = {
  configured?: boolean;
  operational?: boolean;
  runtime_healthy?: boolean;
  customer_release_approved?: boolean;
  customer_animation_enabled?: boolean;
  supports_audio_driven_portrait?: boolean;
  engine?: string | null;
  version?: string | null;
  message?: string;
  runtime_error?: string | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export default function EngineWorkbench() {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checkedAt, setCheckedAt] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/engine/status`, {
        headers: { Accept: "application/json" },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Engine status request failed (${response.status}).`);
      }
      setStatus(data as EngineStatus);
      setCheckedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not contact the backend.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const yesNo = (value?: boolean) => value ? "YES" : "NO";

  return (
    <section className="engine-workbench">
      <div className="engine-workbench-heading">
        <div>
          <p className="eyebrow">IN-HOUSE AI DEVELOPMENT</p>
          <h2>Animation Engine Workbench</h2>
          <p>Live view of the backend engine we are building and qualifying. This panel never enables customer animation by itself.</p>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={loading}>
          {loading ? "Checking…" : "Refresh status"}
        </button>
      </div>

      {error && <div className="workbench-alert">{error}</div>}

      <div className="workbench-status-grid">
        <div><span>Backend engine configured</span><strong>{yesNo(status?.configured)}</strong></div>
        <div><span>Runtime operational</span><strong>{yesNo(status?.operational)}</strong></div>
        <div><span>Runtime health passed</span><strong>{yesNo(status?.runtime_healthy)}</strong></div>
        <div><span>Customer animation approved</span><strong>{yesNo(status?.customer_animation_enabled)}</strong></div>
      </div>

      <div className="workbench-engine-detail">
        <div><span>Engine</span><strong>{status?.engine || "Not installed"}</strong></div>
        <div><span>Version</span><strong>{status?.version || "—"}</strong></div>
        <div><span>Audio-driven portrait</span><strong>{yesNo(status?.supports_audio_driven_portrait)}</strong></div>
        <div><span>Last checked</span><strong>{checkedAt || "Not checked"}</strong></div>
      </div>

      <div className="workbench-roadmap">
        <h3>Our own animation engine — development stages</h3>
        <ol>
          <li className="complete"><strong>Backend and website connection</strong><span>API status and motion diagnostics are connected.</span></li>
          <li className="active"><strong>Build our own model pipeline</strong><span>Define training data, model architecture, and reproducible experiments.</span></li>
          <li><strong>Train and validate portrait animation</strong><span>Requires consented training data and suitable GPU compute.</span></li>
          <li><strong>Connect real photo animation</strong><span>Only after real inference, quality, safety, and rights checks pass.</span></li>
          <li><strong>Live calling and recording</strong><span>Streaming, audio/video synchronization, and recording come after inference works.</span></li>
        </ol>
      </div>

      <p className="workbench-note">
        {status?.customer_animation_enabled
          ? "Customer animation is approved by the backend release gate."
          : "Safe development mode: photo selection and motion tests can be explored, but no real AI photo animation is currently running."}
      </p>
    </section>
  );
}

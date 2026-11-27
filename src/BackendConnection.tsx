import { useCallback, useEffect, useState } from "react";
import "./backend-connection.css";

type BackendSnapshot = {
  status?: string;
  service_alive?: boolean;
  animation_engine_configured?: boolean;
  runtime_health_check_passed?: boolean;
  customer_release_approved?: boolean;
  customer_animation_enabled?: boolean;
  engine?: {
    engine_id?: string;
    version?: string | null;
    operational?: boolean;
    supports_audio_driven_portrait?: boolean;
    message?: string;
    runtime_error?: string | null;
  };
  message?: string;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export default function BackendConnection() {
  const [snapshot, setSnapshot] = useState<BackendSnapshot | null>(null);
  const [checking, setChecking] = useState(true);
  const [checkedAt, setCheckedAt] = useState("");

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const response = await fetch(`${API_BASE}/ready`, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(8000)
      });
      if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
      const data = await response.json() as BackendSnapshot;
      setSnapshot(data);
      setCheckedAt(new Date().toLocaleTimeString());
    } catch (error) {
      setSnapshot(null);
      setCheckedAt(new Date().toLocaleTimeString());
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const connected = Boolean(snapshot?.service_alive);
  const enabled = Boolean(snapshot?.customer_animation_enabled);
  const engineReady = Boolean(snapshot?.engine?.operational);

  return (
    <section className="backend-connection-card" aria-live="polite">
      <div className="backend-connection-top">
        <div>
          <p className="eyebrow">SPEEDY LIVE BACKEND</p>
          <h2>Website connection & engine status</h2>
          <p className="backend-connection-url">{API_BASE}</p>
        </div>
        <span className={connected ? "backend-pill online" : "backend-pill offline"}>
          {checking ? "CHECKING…" : connected ? "API CONNECTED" : "API NOT CONNECTED"}
        </span>
      </div>

      <div className="backend-status-grid">
        <div><span>Backend service</span><strong>{connected ? "Online" : "Unavailable"}</strong></div>
        <div><span>Animation model</span><strong>{engineReady ? "Runtime ready" : "Not installed / ready"}</strong></div>
        <div><span>Customer animation</span><strong>{enabled ? "Enabled" : "Disabled"}</strong></div>
        <div><span>Audio-driven portrait</span><strong>{snapshot?.engine?.supports_audio_driven_portrait ? "Declared by engine" : "Not available"}</strong></div>
      </div>

      <p className="backend-status-message">
        {!connected
          ? "The website cannot reach the backend yet. Set VITE_API_BASE_URL to the deployed backend address and allow this website in the backend CORS settings."
          : enabled
            ? "The backend reports that customer animation is enabled. The actual photo and audio workflows must still be tested end to end."
            : "The website is now checking the backend, but photo animation is correctly blocked because no qualified, runtime-tested and approved animation engine is available."}
      </p>
      <div className="backend-connection-bottom">
        <span>{checkedAt ? `Last checked: ${checkedAt}` : "Waiting for first check"}</span>
        <button type="button" onClick={() => void refresh()} disabled={checking}>
          {checking ? "Checking…" : "Check again"}
        </button>
      </div>
    </section>
  );
}

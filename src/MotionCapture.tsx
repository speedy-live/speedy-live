import { useEffect, useRef, useState } from "react";
import "./motion-capture.css";

type Point = {
  x: number;
  y: number;
  z: number;
  visibility: number | null;
};

type MotionEventDetail = {
  timestampMs: number;
  bodyLandmarks: Point[];
  hands: Array<{ handedness: string; landmarks: Point[] }>;
  face: {
    yawDegrees: number;
    pitchDegrees: number;
    rollDegrees: number;
    blendshapes: Record<string, number>;
  };
};

type MotionSample = MotionEventDetail & { sequence: number };

const MAX_DURATION_MS = 120_000;
const UI_REFRESH_MS = 250;
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export default function MotionCapture() {
  const samplesRef = useRef<MotionSample[]>([]);
  const startTimeRef = useRef<number | null>(null);
  const lastTimestampRef = useRef<number>(-1);
  const [recording, setRecording] = useState(false);
  const [sampleCount, setSampleCount] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnostics, setDiagnostics] = useState<Record<string, number> | null>(null);
  const [message, setMessage] = useState(
    "Start camera tracking before recording movement data."
  );

  useEffect(() => {
    let lastUiUpdate = 0;

    const onMotion = (event: Event) => {
      const startTime = startTimeRef.current;
      if (startTime === null) return;

      const detail = (event as CustomEvent<MotionEventDetail>).detail;
      if (!detail || !Number.isFinite(detail.timestampMs)) return;

      // Preserve every tracker sample in its original order. Do not smooth,
      // debounce, or delay facial blendshapes: blink and mouth peaks matter.
      if (detail.timestampMs <= lastTimestampRef.current) return;

      const elapsed = detail.timestampMs - startTime;
      if (elapsed < 0) return;

      if (elapsed >= MAX_DURATION_MS) {
        startTimeRef.current = null;
        setRecording(false);
        setElapsedMs(MAX_DURATION_MS);
        setMessage("Two-minute capture limit reached. Export your recording.");
        return;
      }

      if (samplesRef.current.length >= 3000) {
        startTimeRef.current = null;
        setRecording(false);
        setSampleCount(samplesRef.current.length);
        setMessage("The 3,000-sample backend diagnostics limit has been reached. Stop and run diagnostics.");
        return;
      }

      lastTimestampRef.current = detail.timestampMs;
      samplesRef.current.push({
        ...detail,
        timestampMs: Math.round(elapsed),
        sequence: samplesRef.current.length
      });

      // React UI refresh is throttled; the underlying motion samples are not.
      // This avoids causing a component rerender for every camera frame.
      if (detail.timestampMs - lastUiUpdate >= UI_REFRESH_MS) {
        lastUiUpdate = detail.timestampMs;
        setSampleCount(samplesRef.current.length);
        setElapsedMs(elapsed);
      }
    };

    window.addEventListener("speedy-live-pose", onMotion);
    return () => window.removeEventListener("speedy-live-pose", onMotion);
  }, []);

  function startRecording() {
    samplesRef.current = [];
    lastTimestampRef.current = -1;
    setSampleCount(0);
    setElapsedMs(0);
    startTimeRef.current = performance.now();
    setRecording(true);
    setMessage(
      "Capturing the latest available camera-tracker samples locally. Facial signals are kept unsmoothed."
    );
  }

  function stopRecording() {
    startTimeRef.current = null;
    setRecording(false);
    setSampleCount(samplesRef.current.length);
    setMessage(
      samplesRef.current.length
        ? "Capture stopped. Export the movement file to keep it."
        : "No movement samples were captured. Start camera tracking first."
    );
  }

  async function sendDiagnostics() {
    const samples = samplesRef.current;
    if (!samples.length || recording || diagnosing) return;
    setDiagnosing(true);
    setDiagnostics(null);
    setMessage("Sending movement landmarks to SPEEDY LIVE backend for diagnostics…");
    try {
      const response = await fetch(API_BASE + "/motion/diagnostics", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(samples.map((sample) => ({
          sequence: sample.sequence,
          timestamp_ms: sample.timestampMs,
          body_landmarks: sample.bodyLandmarks,
          hands: sample.hands,
          face: {
            yaw_degrees: sample.face.yawDegrees,
            pitch_degrees: sample.face.pitchDegrees,
            roll_degrees: sample.face.rollDegrees,
            blendshapes: sample.face.blendshapes
          }
        }))),
        signal: AbortSignal.timeout(20000)
      });
      const result = await response.json();
      if (!response.ok) {
        const detail = typeof result.detail === "string" ? result.detail : "HTTP " + response.status;
        throw new Error(detail);
      }
      setDiagnostics(result as Record<string, number>);
      setMessage("Backend diagnostics completed. This analyses motion data only; it does not animate the photograph.");
    } catch (error) {
      setMessage(error instanceof Error ? "Backend diagnostics unavailable: " + error.message : "Backend diagnostics unavailable. Check the backend URL and CORS settings.");
    } finally {
      setDiagnosing(false);
    }
  }

  function exportRecording() {
    if (!samplesRef.current.length) {
      setMessage("There is no movement data to export yet.");
      return;
    }

    const lastSample = samplesRef.current[samplesRef.current.length - 1];
    const payload = {
      format: "speedy-live-motion-capture",
      version: 2,
      createdAt: new Date().toISOString(),
      durationMs: lastSample.timestampMs,
      sampleCount: samplesRef.current.length,
      captureSource: "browser-mediapipe-tracker",
      timingPolicy: "raw-tracker-samples-no-added-smoothing-or-debounce",
      mediaUploaded: false,
      modelTrainingConsent: false,
      note: "Movement data only. No camera video or photograph is included.",
      samples: samplesRef.current
    };

    const blob = new Blob([JSON.stringify(payload)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `speedy-live-motion-${new Date()
      .toISOString()
      .replace(/[:.]/g, "-")}.json`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMessage("Movement JSON downloaded to your device.");
  }

  return (
    <section className="motion-capture-card">
      <div>
        <p className="eyebrow">INTERNAL RESEARCH TOOL</p>
        <h2>Movement data capture</h2>
        <p>
          Captures timestamped body, hand and facial controls locally.
          Facial signals are not intentionally delayed or smoothed, so short
          events such as blinks are preserved in the captured samples.
          This does not yet animate the uploaded photograph.
        </p>
      </div>

      <div className="motion-capture-stats">
        <div><span>Samples</span><strong>{sampleCount}</strong></div>
        <div><span>Duration</span><strong>{(elapsedMs / 1000).toFixed(1)}s</strong></div>
        <div><span>Limit</span><strong>120s</strong></div>
      </div>

      <div className="motion-capture-actions">
        {!recording ? (
          <button className="motion-start" onClick={startRecording}>
            Start capture
          </button>
        ) : (
          <button className="motion-stop" onClick={stopRecording}>
            Stop capture
          </button>
        )}
        <button
          className="motion-export"
          onClick={exportRecording}
          disabled={!sampleCount || recording}
        >
          Export movement JSON
        </button>
        <button className="motion-export" onClick={sendDiagnostics} disabled={!sampleCount || recording || diagnosing}>
          {diagnosing ? "Checking backend…" : "Run backend diagnostics"}
        </button>
      </div>
      {diagnostics && (
        <div className="motion-capture-stats" aria-live="polite">
          <div><span>Estimated FPS</span><strong>{Number(diagnostics.estimated_fps ?? 0).toFixed(1)}</strong></div>
          <div><span>Duration</span><strong>{(Number(diagnostics.duration_ms ?? 0) / 1000).toFixed(1)}s</strong></div>
          <div><span>Largest gap</span><strong>{diagnostics.max_gap_ms ?? 0}ms</strong></div>
        </div>
      )}
      <p className="motion-capture-message" aria-live="polite">{message}</p>
    </section>
  );
}

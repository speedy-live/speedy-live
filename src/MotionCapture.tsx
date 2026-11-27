import { useEffect, useRef, useState } from "react";
import "./motion-capture.css";

type MotionEventDetail = {
  timestampMs: number;
  bodyLandmarks: Array<{
    x: number;
    y: number;
    z: number;
    visibility: number | null;
  }>;
  hands: Array<{
    handedness: string;
    landmarks: Array<{
      x: number;
      y: number;
      z: number;
      visibility: number | null;
    }>;
  }>;
  face: {
    yawDegrees: number;
    pitchDegrees: number;
    rollDegrees: number;
    blendshapes: Record<string, number>;
  };
};

type MotionSample = MotionEventDetail & { sequence: number };

const MAX_DURATION_MS = 120_000;

export default function MotionCapture() {
  const samplesRef = useRef<MotionSample[]>([]);
  const startTimeRef = useRef<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [sampleCount, setSampleCount] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [message, setMessage] = useState(
    "Start camera tracking before recording movement data."
  );

  useEffect(() => {
    const onMotion = (event: Event) => {
      if (!startTimeRef.current) return;
      const detail = (event as CustomEvent<MotionEventDetail>).detail;
      const elapsed = detail.timestampMs - startTimeRef.current;
      if (elapsed < 0 || elapsed > MAX_DURATION_MS) {
        setRecording(false);
        startTimeRef.current = null;
        setMessage("Two-minute capture limit reached. Export your recording.");
        return;
      }
      samplesRef.current.push({
        ...detail,
        timestampMs: Math.round(elapsed),
        sequence: samplesRef.current.length
      });
      setSampleCount(samplesRef.current.length);
      setElapsedMs(elapsed);
    };

    window.addEventListener("speedy-live-pose", onMotion);
    return () => window.removeEventListener("speedy-live-pose", onMotion);
  }, []);

  function startRecording() {
    samplesRef.current = [];
    setSampleCount(0);
    setElapsedMs(0);
    startTimeRef.current = performance.now();
    setRecording(true);
    setMessage("Recording movement controls locally in this browser.");
  }

  function stopRecording() {
    startTimeRef.current = null;
    setRecording(false);
    setMessage(
      samplesRef.current.length
        ? "Capture stopped. Export the movement file to keep it."
        : "No movement samples were captured. Start camera tracking first."
    );
  }

  function exportRecording() {
    if (!samplesRef.current.length) {
      setMessage("There is no movement data to export yet.");
      return;
    }

    const payload = {
      format: "speedy-live-motion-capture",
      version: 1,
      createdAt: new Date().toISOString(),
      durationMs: elapsedMs,
      sampleCount: samplesRef.current.length,
      captureSource: "browser-mediapipe-tracker",
      mediaUploaded: false,
      modelTrainingConsent: false,
      note: "Movement data only. This file contains no camera video or photograph.",
      samples: samplesRef.current
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `speedy-live-motion-${new Date()
      .toISOString()
      .replace(/[:.]/g, "-")}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setMessage("Movement JSON downloaded to your device.");
  }

  return (
    <section className="motion-capture-card">
      <div>
        <p className="eyebrow">INTERNAL RESEARCH TOOL</p>
        <h2>Movement data capture</h2>
        <p>
          Capture timestamped body, hand and facial controls for internal
          research. This does not record camera video, upload photographs,
          train a model or animate an image.
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
      </div>
      <p className="motion-capture-message" aria-live="polite">{message}</p>
    </section>
  );
}

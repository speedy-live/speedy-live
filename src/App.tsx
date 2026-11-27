import { useEffect, useRef, useState } from "react";
import {
  FaceLandmarker,
  FilesetResolver,
  HandLandmarker,
  PoseLandmarker
} from "@mediapipe/tasks-vision";

type TrackerSet = {
  face: FaceLandmarker;
  pose: PoseLandmarker;
  hands: HandLandmarker;
};

type Metric = { label: string; value: string };

const MODEL_BASE = "https://storage.googleapis.com/mediapipe-models";
const WASM_BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";

const FACE_KEYS = [
  "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
  "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
  "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
  "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
  "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen", "jawRight",
  "mouthClose", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthLeft",
  "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
  "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper",
  "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight",
  "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight"
];

const POSE_NAMES = [
  "nose", "left_eye", "right_eye", "left_ear", "right_ear",
  "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
  "left_wrist", "right_wrist", "left_pinky", "right_pinky",
  "left_index", "right_index", "left_thumb", "right_thumb",
  "left_hip", "right_hip", "left_knee", "right_knee",
  "left_ankle", "right_ankle", "left_heel", "right_heel",
  "left_foot_index", "right_foot_index"
];

function percent(value?: number) {
  return typeof value === "number" ? Math.round(value * 100) + "%" : "—";
}

function getBlendshape(categories: any[] | undefined, name: string) {
  return categories?.find((item) => item.categoryName === name)?.score ?? 0;
}

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const trackersRef = useRef<TrackerSet | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastVideoTimeRef = useRef(-1);

  const [cameraOn, setCameraOn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Camera is off");
  const [error, setError] = useState("");
  const [faceFound, setFaceFound] = useState(false);
  const [poseFound, setPoseFound] = useState(false);
  const [handsFound, setHandsFound] = useState(0);
  const [mode, setMode] = useState<"half" | "full">("half");
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [poseMetrics, setPoseMetrics] = useState<string[]>([]);
  const [fps, setFps] = useState(0);

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      trackersRef.current?.face.close();
      trackersRef.current?.pose.close();
      trackersRef.current?.hands.close();
    };
  }, []);

  async function loadTrackers(): Promise<TrackerSet> {
    setStatus("Loading tracking models…");
    const vision = await FilesetResolver.forVisionTasks(WASM_BASE);

    const [face, pose, hands] = await Promise.all([
      FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: MODEL_BASE + "/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
          delegate: "GPU"
        },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true
      }),
      PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: MODEL_BASE + "/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
          delegate: "GPU"
        },
        runningMode: "VIDEO",
        numPoses: 1
      }),
      HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: MODEL_BASE + "/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
          delegate: "GPU"
        },
        runningMode: "VIDEO",
        numHands: 2
      })
    ]);

    return { face, pose, hands };
  }

  async function startCamera() {
    if (loading || cameraOn) return;
    setError("");
    setLoading(true);

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera access requires HTTPS and a supported browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30, max: 30 }
        }
      });
      streamRef.current = stream;

      const video = videoRef.current;
      if (!video) throw new Error("The camera preview could not be prepared.");
      video.srcObject = stream;
      await video.play();

      const trackers = await loadTrackers();
      trackersRef.current = trackers;
      setCameraOn(true);
      setStatus("Tracking is running");
      lastVideoTimeRef.current = -1;
      let frames = 0;
      let fpsStart = performance.now();

      const render = () => {
        const currentVideo = videoRef.current;
        const canvas = overlayRef.current;
        const active = trackersRef.current;
        if (!currentVideo || !canvas || !active || currentVideo.readyState < 2) {
          frameRef.current = requestAnimationFrame(render);
          return;
        }

        const now = performance.now();
        if (currentVideo.currentTime !== lastVideoTimeRef.current) {
          lastVideoTimeRef.current = currentVideo.currentTime;
          const faceResult = active.face.detectForVideo(currentVideo, now);
          const poseResult = active.pose.detectForVideo(currentVideo, now);
          const handResult = active.hands.detectForVideo(currentVideo, now);

          const faceCategories = faceResult.faceBlendshapes?.[0]?.categories;
          const foundFace = Boolean(faceResult.faceLandmarks?.length);
          const foundPose = Boolean(poseResult.landmarks?.length);
          const foundHands = handResult.landmarks?.length ?? 0;

          setFaceFound(foundFace);
          setPoseFound(foundPose);
          setHandsFound(foundHands);

          const keyMetrics: Metric[] = FACE_KEYS.map((key) => ({
            label: key,
            value: percent(getBlendshape(faceCategories, key))
          }));
          setMetrics(keyMetrics);

          const landmarks = poseResult.landmarks?.[0] ?? [];
          setPoseMetrics(POSE_NAMES.map((name, index) => {
            const point = landmarks[index];
            return point
              ? name + ": " + Math.round(point.x * 100) + "%, " + Math.round(point.y * 100) + "%"
              : name + ": —";
          }));

          const ctx = canvas.getContext("2d");
          if (ctx) {
            canvas.width = currentVideo.videoWidth;
            canvas.height = currentVideo.videoHeight;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            faceResult.faceLandmarks?.forEach((points) => {
              ctx.fillStyle = "#39d7ff";
              points.forEach((point) => {
                ctx.beginPath();
                ctx.arc(point.x * canvas.width, point.y * canvas.height, 1.3, 0, Math.PI * 2);
                ctx.fill();
              });
            });

            poseResult.landmarks?.forEach((points) => {
              ctx.fillStyle = "#a78bfa";
              points.forEach((point, index) => {
                if (point.visibility !== undefined && point.visibility < 0.35) return;
                if (mode === "half" && point.y > 0.72) return;
                ctx.beginPath();
                ctx.arc(point.x * canvas.width, point.y * canvas.height, 3, 0, Math.PI * 2);
                ctx.fill();
                if (POSE_NAMES[index]) {
                  ctx.fillStyle = "#ffffff";
                  ctx.font = "10px sans-serif";
                  ctx.fillText(POSE_NAMES[index], point.x * canvas.width + 4, point.y * canvas.height - 4);
                  ctx.fillStyle = "#a78bfa";
                }
              });
            });

            handResult.landmarks?.forEach((points) => {
              ctx.fillStyle = "#ffca70";
              points.forEach((point) => {
                ctx.beginPath();
                ctx.arc(point.x * canvas.width, point.y * canvas.height, 3, 0, Math.PI * 2);
                ctx.fill();
              });
            });
          }

          frames++;
          if (now - fpsStart >= 1000) {
            setFps(Math.round((frames * 1000) / (now - fpsStart)));
            frames = 0;
            fpsStart = now;
          }
        }
        frameRef.current = requestAnimationFrame(render);
      };

      frameRef.current = requestAnimationFrame(render);
    } catch (err) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      trackersRef.current?.face.close();
      trackersRef.current?.pose.close();
      trackersRef.current?.hands.close();
      trackersRef.current = null;
      setCameraOn(false);
      setStatus("Could not start tracking");
      setError(err instanceof Error ? err.message : "An unexpected camera or model error occurred.");
    } finally {
      setLoading(false);
    }
  }

  function stopCamera() {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    trackersRef.current?.face.close();
    trackersRef.current?.pose.close();
    trackersRef.current?.hands.close();
    trackersRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
    setFaceFound(false);
    setPoseFound(false);
    setHandsFound(0);
    setMetrics([]);
    setPoseMetrics([]);
    setFps(0);
    setStatus("Camera is off");
  }

  const importantMetrics = [
    "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "browDownLeft", "browDownRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft",
    "eyeLookDownLeft", "eyeWideLeft", "eyeSquintLeft", "jawOpen", "jawForward",
    "mouthClose", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthPucker", "mouthFunnel", "mouthLeft", "mouthRight", "mouthStretchLeft",
    "mouthStretchRight", "mouthUpperUpLeft", "mouthLowerDownLeft"
  ];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-mark">SL</div>
        <div>
          <p className="eyebrow">REAL-TIME AVATAR TECHNOLOGY</p>
          <h1>SPEEDY <span>LIVE</span></h1>
        </div>
        <div className="prototype-tag">MOVEMENT LAB · PROTOTYPE 01</div>
      </header>

      <section className="intro">
        <div>
          <p className="eyebrow">YOUR MOVEMENTS, CAPTURED TOGETHER</p>
          <h2>Full movement tracking starts here.</h2>
          <p className="intro-copy">
            Test facial expressions, mouth and jaw motion, eyes, eyebrows, head position,
            shoulders, torso, arms, hands, fingers, legs and feet.
          </p>
        </div>
        <div className="mode-switch" aria-label="Tracking display mode">
          <button className={mode === "half" ? "selected" : ""} onClick={() => setMode("half")}>Half body</button>
          <button className={mode === "full" ? "selected" : ""} onClick={() => setMode("full")}>Full body</button>
        </div>
      </section>

      <section className="workspace">
        <div className="preview-card">
          <div className="card-heading">
            <div><span className="live-dot" /> CAMERA TRACKING</div>
            <span>{fps} FPS</span>
          </div>
          <div className="camera-stage">
            <video ref={videoRef} className="camera-video" playsInline muted />
            <canvas ref={overlayRef} className="tracking-overlay" />
            {!cameraOn && <div className="camera-placeholder">
              <div className="camera-icon">◎</div>
              <strong>Your camera preview will appear here</strong>
              <span>Allow camera access when your browser asks.</span>
            </div>}
          </div>
          <div className="camera-actions">
            {!cameraOn ? (
              <button className="primary-button" onClick={startCamera} disabled={loading}>
                {loading ? "Preparing trackers…" : "Start camera & tracking"}
              </button>
            ) : (
              <button className="stop-button" onClick={stopCamera}>Stop camera</button>
            )}
            <span className="status-text">{status}</span>
          </div>
          {error && <p className="error-message">{error}</p>}
          <div className="detection-row">
            <span className={faceFound ? "detected" : ""}>Face {faceFound ? "detected" : "not found"}</span>
            <span className={poseFound ? "detected" : ""}>Body {poseFound ? "detected" : "not found"}</span>
            <span className={handsFound > 0 ? "detected" : ""}>{handsFound} hands detected</span>
          </div>
        </div>

        <div className="side-column">
          <div className="info-card">
            <p className="eyebrow">FACIAL CAPTURE</p>
            <h3>Face, eyes & mouth</h3>
            <p>Blendshape signals for eyebrows, eye direction, blinking, smiling, frowning, lips and jaw.</p>
            <div className="feature-pills">
              <span>Eyebrows</span><span>Head & gaze</span><span>Eye blink</span>
              <span>Smile / frown</span><span>Lip movement</span><span>Jaw opening</span>
            </div>
          </div>
          <div className="info-card">
            <p className="eyebrow">BODY CAPTURE</p>
            <h3>Body, arms & legs</h3>
            <p>Pose landmarks include shoulders, elbows, wrists, torso, hips, knees, ankles, heels and foot-index points.</p>
            <div className="feature-pills">
              <span>Shoulders</span><span>Torso</span><span>Arms</span>
              <span>Hands & fingers</span><span>Legs</span><span>Feet & toe-base</span>
            </div>
          </div>
          <div className="info-card note-card">
            <p className="eyebrow">IMPORTANT</p>
            <p>This prototype measures movement. A compatible 3D avatar rig is a later step. Individual toe articulation and exact gaze direction depend on visibility and model support.</p>
          </div>
        </div>
      </section>

      <section className="data-section">
        <div className="section-title">
          <div><p className="eyebrow">LIVE SIGNALS</p><h2>Facial movement values</h2></div>
          <span>Updates while tracking is active</span>
        </div>
        <div className="metric-grid">
          {importantMetrics.map((key) => {
            const item = metrics.find((metric) => metric.label === key);
            return <div className="metric" key={key}><span>{key}</span><strong>{item?.value ?? "—"}</strong></div>;
          })}
        </div>
      </section>

      <section className="data-section">
        <div className="section-title">
          <div><p className="eyebrow">BODY LANDMARKS</p><h2>Pose tracking</h2></div>
          <span>Positions are normalized to the camera frame</span>
        </div>
        <div className="pose-grid">
          {poseMetrics.map((value) => <div className="pose-item" key={value}>{value}</div>)}
        </div>
      </section>

      <footer>
        <span>SPEEDY LIVE · MOVEMENT TRACKING PROTOTYPE</span>
        <span>Camera processing runs in this browser. No recording or upload is implemented.</span>
      </footer>
    </main>
  );
}
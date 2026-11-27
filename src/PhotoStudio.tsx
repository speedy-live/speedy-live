import { useEffect, useRef, useState } from "react";
import "./photo-studio.css";

type AnimationMode = "portrait" | "full-body";

export default function PhotoStudio() {
  const inputRef = useRef<HTMLInputElement>(null);
  const imageUrlRef = useRef<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageName, setImageName] = useState("");
  const [imageSize, setImageSize] = useState("");
  const [dimensions, setDimensions] = useState("");
  const [mode, setMode] = useState<AnimationMode>("portrait");
  const [checkMessage, setCheckMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => () => {
    if (imageUrlRef.current) URL.revokeObjectURL(imageUrlRef.current);
  }, []);

  function chooseImage() {
    setError("");
    inputRef.current?.click();
  }

  function handleImageChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image.");
      event.target.value = "";
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Please choose an image smaller than 10 MB.");
      event.target.value = "";
      return;
    }

    const newUrl = URL.createObjectURL(file);
    const probe = new Image();
    probe.onload = () => {
      setDimensions(`${probe.naturalWidth} × ${probe.naturalHeight} px`);
      setCheckMessage("Image loaded locally. Choose a mode and run the preparation check.");
    };
    probe.onerror = () => {
      setError("This image could not be opened. Try another image.");
      URL.revokeObjectURL(newUrl);
    };
    probe.src = newUrl;

    if (imageUrlRef.current) URL.revokeObjectURL(imageUrlRef.current);
    imageUrlRef.current = newUrl;
    setImageUrl(newUrl);
    setImageName(file.name);
    setImageSize((file.size / (1024 * 1024)).toFixed(2) + " MB");
    setCheckMessage("");
    setError("");
    event.target.value = "";
  }

  function removeImage() {
    if (imageUrlRef.current) URL.revokeObjectURL(imageUrlRef.current);
    imageUrlRef.current = null;
    setImageUrl(null);
    setImageName("");
    setImageSize("");
    setDimensions("");
    setCheckMessage("");
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  function runPreparationCheck() {
    if (!imageUrl) {
      setCheckMessage("Upload an image before running the check.");
      return;
    }
    const image = new Image();
    image.onload = () => {
      const ratio = image.naturalWidth / image.naturalHeight;
      const minimum = mode === "portrait" ? 512 : 640;
      const enoughPixels = Math.min(image.naturalWidth, image.naturalHeight) >= minimum;
      const shapeSuitable = mode === "portrait" ? ratio <= 1.15 : ratio >= 0.45;
      const notes = [
        enoughPixels ? "Resolution: suitable for an initial review." : "Resolution: low; a larger image is recommended.",
        shapeSuitable ? "Shape: compatible with the selected framing." : "Shape: consider a different crop for this mode."
      ];
      setCheckMessage(notes.join(" "));
    };
    image.src = imageUrl;
  }

  async function openFullscreen() {
    const stage = document.getElementById("speedy-live-photo-stage");
    if (!stage) return;
    try {
      if (!document.fullscreenElement) await stage.requestFullscreen();
      else await document.exitFullscreen();
    } catch {
      setError("Full screen is not available in this browser.");
    }
  }

  return (
    <section className="photo-studio">
      <div className="photo-studio-heading">
        <div>
          <p className="eyebrow">YOUR DIGITAL APPEARANCE</p>
          <h2>Photo animation studio</h2>
          <p>Select a photograph and prepare it for a portrait or full-body animation workflow.</p>
        </div>
        <span className="photo-status">{imageUrl ? "IMAGE SELECTED" : "NO IMAGE SELECTED"}</span>
      </div>

      <input ref={inputRef} type="file" accept="image/*" hidden onChange={handleImageChange} />

      <div className="photo-mode-picker" aria-label="Animation framing mode">
        <button type="button" className={mode === "portrait" ? "selected" : ""} onClick={() => { setMode("portrait"); setCheckMessage(""); }}>
          <strong>Portrait animation</strong><span>Face, expressions and head movement</span>
        </button>
        <button type="button" className={mode === "full-body" ? "selected" : ""} onClick={() => { setMode("full-body"); setCheckMessage(""); }}>
          <strong>Full-body animation</strong><span>Head, torso, arms and legs</span>
        </button>
      </div>

      <div id="speedy-live-photo-stage" className={`photo-stage ${mode === "full-body" ? "full-body-stage" : "portrait-stage"}`}>
        {imageUrl ? (
          <img src={imageUrl} alt="Your selected photograph preview" className="selected-human-image" />
        ) : (
          <div className="photo-empty">
            <div className="photo-empty-icon">＋</div>
            <h3>No photograph selected</h3>
            <p>Choose a clear photograph you own or have permission to use.</p>
            <button className="photo-primary-button" onClick={chooseImage}>Upload Image</button>
          </div>
        )}
      </div>

      {imageUrl && <>
        <div className="photo-file-name">
          <span><strong>File:</strong> {imageName}</span>
          <span><strong>Size:</strong> {imageSize}</span>
          <span><strong>Dimensions:</strong> {dimensions || "Reading…"}</span>
        </div>
        <div className="photo-actions">
          <button className="photo-primary-button" onClick={chooseImage}>Replace Image</button>
          <button className="photo-secondary-button" onClick={runPreparationCheck}>Check image preparation</button>
          <button className="photo-secondary-button" onClick={openFullscreen}>Full Screen</button>
          <button className="photo-secondary-button" onClick={removeImage}>Remove Image</button>
        </div>
      </>}

      {error && <p className="photo-error" role="alert">{error}</p>}
      {checkMessage && <div className="photo-check-result" aria-live="polite"><strong>Preparation check</strong><p>{checkMessage}</p></div>}

      <div className="photo-information">
        <strong>Development preview — not AI animation yet</strong>
        <p>Your photo is previewed locally in this browser. The preparation check only reviews image resolution and framing; it does not detect a face, animate the photo, upload it, or send it for model training. Real animation remains disabled until a qualified model is installed and approved.</p>
      </div>
    </section>
  );
}

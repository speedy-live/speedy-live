import { useEffect, useRef, useState } from "react";
import "./photo-studio.css";

export default function PhotoStudio() {
  const inputRef = useRef<HTMLInputElement>(null);
  const imageUrlRef = useRef<string | null>(null);

  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageName, setImageName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    return () => {
      if (imageUrlRef.current) {
        URL.revokeObjectURL(imageUrlRef.current);
      }
    };
  }, []);

  function chooseImage() {
    setError("");
    inputRef.current?.click();
  }

  function handleImageChange(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
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

    if (imageUrlRef.current) {
      URL.revokeObjectURL(imageUrlRef.current);
    }

    imageUrlRef.current = newUrl;

    setImageUrl(newUrl);
    setImageName(file.name);
    setError("");

    event.target.value = "";
  }

  function removeImage() {
    if (imageUrlRef.current) {
      URL.revokeObjectURL(imageUrlRef.current);
    }

    imageUrlRef.current = null;

    setImageUrl(null);
    setImageName("");
    setError("");

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function openFullscreen() {
    const stage = document.getElementById("speedy-live-photo-stage");

    if (!stage) return;

    try {
      if (!document.fullscreenElement) {
        await stage.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      setError("Full screen is not available in this browser.");
    }
  }

  return (
    <section className="photo-studio">
      <div className="photo-studio-heading">
        <div>
          <p className="eyebrow">YOUR DIGITAL APPEARANCE</p>
          <h2>Choose your human image</h2>
          <p>
            Upload a photograph you own or have permission to use.
            You can replace or remove it whenever you want.
          </p>
        </div>

        <span className="photo-status">
          {imageUrl ? "IMAGE SELECTED" : "NO IMAGE SELECTED"}
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={handleImageChange}
      />

      <div
        id="speedy-live-photo-stage"
        className="photo-stage"
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Your selected human image"
            className="selected-human-image"
          />
        ) : (
          <div className="photo-empty">
            <div className="photo-empty-icon">＋</div>
            <h3>No photograph selected</h3>
            <p>
              Upload a human photograph to prepare your
              animated image.
            </p>
            <button
              className="photo-primary-button"
              onClick={chooseImage}
            >
              Upload Image
            </button>
          </div>
        )}
      </div>

      {imageUrl && (
        <>
          <div className="photo-file-name">
            Selected image: {imageName}
          </div>

          <div className="photo-actions">
            <button
              className="photo-primary-button"
              onClick={chooseImage}
            >
              Replace Image
            </button>

            <button
              className="photo-secondary-button"
              onClick={removeImage}
            >
              Remove Image
            </button>

            <button
              className="photo-secondary-button"
              onClick={openFullscreen}
            >
              Full Screen
            </button>
          </div>
        </>
      )}

      {error && (
        <p className="photo-error">{error}</p>
      )}

      <div className="photo-information">
        <strong>Animation preparation</strong>
        <p>
          This preview currently displays your selected photograph.
          Realistic facial animation and movement transfer will be
          connected in the next development stage.
        </p>
      </div>
    </section>
  );
}

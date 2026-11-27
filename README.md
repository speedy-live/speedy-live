# SPEEDY LIVE — Movement Lab

The first standalone prototype for SPEEDY LIVE. It tests browser-based face, pose, and hand landmark tracking before a 3D avatar is connected.

## Current prototype

- Face Landmarker with facial blendshape output for eyebrow, eye, blink, smile, frown, lip, and jaw signals.
- Pose Landmarker for upper-body and lower-body landmarks, including shoulders, elbows, wrists, hips, knees, ankles, heels, and foot-index points.
- Hand Landmarker for both hands and finger landmarks.
- Half-body and full-body display modes.
- Camera access begins only after the user presses **Start camera & tracking**.

## Run locally

Requirements: Node.js 20 or newer and npm.

```bash
npm install
npm run dev
```

Open the local address printed by Vite. Camera access requires localhost or HTTPS and the user's permission.

To create a production build:

```bash
npm run build
```

## Important limitations

This is a tracking and signal-inspection prototype, not a finished avatar or calling application. It does not yet animate a 3D avatar, create an avatar from a photo, or provide WebRTC calling.

The next development stage must connect face blendshapes to a compatible facial rig and pose/hand landmarks to a compatible body and hand skeleton. Individual toe articulation, exact gaze estimation, and head rotation quality depend on camera framing, visibility, model support, and validation.

Camera video is processed in the browser in this prototype. Recording, uploading, user accounts, and calling are not implemented.

## Project direction

SPEEDY LIVE is being developed independently. Do not connect this repository to or modify the separate SPEEDY.NG production project.

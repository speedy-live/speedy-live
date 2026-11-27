import { useEffect, useRef } from "react";
import * as THREE from "three";
import "./avatar-preview.css";

type Landmark = {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
};

type PoseMessage = {
  timestampMs: number;
  bodyLandmarks: Landmark[];
  hands: Array<{ handedness: string; landmarks: Landmark[] }>;
  face: {
    yawDegrees: number;
    pitchDegrees: number;
    rollDegrees: number;
    blendshapes: Record<string, number>;
  };
};

type Props = {
  mode: "half" | "full";
  tracking: boolean;
};

const LINKS: [number, number, string][] = [
  [11, 12, "shoulders"],
  [11, 13, "leftUpperArm"],
  [13, 15, "leftForearm"],
  [12, 14, "rightUpperArm"],
  [14, 16, "rightForearm"],
  [11, 23, "leftTorso"],
  [12, 24, "rightTorso"],
  [23, 24, "hips"],
  [23, 25, "leftThigh"],
  [25, 27, "leftShin"],
  [24, 26, "rightThigh"],
  [26, 28, "rightShin"]
];

function pointToVector(point: Landmark) {
  return new THREE.Vector3(
    (0.5 - point.x) * 3.2,
    (0.5 - point.y) * 4,
    -(point.z ?? 0) * 2
  );
}

export default function AvatarPreview({ mode, tracking }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const latestPose = useRef<PoseMessage | null>(null);

  useEffect(() => {
    const hostElement = hostRef.current;
    if (!hostElement) return;
    const host: HTMLDivElement = hostElement;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#081426");

    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0, 8);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x263b65, 2));

    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(3, 5, 6);
    scene.add(light);

    const bodyMaterial = new THREE.MeshStandardMaterial({ color: "#38bdf8", roughness: 0.65 });
    const jointMaterial = new THREE.MeshStandardMaterial({ color: "#a5dfff", roughness: 0.55 });
    const headMaterial = new THREE.MeshStandardMaterial({ color: "#e5b995", roughness: 0.8 });
    const boneGeometry = new THREE.CylinderGeometry(1, 1, 1, 12);
    const boneMeshes: Record<string, THREE.Mesh> = {};

    LINKS.forEach(([, , name]) => {
      const bone = new THREE.Mesh(boneGeometry, bodyMaterial);
      scene.add(bone);
      boneMeshes[name] = bone;
    });

    const joints: THREE.Mesh[] = [];
    for (let i = 0; i < 13; i++) {
      const joint = new THREE.Mesh(
        new THREE.SphereGeometry(0.09, 16, 12),
        jointMaterial
      );
      scene.add(joint);
      joints.push(joint);
    }

    const torso = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 20, 16),
      bodyMaterial
    );
    scene.add(torso);

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.3, 24, 20),
      headMaterial
    );
    scene.add(head);

    function resize() {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    }

    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    function moveBone(bone: THREE.Mesh, start: THREE.Vector3, end: THREE.Vector3) {
      const direction = new THREE.Vector3().subVectors(end, start);
      const length = direction.length();
      bone.position.copy(start).add(end).multiplyScalar(0.5);
      bone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
      bone.scale.set(0.09, Math.max(length, 0.01), 0.09);
    }

    function updateAvatar(data: PoseMessage) {
      const landmarks = data.bodyLandmarks;
      const getPoint = (index: number) => {
        const point = landmarks[index];
        if (!point || (point.visibility !== undefined && point.visibility < 0.35)) {
          return null;
        }
        return pointToVector(point);
      };

      LINKS.forEach(([startIndex, endIndex, name]) => {
        const start = getPoint(startIndex);
        const end = getPoint(endIndex);
        const bone = boneMeshes[name];
        if (!start || !end) {
          bone.visible = false;
          return;
        }
        if (mode === "half" && ["leftThigh", "leftShin", "rightThigh", "rightShin"].includes(name)) {
          bone.visible = false;
          return;
        }
        bone.visible = true;
        moveBone(bone, start, end);
      });

      const visiblePoints = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 0];
      visiblePoints.forEach((index, i) => {
        const point = getPoint(index);
        if (!point || (mode === "half" && index >= 25)) {
          joints[i].visible = false;
          return;
        }
        joints[i].visible = true;
        joints[i].position.copy(point);
      });

      const leftShoulder = getPoint(11);
      const rightShoulder = getPoint(12);
      const nose = getPoint(0);

      if (leftShoulder && rightShoulder) {
        torso.position.copy(leftShoulder).add(rightShoulder).multiplyScalar(0.5);
        torso.visible = true;
      } else {
        torso.visible = false;
      }

      if (nose) {
        head.position.copy(nose);
        head.position.y += 0.25;
        const safeAngle = (value: number) => Number.isFinite(value) ? value : 0;
        head.rotation.set(
          THREE.MathUtils.degToRad(safeAngle(data.face.pitchDegrees)),
          THREE.MathUtils.degToRad(safeAngle(data.face.yawDegrees)),
          THREE.MathUtils.degToRad(safeAngle(data.face.rollDegrees))
        );
        head.visible = true;
      } else {
        head.visible = false;
      }
    }

    const handlePose = (event: Event) => {
      const customEvent = event as CustomEvent<PoseMessage>;
      const detail = customEvent.detail;
      if (
        !detail ||
        !Number.isFinite(detail.timestampMs) ||
        !Array.isArray(detail.bodyLandmarks) ||
        !detail.face
      ) return;
      latestPose.current = detail;
    };

    window.addEventListener("speedy-live-pose", handlePose);

    let animationFrame = 0;
    function animate() {
      animationFrame = requestAnimationFrame(animate);
      if (latestPose.current) updateAvatar(latestPose.current);
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("speedy-live-pose", handlePose);
      observer.disconnect();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) object.geometry.dispose();
      });
      bodyMaterial.dispose();
      jointMaterial.dispose();
      headMaterial.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === host) host.removeChild(renderer.domElement);
    };
  }, [mode]);

  return (
    <div className="avatar-preview-card">
      <div className="avatar-preview-heading">
        <strong>3D TRACKING DIAGNOSTIC</strong>
        <span>{tracking ? "MOVEMENT LINK ACTIVE" : "WAITING FOR CAMERA"}</span>
      </div>
      <div className="avatar-preview-stage" ref={hostRef}>
        {!tracking && (
          <div className="avatar-preview-message">
            Start camera tracking to view the diagnostic landmark rig.
          </div>
        )}
      </div>
      <p className="avatar-preview-note">
        Diagnostic landmark visualization only. This is not the uploaded-photo animation engine.
      </p>
    </div>
  );
}

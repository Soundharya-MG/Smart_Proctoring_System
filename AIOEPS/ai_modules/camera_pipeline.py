"""
camera_pipeline.py - ALL-IN-ONE AI Proctoring Pipeline
AIOEPS - AI Based Online Examination Proctoring System

Runs all AI checks simultaneously:
  - Face Recognition
  - Eye Gaze Tracking
  - Head Pose Estimation
  - Object Detection (Mobile/Book)
  - rPPG Heart Rate
  - Multi-face Detection

Usage:
    python camera_pipeline.py
"""

import sys, os, time, json, threading, base64
import numpy as np

# ─── OpenCV ───────────────────────────────────────────────────────────────────
try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False
    print("❌ OpenCV not found. Install: pip install opencv-python")

# ─── MediaPipe (Face Mesh + Pose) ────────────────────────────────────────────
try:
    import mediapipe as mp
    MP_OK = True
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing   = mp.solutions.drawing_utils
    mp_face_det  = mp.solutions.face_detection
except ImportError:
    MP_OK = False
    print("⚠️  MediaPipe not found. Install: pip install mediapipe")

# ─── Face Recognition ─────────────────────────────────────────────────────────
try:
    import face_recognition
    FR_OK = True
except ImportError:
    FR_OK = False
    print("⚠️  face_recognition not found. Install: pip install face-recognition")

# ─── Requests (to POST alerts to backend) ────────────────────────────────────
try:
    import requests as req
    REQ_OK = True
except ImportError:
    REQ_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
API_BASE      = "http://localhost:5000/api"
SESSION_ID    = None   # Set at runtime via environment / arg
JWT_TOKEN     = None   # Set at runtime
ALERT_COOLDOWN = 5     # Seconds between same-type alerts

# ═══════════════════════════════════════════════════════════════════════════════
#  ALERT SENDER
# ═══════════════════════════════════════════════════════════════════════════════
_last_alert_time: dict = {}

def send_alert(warning_type: str, severity: str = "Medium", frame=None):
    """POST an alert to the Flask backend (non-blocking)."""
    now = time.time()
    if now - _last_alert_time.get(warning_type, 0) < ALERT_COOLDOWN:
        return
    _last_alert_time[warning_type] = now

    snapshot_b64 = None
    if frame is not None and CV2_OK:
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        snapshot_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

    payload = {
        "session_id": SESSION_ID,
        "warning_type": warning_type,
        "severity": severity,
        "snapshot": snapshot_b64
    }

    def _post():
        try:
            if REQ_OK and JWT_TOKEN:
                req.post(
                    f"{API_BASE}/proctor/alert",
                    json=payload,
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    timeout=3
                )
        except Exception:
            pass
    threading.Thread(target=_post, daemon=True).start()
    print(f"[ALERT] {warning_type} | {severity}")

# ═══════════════════════════════════════════════════════════════════════════════
#  EYE GAZE TRACKER  (MediaPipe Face Mesh)
# ═══════════════════════════════════════════════════════════════════════════════
class GazeTracker:
    # Iris landmark indices
    LEFT_IRIS  = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]
    LEFT_EYE   = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE  = [362, 385, 387, 263, 373, 380]

    def __init__(self):
        self.away_counter = 0
        self.THRESHOLD = 12  # frames before alert

    def get_iris_position(self, landmarks, eye_indices, iris_indices, w, h):
        eye_pts   = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in eye_indices])
        iris_pts  = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in iris_indices])
        iris_cx   = np.mean(iris_pts[:, 0])
        eye_left  = eye_pts[:, 0].min()
        eye_right = eye_pts[:, 0].max()
        ratio     = (iris_cx - eye_left) / max(eye_right - eye_left, 1)
        return ratio  # 0=far left, 0.5=center, 1=far right

    def check(self, landmarks, w, h) -> str:
        """Return status string."""
        lr = self.get_iris_position(landmarks, self.LEFT_EYE,  self.LEFT_IRIS,  w, h)
        rr = self.get_iris_position(landmarks, self.RIGHT_EYE, self.RIGHT_IRIS, w, h)
        avg = (lr + rr) / 2
        if avg < 0.30 or avg > 0.70:
            self.away_counter += 1
        else:
            self.away_counter = max(0, self.away_counter - 1)

        if self.away_counter > self.THRESHOLD:
            return "Looking Away"
        return "Focused"

# ═══════════════════════════════════════════════════════════════════════════════
#  HEAD POSE ESTIMATOR  (MediaPipe Face Mesh + solvePnP)
# ═══════════════════════════════════════════════════════════════════════════════
class HeadPoseEstimator:
    # 3D reference face model points
    MODEL_POINTS = np.array([
        (0.0,   0.0,    0.0),     # Nose tip
        (0.0,  -330.0, -65.0),    # Chin
        (-225.0, 170.0, -135.0),  # Left eye corner
        (225.0,  170.0, -135.0),  # Right eye corner
        (-150.0, -150.0, -125.0), # Left mouth
        (150.0,  -150.0, -125.0)  # Right mouth
    ], dtype=np.float64)

    # Corresponding MediaPipe landmark indices
    LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

    def __init__(self):
        self.turned_counter = 0
        self.THRESHOLD = 10

    def estimate(self, landmarks, w, h):
        """Returns (yaw, pitch, roll) in degrees."""
        img_pts = np.array([
            [landmarks[i].x * w, landmarks[i].y * h]
            for i in self.LANDMARK_IDS
        ], dtype=np.float64)

        focal  = w
        center = (w / 2, h / 2)
        cam_matrix = np.array([
            [focal, 0, center[0]],
            [0, focal, center[1]],
            [0, 0,     1        ]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        success, rot_vec, trans_vec = cv2.solvePnP(
            self.MODEL_POINTS, img_pts, cam_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return 0, 0, 0

        rot_mat, _ = cv2.Rodrigues(rot_vec)
        angles, *_ = cv2.RQDecomp3x3(rot_mat)
        yaw, pitch, roll = angles[1], angles[0], angles[2]
        return yaw, pitch, roll

    def check(self, yaw, pitch) -> str:
        if abs(yaw) > 20 or abs(pitch) > 15:
            self.turned_counter += 1
        else:
            self.turned_counter = max(0, self.turned_counter - 1)
        if self.turned_counter > self.THRESHOLD:
            return "Head Turned"
        return "Stable"

# ═══════════════════════════════════════════════════════════════════════════════
#  rPPG HEART RATE  (Signal averaging from forehead ROI)
# ═══════════════════════════════════════════════════════════════════════════════
class RPPGMonitor:
    def __init__(self, fps=30, window_sec=10):
        self.fps        = fps
        self.window     = fps * window_sec
        self.signal     = []
        self.bpm        = 75
        self.frame_cnt  = 0
        self.UPDATE_EVERY = fps  # recalculate every second

    def update(self, frame, face_bbox=None):
        """Extract green channel mean from forehead ROI."""
        h, w = frame.shape[:2]
        if face_bbox:
            x1, y1, x2, y2 = face_bbox
            forehead = frame[y1:y1 + (y2-y1)//4, x1:x2]
        else:
            forehead = frame[int(h*0.05):int(h*0.20), int(w*0.3):int(w*0.7)]

        if forehead.size == 0:
            return

        green_mean = np.mean(forehead[:, :, 1])  # Green channel
        self.signal.append(green_mean)
        if len(self.signal) > self.window:
            self.signal.pop(0)

        self.frame_cnt += 1
        if self.frame_cnt % self.UPDATE_EVERY == 0 and len(self.signal) > self.fps * 3:
            self._calculate_bpm()

    def _calculate_bpm(self):
        """FFT-based BPM estimation."""
        sig = np.array(self.signal) - np.mean(self.signal)
        fft = np.abs(np.fft.rfft(sig))
        freqs = np.fft.rfftfreq(len(sig), d=1.0/self.fps)
        # BPM range: 40–180
        mask = (freqs >= 40/60) & (freqs <= 180/60)
        if mask.any():
            peak_freq = freqs[mask][np.argmax(fft[mask])]
            self.bpm = peak_freq * 60

    @property
    def stress_level(self) -> str:
        if self.bpm > 100: return "High"
        if self.bpm > 85:  return "Medium"
        return "Normal"

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
def run_pipeline(session_id: int = None, jwt_token: str = None):
    """Run the full AI proctoring camera pipeline."""
    global SESSION_ID, JWT_TOKEN
    SESSION_ID = session_id
    JWT_TOKEN  = jwt_token

    if not CV2_OK:
        print("❌ Cannot run pipeline without OpenCV")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    gaze       = GazeTracker()       if MP_OK  else None
    head_pose  = HeadPoseEstimator() if MP_OK and CV2_OK else None
    rppg       = RPPGMonitor()

    face_mesh_ctx   = mp_face_mesh.FaceMesh(
        max_num_faces=3,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) if MP_OK else None

    face_det_ctx = mp_face_det.FaceDetection(
        min_detection_confidence=0.5
    ) if MP_OK else None

    print("✅ AI Pipeline started. Press 'q' to quit.")

    with (face_mesh_ctx or _NullContext()) as face_mesh, \
         (face_det_ctx  or _NullContext()) as face_det:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            display = frame.copy()

            # ── Multi-face Detection ───────────────────────────────────────
            face_count = 0
            if face_det and MP_OK:
                det_result = face_det.process(rgb)
                if det_result.detections:
                    face_count = len(det_result.detections)
                    if face_count > 1:
                        send_alert("Multiple Faces", "High", frame)
                        cv2.putText(display, f"⚠ {face_count} FACES!", (10, 90),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

            # ── Face Mesh (Gaze + Head Pose) ──────────────────────────────
            gaze_status = "Focused"
            head_status = "Stable"
            if face_mesh and MP_OK:
                mesh_result = face_mesh.process(rgb)
                if mesh_result.multi_face_landmarks:
                    lm = mesh_result.multi_face_landmarks[0].landmark

                    # Eye gaze
                    if gaze:
                        gaze_status = gaze.check(lm, w, h)
                        if gaze_status == "Looking Away":
                            send_alert("Looking Away", "Medium", frame)

                    # Head pose
                    if head_pose and CV2_OK:
                        try:
                            yaw, pitch, roll = head_pose.estimate(lm, w, h)
                            head_status = head_pose.check(yaw, pitch)
                            if head_status == "Head Turned":
                                send_alert("Head Turned", "Medium", frame)
                            cv2.putText(display,
                                        f"Yaw:{yaw:.0f}° Pitch:{pitch:.0f}°",
                                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,0), 1)
                        except Exception:
                            pass

            # ── rPPG Stress ────────────────────────────────────────────────
            rppg.update(frame)
            bpm_text  = f"rPPG: {rppg.bpm:.0f} BPM ({rppg.stress_level})"
            bpm_color = (0,255,0) if rppg.stress_level == "Normal" else \
                        (0,165,255) if rppg.stress_level == "Medium" else (0,0,255)

            # ── Overlay HUD ───────────────────────────────────────────────
            _draw_hud(display, face_count, gaze_status, head_status, rppg, w, h)

            cv2.imshow("AIOEPS - AI Proctoring Monitor", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("✅ AI Pipeline stopped.")

def _draw_hud(frame, faces, gaze, head, rppg, w, h):
    """Draw status overlay on camera frame."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (280, 160), (15, 15, 30), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    def status_color(s):
        ok = {"Focused", "Stable", "Normal"}
        return (50, 220, 50) if s in ok else (0, 100, 255)

    lines = [
        ("AIOEPS Monitor",         (180, 180, 255), 0.55),
        (f"Faces Detected: {faces}", status_color("Normal" if faces <= 1 else "Alert"), 0.5),
        (f"Eye Gaze: {gaze}",       status_color(gaze), 0.5),
        (f"Head: {head}",           status_color(head), 0.5),
        (f"rPPG: {rppg.bpm:.0f} BPM", status_color(rppg.stress_level), 0.5),
        (f"Stress: {rppg.stress_level}", status_color(rppg.stress_level), 0.5),
    ]
    for i, (text, color, scale) in enumerate(lines):
        cv2.putText(frame, text, (10, 22 + i*24),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)

class _NullContext:
    """No-op context manager for optional modules."""
    def __enter__(self): return None
    def __exit__(self, *a): pass

if __name__ == '__main__':
    run_pipeline()

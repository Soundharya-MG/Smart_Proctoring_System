# 🛡️ AIOEPS — AI Based Online Examination Proctoring System

> **Final Year Project** | AI + ML + Full Stack | Flask + OpenCV + MediaPipe + YOLOv8

---

## 📸 Features

| Feature | Technology |
|---|---|
| 👤 Face Recognition | `face_recognition` + `dlib` |
| 👀 Eye Gaze Tracking | MediaPipe FaceMesh |
| 🤦 Head Pose Estimation | MediaPipe + OpenCV solvePnP |
| ❤️ Stress Detection (rPPG) | Green-channel FFT |
| 📱 Object Detection | YOLOv8 (ultralytics) |
| ⌨️ Keystroke Dynamics | Custom ML model |
| 🎤 Voice Detection | PyAudio + NumPy |
| 🔒 Tab/Copy Prevention | JavaScript Security |
| 🔗 Federated Learning | FedAvg (privacy-preserving) |
| 📊 Reports | ReportLab PDF |
| 🌐 REST API | Flask + JWT |
| 💾 Database | SQLite + SQLAlchemy |

---

## 📁 Project Structure

```
ai-proctoring-system/
├── backend/           ⚙️  Flask REST API
│   ├── app.py         ⭐ Entry point
│   ├── config.py
│   ├── requirements.txt
│   ├── database/      💾 SQLite + ORM
│   ├── routes/        🌐 API endpoints
│   ├── services/      🧠 Business logic
│   └── utils/         🛠️ Helpers
├── ai_modules/        🤖 All AI/ML code
│   ├── camera_pipeline.py  ⭐ All-in-one pipeline
│   ├── face_recognition/
│   ├── eye_tracking/
│   ├── head_pose/
│   ├── object_detection/
│   ├── rppg/
│   └── voice_detection/
├── frontend/          🌐 HTML/CSS/JS UI
│   ├── index.html     🏠 Landing + Login
│   ├── student/       👨‍🎓 Student panel
│   ├── admin/         👨‍💼 Admin panel
│   ├── css/style.css
│   └── js/auth.js
├── federated_learning/ 🔗 FL client + server
├── dataset/           📁 Student face images
├── models/            📦 Trained models
├── uploads/           📂 Runtime files
└── logs/              📊 System logs
```

---

## ⚡ Quick Setup (Step-by-Step)

### ✅ STEP 1 — Prerequisites

Install these first:
- [Python 3.10+](https://python.org/downloads)
- [Visual Studio Code](https://code.visualstudio.com)
- [Git](https://git-scm.com) *(optional)*

> **Windows users:** Also install [CMake](https://cmake.org/download/) and
> [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
> (required for `dlib`)

---

### ✅ STEP 2 — Open in VS Code

```bash
# Open the project folder in VS Code
code ai-proctoring-system
```

Or: **File → Open Folder** → select `ai-proctoring-system`

---

### ✅ STEP 3 — Create Virtual Environment

Open **Terminal** in VS Code (`Ctrl+`` ` ``):

```bash
# Go to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

---

### ✅ STEP 4 — Install Dependencies

```bash
# Install all packages (inside backend/ with venv active)
pip install -r requirements.txt
```

> ⚠️ `dlib` can take 5–10 minutes to compile.
> If it fails on Windows, install the pre-built wheel:
> ```
> pip install dlib==19.24.2 --find-links https://github.com/jloh02/dlib/releases
> ```

---

### ✅ STEP 5 — Run the Backend Server

```bash
# Make sure you're in backend/ with venv active
python app.py
```

You should see:
```
✅ Database initialized from schema.sql
✅ Sample data seeded
============================================================
  🛡️  AIOEPS - AI Proctoring System
  🌐  http://localhost:5000
  📋  API: http://localhost:5000/api/health
============================================================
```

---

### ✅ STEP 6 — Open the Frontend

Open your browser and go to:
```
http://localhost:5000
```

The Flask server serves the frontend automatically.

---

### ✅ STEP 7 — Login Credentials

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@aioeps.com` | `admin123` |
| **Student** | Register a new account | Your password |

---

## 🤖 Run AI Camera Pipeline (Optional)

In a **new terminal** (with venv active):

```bash
cd ai_modules
python camera_pipeline.py
```

This opens your webcam with live:
- Face detection
- Eye gaze tracking
- Head pose estimation
- rPPG heart rate monitoring

Press `q` to quit.

---

## 📷 Register Student Face

```bash
cd ai_modules/face_recognition
python capture_dataset.py --student_id YOUR_STUDENT_ID --samples 30
python encode_faces.py
```

---

## 🔗 Federated Learning (Optional)

Terminal 1 — Start FL Server:
```bash
cd federated_learning
python server.py
```

Terminal 2 — Run FL Client:
```bash
cd federated_learning
python client.py --server http://localhost:8080 --student_id S25001
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/register` | Register |
| GET | `/api/student/exams` | Get exams |
| POST | `/api/student/exams/<id>/start` | Start exam |
| POST | `/api/student/sessions/<id>/submit` | Submit exam |
| GET | `/api/admin/dashboard` | Admin stats |
| GET | `/api/admin/students` | All students |
| POST | `/api/admin/exams` | Create exam |
| GET | `/api/admin/warnings` | All warnings |
| POST | `/api/proctor/alert` | Log alert |
| GET | `/api/health` | Health check |

---

## 🛠️ VS Code Extensions (Recommended)

Install these for best experience:
- **Python** (Microsoft)
- **Pylance**
- **Live Server**
- **Thunder Client** (API testing)

---

## 📦 Key Python Packages

```
Flask              — Web framework
face-recognition   — Face detection & recognition
mediapipe          — Eye tracking, head pose
ultralytics        — YOLOv8 object detection
opencv-python      — Computer vision
Flask-JWT-Extended — Authentication
reportlab          — PDF report generation
pyaudio            — Microphone monitoring
pyttsx3            — Text-to-speech alerts
scikit-learn       — ML for keystroke analysis
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `dlib` install fails | Install CMake + VS Build Tools first |
| Camera not opening | Check webcam permissions in browser |
| Port 5000 in use | Change `PORT=5001` in `config.py` |
| `face_recognition` import error | `pip install face-recognition` separately |
| DB errors | Delete `backend/database/aioeps.db` and restart |
| Module not found | Ensure venv is activated |

---

## 👨‍💻 Tech Stack

```
Backend:   Python 3.10, Flask 3.0, SQLite, JWT
Frontend:  HTML5, CSS3, Vanilla JavaScript
AI/ML:     OpenCV, MediaPipe, face_recognition, YOLOv8
Audio:     PyAudio, SpeechRecognition, pyttsx3
Reports:   ReportLab
Security:  bcrypt, CORS, JWT tokens
```

---

## 📄 License

This project is built for **educational/academic purposes** as a Final Year Project.

---

*© 2025 AIOEPS — AI Based Online Examination Proctoring System*

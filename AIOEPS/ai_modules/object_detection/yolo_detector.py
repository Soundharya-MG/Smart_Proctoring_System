"""
yolo_detector.py - YOLO Object Detection (Mobile Phone / Book / Person)
AIOEPS - AI Based Online Examination Proctoring System
"""
import os

MODELS_DIR  = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
YOLO_PATH   = os.path.join(MODELS_DIR, 'yolo_model.pt')

# Objects that trigger an alert during exam
SUSPICIOUS_CLASSES = {'cell phone', 'mobile phone', 'book', 'laptop', 'tablet', 'person'}

try:
    from ultralytics import YOLO as _YOLO
    _model = _YOLO('yolov8n.pt')   # downloads yolov8n automatically on first run
    YOLO_OK = True
except Exception:
    YOLO_OK = False

def detect_objects(frame_bgr: 'np.ndarray') -> dict:
    """
    Run YOLOv8 on a BGR frame.
    Returns list of detected suspicious objects.
    """
    if not YOLO_OK:
        return {'objects': [], 'suspicious': False}

    results = _model(frame_bgr, verbose=False)[0]
    found = []
    for box in results.boxes:
        cls_name = results.names[int(box.cls)].lower()
        conf     = float(box.conf)
        if conf > 0.45:
            found.append({'class': cls_name, 'confidence': round(conf, 2)})

    suspicious = [o for o in found if o['class'] in SUSPICIOUS_CLASSES
                  and o['class'] != 'person']
    return {
        'objects':   found,
        'suspicious': len(suspicious) > 0,
        'suspicious_objects': suspicious
    }

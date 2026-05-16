"""
encode_faces.py - Train & Save Face Encodings
AIOEPS - AI Based Online Examination Proctoring System

Usage:
    python encode_faces.py
"""

import os, pickle, sys

DATASET_DIR    = os.path.join(os.path.dirname(__file__), '..', '..', 'dataset')
MODELS_DIR     = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
EMBEDDINGS_PATH = os.path.join(MODELS_DIR, 'face_embeddings.pkl')

def encode_all():
    try:
        import face_recognition
    except ImportError:
        print("❌ face_recognition not installed. Run: pip install face-recognition")
        sys.exit(1)

    os.makedirs(MODELS_DIR, exist_ok=True)
    embeddings = {}
    students = [d for d in os.listdir(DATASET_DIR)
                if os.path.isdir(os.path.join(DATASET_DIR, d))]

    if not students:
        print("⚠️  No student folders found in dataset/")
        return

    for student_id in students:
        folder = os.path.join(DATASET_DIR, student_id)
        images = [f for f in os.listdir(folder)
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        print(f"🔍 Encoding {student_id}: {len(images)} images...")
        encs = []
        for img_name in images:
            path = os.path.join(folder, img_name)
            img  = face_recognition.load_image_file(path)
            enc  = face_recognition.face_encodings(img)
            if enc:
                encs.append(enc[0])
        if encs:
            import numpy as np
            embeddings[student_id] = np.mean(encs, axis=0)  # Average encoding
            print(f"  ✅ {student_id} encoded ({len(encs)} valid faces)")
        else:
            print(f"  ⚠️  No faces found for {student_id}")

    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(embeddings, f)
    print(f"\n✅ Saved {len(embeddings)} encodings → {EMBEDDINGS_PATH}")

if __name__ == '__main__':
    encode_all()

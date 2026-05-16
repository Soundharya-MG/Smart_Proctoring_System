"""
capture_dataset.py - Capture Student Face Dataset
AIOEPS - AI Based Online Examination Proctoring System

Usage:
    python capture_dataset.py --student_id S25123456789 --samples 30
"""

import cv2
import os
import sys
import argparse
import time

DATASET_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dataset')

def capture_faces(student_id: str, samples: int = 30):
    """Capture face images from webcam for a student."""
    save_dir = os.path.join(DATASET_DIR, student_id)
    os.makedirs(save_dir, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    count = 0
    print(f"📷 Capturing {samples} face images for {student_id}...")
    print("   Look at the camera. Press 'q' to quit early.")

    while count < samples:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            count += 1
            face_img = frame[y:y+h, x:x+w]
            path = os.path.join(save_dir, f'face_{count:04d}.jpg')
            cv2.imwrite(path, face_img)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Captured: {count}/{samples}",
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        cv2.imshow(f"Capturing: {student_id}", frame)
        time.sleep(0.05)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Captured {count} images saved to: {save_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture face dataset for a student')
    parser.add_argument('--student_id', required=True, help='Student ID (e.g. S25123456789)')
    parser.add_argument('--samples', type=int, default=30, help='Number of images to capture')
    args = parser.parse_args()
    capture_faces(args.student_id, args.samples)

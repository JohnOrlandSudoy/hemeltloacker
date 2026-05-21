"""USB webcam face capture and recognition."""
import logging
import pickle
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_face_recognition = None


def _import_face_recognition():
    global _face_recognition
    if _face_recognition is None:
        import face_recognition

        _face_recognition = face_recognition
    return _face_recognition


def _open_capture():
    if config.SIMULATE_HARDWARE:
        return None
    import cv2

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {config.CAMERA_INDEX}")
    return cap


def _capture_frame():
    if config.SIMULATE_HARDWARE:
        import numpy as np

        # Dummy RGB frame (no face) — encoding uses fixed sim vector
        return np.zeros((240, 320, 3), dtype=np.uint8)
    import cv2

    cap = _open_capture()
    try:
        for _ in range(10):
            ret, frame = cap.read()
            if ret:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        raise RuntimeError("Failed to read frame from camera")
    finally:
        cap.release()


def capture_encoding() -> list[float] | None:
    """
    Capture face encoding from webcam.
    Returns 128-d encoding list or None if no face found.
    """
    if config.SIMULATE_HARDWARE:
        logger.info("Face capture (simulated)")
        return [0.1] * 128

    fr = _import_face_recognition()
    rgb = _capture_frame()
    locations = fr.face_locations(rgb, model="hog")
    if not locations:
        logger.warning("No face detected")
        return None
    encodings = fr.face_encodings(rgb, known_face_locations=locations)
    if not encodings:
        return None
    return list(encodings[0])


def capture_encoding_averaged(samples: int | None = None) -> list[float] | None:
    """Average multiple captures for more stable registration."""
    n = samples or config.FACE_CAPTURE_FRAMES
    collected = []
    for i in range(n):
        enc = capture_encoding()
        if enc:
            collected.append(enc)
        logger.info("Face sample %s/%s", i + 1, n)
    if not collected:
        return None
    if len(collected) == 1:
        return collected[0]
    try:
        import numpy as np

        return list(np.mean(collected, axis=0))
    except ImportError:
        # Fallback without numpy
        size = len(collected[0])
        return [
            sum(row[i] for row in collected) / len(collected) for i in range(size)
        ]


def encoding_to_bytes(encoding: list[float]) -> bytes:
    return pickle.dumps(encoding)


def bytes_to_encoding(data: bytes) -> list[float]:
    return pickle.loads(data)


def save_face_photo(user_id: int, encoding: list[float]) -> Path | None:
    """Optionally save reference photo path; encoding stored in DB."""
    config.FACES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FACES_DIR / f"user_{user_id}.pkl"
    path.write_bytes(encoding_to_bytes(encoding))
    return path


def load_encoding_from_file(path: Path) -> list[float] | None:
    if not path.exists():
        return None
    return bytes_to_encoding(path.read_bytes())


def match_encoding(
    probe: list[float],
    known: list[float],
    tolerance: float | None = None,
) -> bool:
    tol = tolerance if tolerance is not None else config.FACE_TOLERANCE
    if config.SIMULATE_HARDWARE:
        return probe == known or (probe and known and probe[0] == known[0])

    fr = _import_face_recognition()
    results = fr.compare_faces([known], probe, tolerance=tol)
    return bool(results[0])


def find_matching_user(
    probe: list[float],
    users_encodings: list[tuple[int, str, list[float]]],
    tolerance: float | None = None,
) -> tuple[int, str] | None:
    """Return (user_id, name) for best match or None."""
    tol = tolerance if tolerance is not None else config.FACE_TOLERANCE
    if config.SIMULATE_HARDWARE:
        for uid, name, enc in users_encodings:
            if match_encoding(probe, enc, tol):
                return uid, name
        return None

    fr = _import_face_recognition()
    if not users_encodings:
        return None
    known = [u[2] for u in users_encodings]
    ids_names = [(u[0], u[1]) for u in users_encodings]
    results = fr.compare_faces(known, probe, tolerance=tol)
    if True not in results:
        return None
    idx = results.index(True)
    return ids_names[idx]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Capturing face — look at the camera...")
    enc = capture_encoding_averaged(3)
    if enc:
        print("OK — encoding length:", len(enc))
        print("First 5 values:", enc[:5])
    else:
        print("FAILED — no face detected")

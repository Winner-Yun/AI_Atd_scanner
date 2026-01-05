import cv2
import atexit

global_capture = None


def get_camera():
    global global_capture
    if global_capture is None or not global_capture.isOpened():
        global_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        # 🔥 LOW LATENCY CAMERA SETTINGS
        global_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        global_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        global_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        global_capture.set(cv2.CAP_PROP_FPS, 30)

    return global_capture


def release_camera():
    global global_capture
    if global_capture and global_capture.isOpened():
        global_capture.release()
    global_capture = None


atexit.register(release_camera)

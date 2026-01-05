import cv2
import face_recognition
import numpy as np
import time
from core.config import MATCH_TOLERANCE, SCALE
from core.data_manager import get_all_face_encodings
from core.attendance import mark_attendance, get_scan_status

cv2.setUseOptimized(True)
cv2.setNumThreads(4)


class FaceSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_training_data()

    def load_training_data(self):
        self.known_face_encodings.clear()
        self.known_face_names.clear()

        print("--- Loading Face Data from MongoDB... ---")

        faces_data = get_all_face_encodings()

        for name, encoding_list in faces_data.items():
            self.known_face_names.append(name)
            self.known_face_encodings.append(
                np.array(encoding_list, dtype=np.float32)
            )

        print(f"--- Loaded {len(self.known_face_names)} students from DB. ---")

    def process_frame(self, frame, frame_count, state_vars):
        UPSCALE = int(1 / SCALE)
        PROCESS_EVERY = 6  # 🔥 Increase for more speed (5–8 safe)

        if frame_count % PROCESS_EVERY == 0:
            small_frame = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(
                rgb_small_frame,
                model="hog",
                number_of_times_to_upsample=0
            )

            face_encodings = []
            if face_locations:
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame,
                    face_locations,
                    num_jitters=1
                )

            face_names = []
            face_statuses = []
            detected_candidate = None

            for encodeFace in face_encodings:
                name = "Unknown"
                status = "unknown"

                if self.known_face_encodings:
                    matches = face_recognition.compare_faces(
                        self.known_face_encodings,
                        encodeFace,
                        tolerance=MATCH_TOLERANCE
                    )

                    if True in matches:
                        best_match_index = matches.index(True)
                        real_name = self.known_face_names[best_match_index]

                        scan_status = get_scan_status(real_name)

                        if scan_status == 'ready':
                            status = "scannable"
                            name = real_name
                            detected_candidate = real_name
                        elif scan_status == 'marked':
                            status = "done"
                            name = real_name

                face_names.append(name)
                face_statuses.append(status)

            state_vars['last_locs'] = face_locations
            state_vars['last_names'] = face_names
            state_vars['last_statuses'] = face_statuses
            state_vars['detected'] = detected_candidate

        # --- Timer Logic (unchanged) ---
        detected = state_vars.get('detected')
        if detected:
            if detected == state_vars.get('verified_name'):
                if not state_vars.get('recorded'):
                    if time.time() - state_vars.get('timer_start', 0) >= 2:
                        mark_attendance(detected)
                        state_vars['recorded'] = True
            else:
                state_vars['verified_name'] = detected
                state_vars['timer_start'] = time.time()
                state_vars['recorded'] = False
        else:
            state_vars['verified_name'] = None
            state_vars['recorded'] = False

        # --- Drawing (unchanged) ---
        locations = state_vars.get('last_locs', [])
        names = state_vars.get('last_names', [])
        statuses = state_vars.get('last_statuses', [])

        for (top, right, bottom, left), name, status in zip(locations, names, statuses):
            top *= UPSCALE
            right *= UPSCALE
            bottom *= UPSCALE
            left *= UPSCALE

            if status == "scannable":
                is_verifying = (name == state_vars.get('verified_name'))
                is_recorded = state_vars.get('recorded') and is_verifying

                if is_recorded:
                    color = (0, 255, 0)
                    label = f"{name} (OK)"
                elif is_verifying:
                    color = (0, 165, 255)
                    label = f"{name}..."
                else:
                    color = (0, 0, 255)
                    label = name

            elif status == "done":
                color = (0, 215, 255)
                label = f"{name} (Done)"

            else:
                color = (100, 100, 100)
                label = "Unknown"

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

        return frame


face_system = FaceSystem()

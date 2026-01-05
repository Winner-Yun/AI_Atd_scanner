from flask import Blueprint, render_template, Response, request, redirect, url_for, flash, jsonify, send_file
import cv2
import time
import os
import io
import csv
import face_recognition 
import numpy as np
from datetime import datetime
from core.config import DATASET_PATH
from core.camera import get_camera, release_camera
from core.recognition import face_system

from core.attendance import (
    get_records, state as attendance_state, set_active_session, active_session
)
from core.data_manager import (
    get_all_classes, create_class_group, add_subject_to_class, 
    delete_class, remove_subject, add_student_to_class, 
    remove_student_from_class, get_all_registered_students,
    update_subject_in_class, get_all_logs, get_available_dates,
    save_student_face, delete_student_globally 
)

main = Blueprint('main', __name__)

@main.app_template_filter('format_time')
def format_time(value):
    return value 

# --- Generators (Unchanged) ---
def generate_frames():
    camera = get_camera()
    frame_count = 0
    state_vars = {'last_locs': [], 'last_names': [], 'verified_name': None, 'timer_start': 0, 'recorded': False, 'detected': None}
    while True:
        if not camera.isOpened(): break
        success, frame = camera.read()
        if not success: break
        frame = face_system.process_frame(frame, frame_count, state_vars)
        frame_count += 1
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def generate_preview():
    camera = get_camera()
    while True:
        if not camera.isOpened(): break
        success, frame = camera.read()
        if not success: break
        preview = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        ret, buffer = cv2.imencode('.jpg', preview)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# --- MAIN ROUTES ---

@main.route('/')
def index():
    classes = get_all_classes()
    available_dates = get_available_dates()
    today_str = datetime.now().strftime('%Y-%m-%d')
    if today_str not in available_dates:
        available_dates.insert(0, today_str)

    selection = request.args.get('session_key') 
    search_date = request.args.get('search_date')
    show_absent = request.args.get('show_absent', '1')
    
    if not search_date: search_date = today_str

    current_class_id = None
    current_subject = None
    
    if not selection and classes:
        first_class = list(classes.keys())[0]
        subjects = classes[first_class].get('subjects', [])
        if subjects:
            selection = f"{first_class}|0"

    if selection and '|' in selection:
        try:
            parts = selection.split('|')
            c_id = parts[0]
            s_idx = int(parts[1])
            if c_id in classes and 'subjects' in classes[c_id] and len(classes[c_id]['subjects']) > s_idx:
                current_class_id = c_id
                current_subject = classes[c_id]['subjects'][s_idx]
                set_active_session(c_id, s_idx, current_subject)
        except: pass

    raw_records = get_records(search_date)
    dashboard_data = []
    raw_records.sort(key=lambda x: x['Name'])

    for log in raw_records:
        if show_absent == '0' and log['Status'] == 'Absent':
            continue
        dashboard_data.append(log)

    return render_template('index.html', 
                           records=dashboard_data, 
                           classes=classes, 
                           current_selection=selection,
                           current_subject=current_subject,
                           search_date=search_date,
                           available_dates=available_dates,
                           show_absent=show_absent)

@main.route('/download_report')
def download_report():
    logs = get_all_logs()
    classes = get_all_classes() # Fetch class data to look up schedules

    if not logs:
        flash("No attendance data recorded yet.", "warning")
        return redirect(url_for('main.index'))

    # Prepare data with Schedule Times
    enhanced_logs = []
    
    for log in logs:
        # Default values
        s_time = "-"
        l_time = "-"
        
        c_id = log.get('Class')
        subj_name = log.get('Subject')

        # Look up the schedule details for this log
        if c_id in classes:
            subjects = classes[c_id].get('subjects', [])
            for s in subjects:
                # Match the subject name to find the times
                if s.get('subject') == subj_name:
                    s_time = s.get('start_time', '-')
                    l_time = s.get('late_time', '-')
                    break
        

        log['Start Time'] = s_time
        log['Late Time'] = l_time
        enhanced_logs.append(log)


    proxy = io.StringIO()
    fieldnames = ["Name", "Class", "Teacher", "Subject", "Date", "Time", "Status", "Start Time", "Late Time"]
    
    writer = csv.DictWriter(proxy, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(enhanced_logs)
    
    mem = io.BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem, 
        as_attachment=True, 
        download_name=f'attendance_full_{datetime.now().strftime("%Y%m%d")}.csv',
        mimetype='text/csv'
    )

@main.route('/manage_classes')
def manage_classes():
    classes = get_all_classes()
    return render_template('manage_classes.html', classes=classes)

# --- NEW ROUTE: Manage Students (Global Database) ---
@main.route('/manage_students')
def manage_students():
    all_students = get_all_registered_students()
    all_students.sort()
    return render_template('manage_students.html', all_students=all_students)

@main.route('/create_class', methods=['POST'])
def create_class():
    class_id = request.form['class_id']
    create_class_group(class_id)
    flash(f"Class {class_id} created!", "success")
    return redirect(url_for('main.edit_class', class_id=class_id))

@main.route('/delete_class/<class_id>')
def delete_class_route(class_id):
    delete_class(class_id)
    flash(f"Deleted {class_id}", "warning")
    return redirect(url_for('main.manage_classes'))

@main.route('/edit_class/<class_id>', methods=['GET', 'POST'])
def edit_class(class_id):
    classes = get_all_classes()
    if class_id not in classes: return redirect(url_for('main.manage_classes'))
    
    if request.method == 'POST':
        start_24 = request.form['start_time']
        late_24 = request.form['late_time']
        
        try:
            start_12 = datetime.strptime(start_24, "%H:%M").strftime("%I:%M %p")
            late_12 = datetime.strptime(late_24, "%H:%M").strftime("%I:%M %p")
        except:
            start_12 = start_24
            late_12 = late_24

        add_subject_to_class(class_id, request.form['teacher'], request.form['subject'], start_12, late_12)
        flash("Subject Added!", "success")
        return redirect(url_for('main.edit_class', class_id=class_id))
    
    all_students = get_all_registered_students()
    return render_template('edit_class.html', class_id=class_id, class_data=classes[class_id], all_students=all_students)

@main.route('/update_subject/<class_id>/<int:idx>', methods=['POST'])
def update_subject(class_id, idx):
    start_24 = request.form['start_time']
    late_24 = request.form['late_time']
    try:
        start_12 = datetime.strptime(start_24, "%H:%M").strftime("%I:%M %p")
        late_12 = datetime.strptime(late_24, "%H:%M").strftime("%I:%M %p")
    except:
        start_12 = start_24
        late_12 = late_24

    update_subject_in_class(
        class_id, idx, request.form['teacher'], request.form['subject'], start_12, late_12
    )
    flash("Schedule updated!", "success")
    return redirect(url_for('main.edit_class', class_id=class_id))

@main.route('/enroll_existing_student/<class_id>', methods=['POST'])
def enroll_existing_student(class_id):
    student_name = request.form.get('student_name')
    if student_name:
        add_student_to_class(class_id, student_name)
        flash(f"{student_name} added to {class_id}!", "success")
    return redirect(url_for('main.edit_class', class_id=class_id))

@main.route('/remove_student/<class_id>/<student_name>')
def remove_student_route(class_id, student_name):
    # Removes from class roster AND deletes logs for this specific class
    remove_student_from_class(class_id, student_name)
    flash(f"Removed {student_name} from {class_id} (Logs cleared for this class)", "warning")
    return redirect(url_for('main.edit_class', class_id=class_id))

# --- ROUTE FOR GLOBAL DELETION (Redirects to Manage Students) ---
@main.route('/delete_student_globally/<student_name>')
def delete_student_globally_route(student_name):
    delete_student_globally(student_name)
    # Re-sync face system in runtime
    face_system.load_training_data()
    flash(f"PERMANENTLY deleted {student_name} data (Images, Logs, Enrollments).", "danger")
    return redirect(url_for('main.manage_students'))

@main.route('/delete_subject/<class_id>/<int:idx>')
def delete_subject(class_id, idx):
    remove_subject(class_id, idx)
    flash("Subject removed", "warning")
    return redirect(url_for('main.edit_class', class_id=class_id))

@main.route('/add_user', methods=['GET', 'POST'])
def add_user():
    classes = get_all_classes()
    if request.method == 'POST':
        name = request.form['name']
        class_id = request.form.get('class_id')
        
        # 1. Prepare Storage
        student_path = os.path.join(DATASET_PATH, name)
        if not os.path.exists(student_path): os.makedirs(student_path)
        
        captured_encodings = []
        uploaded_files = request.files.getlist('user_images')

        # 2. Check for Uploads First
        if uploaded_files and len(uploaded_files) > 0 and uploaded_files[0].filename != '':
            print(f"--- Processing Uploads for {name} ---")
            count = 0
            for file in uploaded_files:
                # Save image to disk
                file_path = os.path.join(student_path, f"{name}_{count}.jpg")
                file.save(file_path)

                # Process image for face encoding
                image = face_recognition.load_image_file(file_path)
                encs = face_recognition.face_encodings(image)
                
                if encs:
                    captured_encodings.append(encs[0])
                
                count += 1

        # 3. If No Uploads, Use Camera
        else:
            print(f"--- Starting Camera for {name} ---")
            release_camera()
            time.sleep(0.5)
            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            count = 0
            while count < 5: 
                ret, frame = cam.read()
                if ret:
                    # Save image to disk
                    cv2.imwrite(f"{student_path}/{name}_{count}.jpg", frame)
                    
                    # Process frame for face encoding
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    encs = face_recognition.face_encodings(rgb)
                    
                    if encs:
                        captured_encodings.append(encs[0])

                    count += 1
                    cv2.waitKey(150)
                else: 
                    break
            cam.release()
            release_camera() 

        # 4. Save to Database (Common Step)
        if captured_encodings:
            # Calculate average encoding for better accuracy
            avg_encoding = np.mean(captured_encodings, axis=0)
            
            # Save to MongoDB (faces collection)
            save_student_face(name, avg_encoding)
            
            # Update Runtime System (so you don't need to restart)
            face_system.known_face_names.append(name)
            face_system.known_face_encodings.append(avg_encoding)
            
            # Add to Class Roster
            if class_id: 
                add_student_to_class(class_id, name)
            
            flash(f"Student {name} added and synced to Database!", "success")
        else:
            # Cleanup if no face found
            flash(f"Error: No face detected. Please try again with clearer photos.", "danger")
            try:
                import shutil
                shutil.rmtree(student_path)
            except: pass

        return redirect(url_for('main.index'))
    return render_template('add_user.html', classes=classes)

@main.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
@main.route('/preview_feed')
def preview_feed():
    return Response(generate_preview(), mimetype='multipart/x-mixed-replace; boundary=frame')
@main.route('/check_update')
def check_update():
    return jsonify({'last_update': attendance_state['last_update_time']})
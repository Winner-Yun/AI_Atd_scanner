import time
from datetime import datetime
from core.config import logs_col
from core.data_manager import get_students_in_class

# Global state
active_session = None
state = {'last_update_time': time.time()}

def set_active_session(class_id, subject_idx, subject_info):
    global active_session
    active_session = {
        'class_id': str(class_id).strip(),
        'subject_idx': int(subject_idx),
        'info': subject_info
    }
    print(f"DEBUG: Session Active: {class_id} - {subject_info.get('subject')}")
    initialize_attendance()

def initialize_attendance():
    """Batch creates Absent records for missing students."""
    if not active_session: return

    today = datetime.now().strftime('%Y-%m-%d')
    class_id = active_session['class_id']
    subject_name = active_session['info']['subject']
    teacher = active_session['info']['teacher']

    students = get_students_in_class(class_id)
    if not students: return

    # Check who is already in DB for this specific session
    existing_logs = logs_col.find({
        "Date": today,
        "Class": class_id,
        "Subject": subject_name
    }, {"Name": 1})
    
    existing_names = {log['Name'] for log in existing_logs}
    new_logs = []

    for student in students:
        if student not in existing_names:
            new_logs.append({
                "Name": student,
                "Class": class_id,
                "Teacher": teacher,
                "Subject": subject_name,
                "Date": today,
                "Time": "-",
                "Status": "Absent"
            })

    if new_logs:
        logs_col.insert_many(new_logs)
        state['last_update_time'] = time.time()
        print(f"INIT: Added {len(new_logs)} absent records.")

def get_scan_status(name):
    if not active_session: return None
    
    class_id = active_session['class_id']
    students = get_students_in_class(class_id)
    
    # 1. Check if student is in this class
    if not any(str(s).lower() == str(name).lower() for s in students):
        return 'not_in_class'
        
    # 2. Check current status in DB
    today = datetime.now().strftime('%Y-%m-%d')
    subject_name = active_session['info']['subject']
    
    log = logs_col.find_one({
        "Name": name,
        "Date": today,
        "Class": class_id,
        "Subject": subject_name
    }, {"Status": 1})
    
    if log and log['Status'] in ['Present', 'Late']:
        return 'marked'
            
    return 'ready'

def mark_attendance(name):
    global active_session, state
    if not active_session: return False

    today = datetime.now().strftime('%Y-%m-%d')
    subject_name = active_session['info']['subject']
    class_id = active_session['class_id']
    
    now = datetime.now()
    time_str = now.strftime('%I:%M %p')
    
    # Check Late Time
    late_limit_str = active_session['info'].get('late_time', '11:59 PM')
    status = "Present"
    try:
        late_limit = datetime.strptime(late_limit_str, '%I:%M %p').time()
        if now.time() > late_limit:
            status = "Late"
    except: pass

    # Update DB
    result = logs_col.update_one(
        {
            "Name": name,
            "Date": today,
            "Class": class_id,
            "Subject": subject_name,
            "Status": "Absent" # Only update if currently Absent
        },
        {
            "$set": {
                "Time": time_str,
                "Status": status
            }
        }
    )

    if result.modified_count > 0:
        state['last_update_time'] = time.time()
        print(f"UPDATE: {name} marked as {status}")
        return True

    return False

def get_records(target_date=None):
    if not target_date: target_date = datetime.now().strftime('%Y-%m-%d')
    
    query = {"Date": target_date}
    if active_session:
        query["Class"] = active_session['class_id']
        query["Subject"] = active_session['info']['subject']

    return list(logs_col.find(query, {"_id": 0}))
import os
import shutil 
import numpy as np
from core.config import classes_col, logs_col, faces_col, DATASET_PATH

# --- CLASS MANAGEMENT ---
def create_class_group(class_id):
    if not classes_col.find_one({"class_id": class_id}):
        classes_col.insert_one({
            "class_id": class_id,
            "students": [],
            "subjects": []
        })

def add_subject_to_class(class_id, teacher, subject_name, start_time, late_time):
    new_subject = {
        "teacher": teacher,
        "subject": subject_name,
        "start_time": start_time,
        "late_time": late_time
    }
    classes_col.update_one(
        {"class_id": class_id},
        {"$push": {"subjects": new_subject}}
    )

def update_subject_in_class(class_id, subject_index, teacher, subject_name, start_time, late_time):
    key = f"subjects.{subject_index}"
    updated_subject = {
        "teacher": teacher,
        "subject": subject_name,
        "start_time": start_time,
        "late_time": late_time
    }
    classes_col.update_one(
        {"class_id": class_id},
        {"$set": {key: updated_subject}}
    )

def delete_class(class_id):
    # 1. Delete the Class Definition from 'classes' collection
    classes_col.delete_one({"class_id": class_id})
    
    # 2. Delete ALL Attendance Logs for this specific class from 'logs' collection
    # This ensures no "ghost" data remains for the deleted class.
    logs_col.delete_many({"Class": class_id})

def remove_subject(class_id, subject_index):
    classes_col.update_one(
        {"class_id": class_id},
        {"$unset": {f"subjects.{subject_index}": 1}}
    )
    classes_col.update_one(
        {"class_id": class_id},
        {"$pull": {"subjects": None}}
    )

def add_student_to_class(class_id, student_name):
    classes_col.update_one(
        {"class_id": class_id},
        {"$addToSet": {"students": student_name}}
    )

def remove_student_from_class(class_id, student_name):
    """
    Removes student from the class roster AND deletes their attendance logs 
    for this specific class.
    """
    # 1. Remove from Class Roster
    classes_col.update_one(
        {"class_id": class_id},
        {"$pull": {"students": student_name}}
    )
    
    # 2. Remove from Attendance Logs for this Class ONLY
    logs_col.delete_many({
        "Class": class_id,
        "Name": student_name
    })

def get_students_in_class(class_id):
    data = classes_col.find_one({"class_id": class_id}, {"students": 1})
    if data and "students" in data:
        return data["students"]
    return []

def get_all_registered_students():
    return list(faces_col.distinct("name"))

# --- FACE DATA MANAGEMENT ---
def save_student_face(name, encoding):
    faces_col.update_one(
        {"name": name},
        {
            "$set": {
                "name": name,
                "encoding": encoding.tolist()
            }
        },
        upsert=True
    )

def get_all_face_encodings():
    all_faces = faces_col.find({}, {"_id": 0, "name": 1, "encoding": 1})
    data = {}
    for face in all_faces:
        data[face['name']] = face['encoding']
    return data

def delete_student_globally(student_name):
    """
    Completely removes a student from the system:
    1. Faces DB
    2. Image Folder
    3. All Classes
    4. All Logs
    """
    # 1. Delete Face Data
    faces_col.delete_one({"name": student_name})
    
    # 2. Remove from ALL Class lists
    classes_col.update_many(
        {}, 
        {"$pull": {"students": student_name}}
    )
    
    # 3. Delete ALL Logs
    logs_col.delete_many({"Name": student_name})
    
    # 4. Delete Image Folder
    folder_path = os.path.join(DATASET_PATH, student_name)
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            print(f"Error deleting folder: {e}")

# --- LOGGING MANAGEMENT ---
def append_log(record):
    logs_col.insert_one(record)

def get_all_logs():
    return list(logs_col.find({}, {"_id": 0}))

def get_all_classes():
    all_docs = classes_col.find({}, {"_id": 0})
    result = {}
    for doc in all_docs:
        if "class_id" in doc:
            c_id = doc.pop("class_id")
            result[c_id] = doc
    return result

def get_available_dates():
    dates = logs_col.distinct("Date")
    dates.sort(reverse=True)
    return dates
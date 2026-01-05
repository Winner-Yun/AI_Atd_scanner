# 🛡️ AI Face Recognition Attendance System

A high-performance, real-time attendance management system built with **Python**, **Flask**, and **MongoDB**. This project uses deep learning for face recognition and provides a web-based dashboard for managing classes, students, and schedules.

---

## 🚀 Key Features

- **Real-time Recognition**: Sub-second face detection and matching using `face_recognition` (dlib).  
- **Dual Enrollment**: Register students via a live webcam feed or by uploading 5 photos.  
- **Smart Attendance**: Automatically marks students as "Present" or "Late" based on class schedules.  
- **MongoDB Integration**: Stores face encodings, class rosters, and attendance logs.  
- **CSV Reports**: Download filtered attendance logs including schedule times (Start/Late).  
- **Class Management**: Create classes, assign teachers/subjects, and manage student lists.  

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask  
- **Database**: MongoDB  
- **Computer Vision**: OpenCV, face_recognition (HOG & Deep Learning)  
- **Frontend**: Bootstrap 5, FontAwesome, JavaScript  

---

## 📋 Installation & Setup

### 1. Prerequisites

- Python 3.8+  
- MongoDB installed and running (default: `localhost:27019`)  
- C++ Compiler (required for `dlib` installation)  

### 2. Clone the Project

```bash
git clone https://github.com/yourusername/attendance-system.git
cd attendance-system
```
###  3. Install Dependencies
```bash
pip install flask pymongo opencv-python face_recognition numpy
```
### 4. Configuration

Open core/config.py and update your MongoDB URI if necessary:
```bash
MONGO_URI = "mongodb://aiscanner:aiscanner123@localhost:27019/"
DB_NAME = "attendance_system"
```
### 5. Run the Application
```bash
python app.py
```
# 📸 Face Recognition Attendance System

A real-time face recognition attendance system built with Flask and MongoDB. Track attendance, manage classes, and generate CSV reports with ease.

---

## 📂 Project Structure

| File | Description |
|------|-------------|
| `app.py` | Main entry point of the Flask application |
| `core/routes.py` | Handles all URL logic (Add User, Download CSV, etc.) |
| `core/data_manager.py` | Database CRUD operations for MongoDB |
| `core/recognition.py` | Logic for face matching and frame processing |
| `core/attendance.py` | Attendance session tracking and late-time logic |
| `core/camera.py` | Optimized camera feed handler (low latency) |
| `image/` | Local storage for captured/uploaded student faces |

---

## 📊 Database Schema

The system uses three main collections in the `attendance_system` database:

### **1. faces**
Stores student names and their 128-d face encodings.  

### **2. classes**
Stores Class IDs, student rosters, and subject schedules.  

### **3. logs**
Stores attendance records:

| Field | Description |
|-------|-------------|
| Name | Student name |
| Class | Class ID |
| Subject | Subject name |
| Date | Attendance date |
| Time | Attendance time |
| Status | Present / Absent / Late |

---

## 📝 Important Notes for Users

- **Enrollment:**  
  - Using the camera: stay still for accurate capture.  
  - Uploading images: provide **exactly 5 clear images** per student.  

- **CSV Export:**  
  - Download the full attendance history or filter by a specific **Class ID** directly from the Class Manager.  

- **Auto-Cleanup:**  
  - Deleting a class will remove all associated attendance logs to keep the database clean.

---

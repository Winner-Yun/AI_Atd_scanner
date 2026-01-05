import os
from pymongo import MongoClient

# Paths
DATASET_PATH = 'image'

# MongoDB Configuration
# User provided: mongodb://aiscanner:aiscanner123@localhost:27019
MONGO_URI = "mongodb://aiscanner:aiscanner123@localhost:27019/" 
DB_NAME = "attendance_system"

# Settings
MATCH_TOLERANCE = 0.50 
SCALE = 0.25 

if not os.path.exists(DATASET_PATH): 
    os.makedirs(DATASET_PATH)

# Initialize Database Connection
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Collections
    classes_col = db["classes"]
    logs_col = db["logs"]
    faces_col = db["faces"]
    
    # Test connection
    client.server_info()
    print("--- Connected to MongoDB Successfully ---")
except Exception as e:
    print(f"--- MongoDB Connection Error: {e} ---")
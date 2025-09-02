import firebase_admin
from firebase_admin import credentials, firestore
import time
import random
from datetime import datetime, timedelta
import numpy as np

# CONFIGURATION
CREDENTIALS_FILE = "firebase_credentials.json"
ROOM_IDS = ["Clasroom 1", "Classroom 2", "Lab"]
COLLECTION_NAME = "room_data_aggregated"
TIME_ACCELERATION_FACTOR = 60 # 1 real second = 60 simulated seconds

def initialize_firebase():
    """Initializes the connection to Firebase."""
    try:
        cred = credentials.Certificate(CREDENTIALS_FILE)
        if not firebase_admin._apps: firebase_admin.initialize_app(cred)
        print("Successfully connected to Firebase.")
        return firestore.client()
    except Exception as e:
        print(f"Error connecting to Firebase: {e}"); return None

def generate_sensor_data(timestamp):
    """Generates a single, realistic sensor data point for a specific moment."""
    hour, weekday = timestamp.hour, timestamp.weekday()
    is_occupied, person_count = False, 0
    if weekday < 5:
        if 8 <= hour < 12 or 13 <= hour < 17:
            if random.random() > 0.3: is_occupied, person_count = True, random.randint(5, 35)
        elif 12 <= hour < 13 or 17 <= hour < 20:
            if random.random() > 0.7: is_occupied, person_count = True, random.randint(1, 10)
    else:
        if 10 <= hour < 16 and random.random() > 0.85: is_occupied, person_count = True, random.randint(1, 5)
    
    return {
        "avg_person_count": person_count,
        "max_person_count": person_count + random.randint(0, 5),
        "is_occupied": 1 if is_occupied else 0,
        "is_smoke_detected": 1 if random.random() > 0.999 else 0,
        "avg_light_intensity": round(random.uniform(300, 550) if is_occupied and 7 < hour < 18 else random.uniform(10, 50), 2),
        "avg_air_quality_ppm": round(400 + (person_count * 15) + random.uniform(-20, 20), 2),
        "timestamp": timestamp
    }

def simulate_accelerated_time(db):
    """Simulates time passing at an accelerated rate and only writes on change."""
    print(f"\n--- Starting INTELLIGENT live simulation ---")
    print(f"--- (Writes to Firebase ONLY when person count changes) ---")
    
    current_simulated_time = datetime.now()
    
    # This dictionary will remember the last written state for each room
    last_written_state = {room_id: {"person_count": -1} for room_id in ROOM_IDS}

    while True:
        try:
            current_simulated_time += timedelta(seconds=TIME_ACCELERATION_FACTOR)
            
            for room_id in ROOM_IDS:
                data = generate_sensor_data(current_simulated_time)
                
                # Compare the current person count with the last one written
                last_count = last_written_state[room_id]["person_count"]
                current_count = data["avg_person_count"]
                
                if current_count != last_count:
                    # The count has changed and writes to the database.
                    print(f"\nState change in {room_id}! From {last_count} to {current_count}. Writing to Firebase...")
                    
                    data['room_id'] = room_id
                    db.collection(COLLECTION_NAME).add(data)
                    
                    # Update the state memory with the new value
                    last_written_state[room_id]["person_count"] = current_count
                # If the count is the same, do nothing and save a write
            
            print(f"Simulating Time: {current_simulated_time.strftime('%Y-%m-%d %H:%M:%S')}", end='\r')
            
            time.sleep(1) # Wait for 1 second

        except KeyboardInterrupt:
            print("\n--- Live simulation stopped. ---")
            break

if __name__ == "__main__":
    db_client = initialize_firebase()
    if db_client:
        simulate_accelerated_time(db_client)
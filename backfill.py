import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random
import time
from google.api_core.exceptions import ResourceExhausted, RetryError

# CONFIGURATION
CREDENTIALS_FILE = "firebase_credentials.json"
ROOM_IDS = ["Clasroom 1", "Classroom 2", "Lab"]
COLLECTION_NAME = "room_data_aggregated"
NUM_DAYS_HISTORY = 30
HISTORY_INTERVAL_MINUTES = 15

# These settings are extremely conservative to guarantee success.
BATCH_SIZE = 50  # Very small batch size
PAUSE_BETWEEN_BATCHES_SECONDS = 2  # A polite pause after every successful batch

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
    """Generates a realistic sensor data payload for a specific point in time."""
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
        "timestamp": timestamp,
        "room_id": None
    }

def commit_batch_with_retry(db, batch_data):
    """Commits a batch to Firestore and handles rate limit errors with retries."""
    max_retries = 5
    retry_delay = 5  # Start with a 5-second delay
    
    for attempt in range(max_retries):
        try:
            batch = db.batch()
            for data in batch_data:
                doc_ref = db.collection(COLLECTION_NAME).document()
                batch.set(doc_ref, data)
            batch.commit()
            return True # Success
        except (ResourceExhausted, RetryError) as e:
            print(f"\n[Attempt {attempt + 1}/{max_retries}] Rate limit hit. Waiting for {retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
            retry_delay *= 2 # Double the delay for the next attempt (exponential backoff)
    
    print(f"\nFailed to commit batch after {max_retries} attempts. Aborting.")
    return False # Failed after all retries

def backfill_historical_data(db):
    """Generates historical data and sends it in throttled, robust batches."""
    print("--- Starting ULTRA-SAFE historical data backfill to Firebase ---")
    now = datetime.now()
    start_time = now - timedelta(days=NUM_DAYS_HISTORY)
    current_time = start_time
    data_batch = []
    
    total_points = (NUM_DAYS_HISTORY * 24 * 60) // HISTORY_INTERVAL_MINUTES * len(ROOM_IDS)
    points_generated = 0

    while current_time < now:
        for room_id in ROOM_IDS:
            data = generate_sensor_data(current_time)
            data['room_id'] = room_id
            data_batch.append(data)
            points_generated += 1

            if len(data_batch) >= BATCH_SIZE:
                success = commit_batch_with_retry(db, data_batch)
                if not success:
                    return # Stop the script if a batch fails completely
                
                data_batch = []
                progress = (points_generated / total_points) * 100
                print(f"Backfill progress: {progress:.1f}% complete...", end='\r')
                
                time.sleep(PAUSE_BETWEEN_BATCHES_SECONDS)

        current_time += timedelta(minutes=HISTORY_INTERVAL_MINUTES)
    
    if data_batch:
        commit_batch_with_retry(db, data_batch)
        
    print(f"\n--- Historical data backfill complete. Total points: {points_generated} ---")

if __name__ == "__main__":
    db_client = initialize_firebase()
    if db_client:
        backfill_historical_data(db_client)
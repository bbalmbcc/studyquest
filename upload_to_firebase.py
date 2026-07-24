import json
import urllib.request
import time

URL = "https://studyquest-971b6-default-rtdb.asia-southeast1.firebasedatabase.app/quizData/questions.json"

try:
    with open('data/questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    questions = data.get('questions', [])
    
    # Convert list to dict with ID as key
    firebase_data = {}
    now = int(time.time() * 1000)
    for q in questions:
        if "updatedAt" not in q:
            q["updatedAt"] = now
        firebase_data[q["id"]] = q
        
    print(f"Uploading {len(firebase_data)} questions to Firebase...")
    
    req = urllib.request.Request(URL, method='PUT')
    req.add_header('Content-Type', 'application/json')
    
    json_data = json.dumps(firebase_data).encode('utf-8')
    
    with urllib.request.urlopen(req, data=json_data) as response:
        if response.status == 200:
            print("Successfully uploaded to Firebase!")
        else:
            print(f"Failed: {response.status} {response.read()}")
            
except Exception as e:
    print(f"Error: {e}")

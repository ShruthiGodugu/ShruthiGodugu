import os
import cv2
import base64
import pymongo
import gridfs
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("gemini_api_key")
genai.configure(api_key=API_KEY)

# Connect to MongoDB (Running Locally)
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["MajorProject"]
fs = gridfs.GridFS(db)

# Function to extract key frames
def extract_key_frames(video_path, output_folder, frame_interval=5):
    os.makedirs(output_folder, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    extracted_frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % int(fps * frame_interval) == 0:  # Extract every 5 seconds
            frame_path = os.path.join(output_folder, f"frame_{frame_count}.jpg")
            cv2.imwrite(frame_path, frame)
            extracted_frames.append(frame_path)
        frame_count += 1

    cap.release()
    return extracted_frames

# Function to encode images as base64
def encode_images(image_paths):
    encoded_images = []
    for img_path in image_paths:
        with open(img_path, "rb") as img_file:
            encoded_images.append({
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_file.read()).decode("utf-8")
            })
    return encoded_images

# Function to detect crime type
def detect_crime_type(video_path):
    frames_folder = "frames"
    print("Extracting key frames from video...")
    key_frames = extract_key_frames(video_path, frames_folder)

    if not key_frames:
        return "No frames extracted. Check the video file."

    print(f"Extracted {len(key_frames)} frames. Sending to Gemini API...")

    model = genai.GenerativeModel("gemini-1.5-pro")  # Use "gemini-1.5-flash" for faster results
    images_data = encode_images(key_frames)

    # 🔹 Strict list of crime types (No "Surveillance" or irrelevant answers)
    prompt_text = """
    Identify the crime type from the given images. Choose only one of the following options:
    
    - Theft
    - Robbery
    - Assault
    - Burglary
    - Kidnapping
    - Arson
    - Murder
    - Vandalism
    - Drug Dealing
    - Fraud
    - Trespassing
    - Harassment
    - Pickpocketing
    - Domestic Violence
    - Sexual Assault
    - No Crime Detected

    Respond with only **one** of the above terms. Do not include any explanation.
    """

    try:
        response = model.generate_content([
            {"role": "user", "parts": images_data + [{"text": prompt_text}]}
        ])

        crime_type = response.text.strip()

        # 🔹 Ensure only a valid response is returned
        valid_crimes = [
            "Theft", "Robbery", "Assault", "Burglary", "Kidnapping", "Arson", 
            "Murder", "Vandalism", "Drug Dealing", "Fraud", "Trespassing", 
            "Harassment", "Pickpocketing", "Domestic Violence", "Sexual Assault", 
            "No Crime Detected"
        ]
        
        return crime_type if crime_type in valid_crimes else "No Crime Detected"

    except Exception as e:
        return f"Error: {str(e)}"

# Function to store video in MongoDB only if a crime is detected
def store_video_if_crime_detected(video_path):
    crime_type = detect_crime_type(video_path)
    
    if crime_type == "No Crime Detected":
        print("✅ No crime detected. Video will NOT be stored in the database.")
        return
    
    print(f"🚨 Crime Detected: {crime_type}. Storing video in MongoDB...")

    # Store video in MongoDB
    with open(video_path, "rb") as video_file:
        video_id = fs.put(video_file, filename=os.path.basename(video_path), crime_type=crime_type)
    
    print(f"✅ Video stored in MongoDB with ID: {video_id} (Crime Type: {crime_type})")

# Example usage
video_path = "testing.webm"
store_video_if_crime_detected(video_path)

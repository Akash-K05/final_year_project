from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import cv2
import easyocr
import uuid
import numpy as np
import pandas as pd
import requests
from roboflow import Roboflow
from pydantic import BaseModel

# ==========================
#  DIRECTORY CONFIGURATION
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOADS_DIR = os.path.join(OUTPUT_DIR, "uploads")
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ==========================
#  LOAD OFFICIAL DRUG DATABASE (CSV)
# ==========================
CSV_FILE_PATH = os.path.join(BASE_DIR, "official_drugs.csv")

try:
    drug_database = pd.read_csv(CSV_FILE_PATH)
    print(f"✅ Loaded CSV file: {CSV_FILE_PATH}")
except FileNotFoundError:
    print(f"❌ Error: CSV file '{CSV_FILE_PATH}' not found. Creating an empty DataFrame.")
    drug_database = pd.DataFrame(columns=["Composition"])  # Empty DataFrame

# ==========================
#  FASTAPI SETUP
# ==========================
app = FastAPI(title="Smart Drug Authentication API")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Enable CORS (for frontend API calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
#  INITIALIZE MODELS
# ==========================
reader = easyocr.Reader(['en'], gpu=True)

# Initialize Roboflow for Medicine Detection
rf = Roboflow(api_key="QXEU69ZtGV5d9DdttRdN")
project = rf.workspace().project("medicine-images")
model = project.version(1).model

class MedicineUpdate(BaseModel):
    detection_id: str
    new_name: str

@app.get("/")
async def home():
    return {"status": "healthy"}

# ==========================
#  FUNCTION TO FETCH DRUG COMPOSITION FROM GEMINI API
# ==========================
def get_drug_composition(medicine_name: str):
    try:
        api_key = "AIzaSyB3O1VjUkgqvXqBnFp6dxq1SxjQqe_ydkI"  # Replace with your actual API key
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateText?key={api_key}"
        
        payload = {
            "prompt": {
                "text": f"What is the composition of {medicine_name}? Please provide a simple, concise answer."
            }
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error: API returned {response.status_code} - {response.text}")
            return "Unknown"

        response_data = response.json()
        composition_text = response_data.get("candidates", [{}])[0].get("output", "")
        
        return composition_text if composition_text else "Unknown"

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {str(e)}")
        return "Unknown"

# ==========================
#  FUNCTION TO FETCH DRUG SIDE EFFECTS FROM GEMINI API
# ==========================
def get_drug_side_effects(medicine_name: str):
    try:
        api_key = "AIzaSyB3O1VjUkgqvXqBnFp6dxq1SxjQqe_ydkI"  # Replace with your actual API key
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateText?key={api_key}"
        
        payload = {
            "prompt": {
                "text": f"What are the common side effects of {medicine_name}? Please provide a brief list."
            }
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error: API returned {response.status_code} - {response.text}")
            return "Not Available"

        response_data = response.json()
        side_effects = response_data.get("candidates", [{}])[0].get("output", "")
        
        return side_effects if side_effects else "Not Available"

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {str(e)}")
        return "Not Available"

# ==========================
#  FUNCTION TO VERIFY AUTHENTICITY AGAINST CSV DATABASE
# ==========================
def is_authentic_drug(drug_composition: str):
    try:
        if "Composition" not in drug_database.columns:
            print("❌ Error: 'Composition' column not found in CSV file!")
            return False

        official_compositions = drug_database["Composition"].astype(str).str.lower().tolist()
        composition_lower = drug_composition.lower()
        
        # Check if any official composition appears in the text
        for official_comp in official_compositions:
            if official_comp in composition_lower:
                return True  # ✅ Drug found in the official database

        return False  # ❌ Drug NOT found (Counterfeit warning)

    except Exception as e:
        print(f"❌ Error checking drug authenticity: {str(e)}")
        return False

# ==========================
#  GET MEDICINE INFO API ENDPOINT
# ==========================
@app.get("/api/get-medicine-info")
async def get_medicine_info(medicine_name: str):
    try:
        composition = get_drug_composition(medicine_name)
        side_effects = get_drug_side_effects(medicine_name)
        is_authentic = is_authentic_drug(composition)
        
        return {
            "medicine_name": medicine_name,
            "composition": composition,
            "side_effects": side_effects,
            "is_authentic": is_authentic
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error getting medicine information: {str(e)}")

# ==========================
#  MEDICINE DETECTION API
# ==========================
@app.post("/api/detect/")
async def detect_medicine(file: UploadFile = File(...)):
    try:
        session_id = str(uuid.uuid4())

        # Save uploaded image
        file_ext = file.filename.split(".")[-1]
        file_path = os.path.join(UPLOADS_DIR, f"{session_id}.{file_ext}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Load image using OpenCV
        image = cv2.imread(file_path)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # Run Roboflow model for medicine detection
        result = model.predict(image, confidence=40, overlap=30).json()

        # Initialize detection result
        detection_result = None
        
        # Process predictions
        for prediction in result["predictions"]:
            if prediction["class"] == "medicine":
                detection_id = f"{session_id}_0"  # We'll just use the first medicine detected

                x1 = int(prediction["x"] - prediction["width"] / 2)
                y1 = int(prediction["y"] - prediction["height"] / 2)
                x2 = int(prediction["x"] + prediction["width"] / 2)
                y2 = int(prediction["y"] + prediction["height"] / 2)

                # Mark detection on image
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Extract region of interest for OCR
                roi = image[y1:y2, x1:x2]

                # Perform OCR using GPU-accelerated EasyOCR
                ocr_results = reader.readtext(roi)
                medicine_name = " ".join([text for _, text, _ in ocr_results]) if ocr_results else ""
                confidence = ocr_results[0][2] if ocr_results else 0.0

                if medicine_name:
                    # Get composition and side effects from Gemini API
                    composition = get_drug_composition(medicine_name)
                    side_effects = get_drug_side_effects(medicine_name)
                    
                    # Check authenticity
                    is_authentic = is_authentic_drug(composition)
                    
                    # Create detection result
                    detection_result = {
                        "detection_id": detection_id,
                        "medicine_name": medicine_name.strip(),
                        "confidence": float(confidence),
                        "composition": composition,
                        "side_effects": side_effects,
                        "is_authentic": is_authentic
                    }
                    
                    # We'll process only the first medicine detected
                    break

        # If no medicine detected
        if detection_result is None:
            detection_result = {
                "detection_id": f"{session_id}_none",
                "medicine_name": "No medicine detected",
                "confidence": 0.0,
                "composition": "Unknown",
                "side_effects": "Not Available",
                "is_authentic": False
            }

        # Save the annotated image
        output_path = os.path.join(RESULTS_DIR, f"{session_id}_result.{file_ext}")
        cv2.imwrite(output_path, image)

        # Construct image URL
        image_url = f"http://127.0.0.1:8080/uploads/{session_id}.{file_ext}"
        
        # Add image URL to the result
        detection_result["image_url"] = image_url

        return detection_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error processing image: {str(e)}")

# ==========================
#  UPDATE MEDICINE NAME API
# ==========================
@app.put("/api/update-medicine-name/")
async def update_medicine_name(update: MedicineUpdate):
    try:
        # Get new medicine information
        new_name = update.new_name
        composition = get_drug_composition(new_name)
        side_effects = get_drug_side_effects(new_name)
        is_authentic = is_authentic_drug(composition)
        
        return {
            "success": True,
            "detection_id": update.detection_id,
            "updated_name": new_name,
            "composition": composition,
            "side_effects": side_effects,
            "is_authentic": is_authentic
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error updating medicine name: {str(e)}")

# ==========================
#  RUN FASTAPI SERVER
# ==========================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
from flask import Flask, render_template, request
import os
from modules.ocr_extraction import extract_text
from modules.medicine_verification import verify_medicine

app = Flask(__name__)

UPLOAD_FOLDER = "static/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def upload_and_verify():
    if request.method == "POST":
        file = request.files["image"]
        if file:
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(image_path)

            # Extract medicine names using EasyOCR
            extracted_medicines = extract_text(image_path)

            # Verify each medicine with Gemini API + Official CSV
            verification_results = {med: verify_medicine(med) for med in extracted_medicines}

            return render_template("verify.html", verification_results=verification_results)

    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True)

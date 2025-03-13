import easyocr
import re

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'])

def extract_text(image_path):
    """
    Extracts potential medicine names from a bill using EasyOCR.
    
    :param image_path: Path to the uploaded bill image
    :return: List of extracted medicine names
    """
    results = reader.readtext(image_path)
    extracted_text = [res[1] for res in results]  # Extract only text

    # Filter out potential medicine names using regex (Modify as needed)
    medicine_names = [text for text in extracted_text if re.match(r"^[A-Za-z0-9\s-]+$", text)]

    return medicine_names

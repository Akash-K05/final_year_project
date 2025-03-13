import google.generativeai as genai
import pandas as pd
import os

# Load Official Drug Database (CSV)
csv_path = os.path.join("database", "official_drugs.csv")
official_drugs = pd.read_csv(csv_path)

# Configure Gemini API Key
genai.configure(api_key="AIzaSyAAiveK88QlGhAN_CbXLYxtCVOMipAdnPw")

def get_drug_composition(medicine_name):
    """
    Queries Gemini API for the composition of a given medicine.
    
    :param medicine_name: Name of the medicine
    :return: Extracted composition details
    """
    model = genai.GenerativeModel("gemini-pro")  # Use appropriate Gemini model

    response = model.generate_content(f"Give me the chemical composition of the medicine: {medicine_name}.")
    
    if response and hasattr(response, "text"):
        return response.text.strip()
    return "Composition not found"

def verify_medicine(medicine_name):
    """
    Verifies if the extracted medicine composition matches the official database.

    :param medicine_name: Name of the extracted medicine
    :return: Verification result (Match / No Match)
    """
    gemini_composition = get_drug_composition(medicine_name)

    # Check against CSV database
    official_match = official_drugs[official_drugs["Medicine Name"].str.lower() == medicine_name.lower()]
    
    if not official_match.empty:
        official_composition = official_match.iloc[0]["Composition"]
        if official_composition.lower() in gemini_composition.lower():
            return f"✅ Verified: {medicine_name} contains {official_composition}"
        else:
            return f"❌ Alert: {medicine_name} composition mismatch!"
    return f"⚠️ Warning: {medicine_name} not found in official database."

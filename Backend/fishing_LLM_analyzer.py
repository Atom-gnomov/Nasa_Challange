import os
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv


def parse_gemini_response(response_text):
    """
    Cleans Gemini API response and parses it as JSON.
    Returns a dictionary with keys: rating, justification, recommendations.
    """
    cleaned = response_text.strip()
    # Remove code block markers
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    # Replace doubled quotes with normal quotes
    cleaned = cleaned.replace('""', '"')
    # Remove trailing comma before closing brace if present
    if cleaned.endswith(",}"):
        cleaned = cleaned.replace(",}", "}")
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print("❌ JSON decode failed. Returning defaults.")
        return {
            "rating": "N/A",
            "justification": "Failed to decode response.",
            "recommendations": cleaned[:200]  # partial raw response
        }


def evaluate_fishing_with_gemini(air_temp_par,
                                 pressure_kpa_par,
                                 wind_speed_par,
                                 moon_phase_par,
                                 water_temp_par):
    """
    Evaluates fishing suitability using Google Gemini API.
    Returns a pandas DataFrame with columns: date, rating, justification, recommendations.
    """
    # Load API key
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: API key not found. Please set GEMINI_API_KEY in your environment.")
        return pd.DataFrame(columns=["rating", "justification", "recommendations"])

    genai.configure(api_key=api_key)

    # Build prompt
    prompt_text = f"""
    You are an expert angler and meteorologist.
    Analyze the provided weather conditions and evaluate fishing suitability.

    Input Data:
    - Air Temperature: {air_temp_par}°C
    - Atmospheric Pressure: {pressure_kpa_par} kPa
    - Wind Speed: {wind_speed_par} m/s
    - Moon Phase: "{moon_phase_par}"
    - Water Temperature: {water_temp_par}°C

    Response Requirements:
    1. Respond ONLY in JSON format.
    2. JSON must contain exactly: "rating", "justification", "recommendations".
    3. Rating: one of "very poor", "poor", "average", "good", "excellent".
    4. Justification: ≤35 words.
    5. Recommendations: ≤3 sentences, combining gear and general tips.

    Example:
    {{
      "rating": "good",
      "justification": "Stable pressure and warm water should make fish active.",
      "recommendations": "Use topwater lures or spinners. A medium-light spinning rod is ideal. Polarized sunglasses help reduce glare."
    }}
    """

    try:
        print("Sending request to Gemini API...")
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt_text)

        result = parse_gemini_response(response.text)

        # Convert to DataFrame
        df_result = pd.DataFrame([{
            "rating": result.get("rating", "N/A"),
            "justification": result.get("justification", "N/A"),
            "recommendations": result.get("recommendations", "N/A")
        }])

        return df_result

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return pd.DataFrame([{
            "rating": "N/A",
            "justification": str(e),
            "recommendations": "Error during Gemini evaluation."
        }])



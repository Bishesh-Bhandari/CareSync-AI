from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json

load_dotenv()
# Configure Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.5-flash")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict later
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class SymptomRequest(BaseModel):
    symptoms: str = Field(min_length=5)

@app.get("/")
def home():
    return {"message": "HealthSync Backend Running"}

@app.post("/analyze")
def analyze(data: SymptomRequest):

    prompt = f"""
    A patient describes their symptoms as: "{data.symptoms}"

    Respond ONLY with a JSON object in this exact format:

    {{
      "condition": "<most likely condition>",
      "severity": "<Mild | Moderate | Severe>",
      "recommendations": [
        "<recommendation1>",
        "<recommendation2>",
        "<recommendation3>"
      ]
    }}
    """

    try:
        response = model.generate_content(prompt)

        raw = response.text.strip()

        print("\n========== GEMINI RAW RESPONSE ==========")
        print(raw)
        print("TYPE:", type(raw))
        print("=========================================\n")

        result = json.loads(raw)

        return result

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=500,
            detail="Gemini returned invalid JSON."
        )

    except Exception as e:
      print("\n========== ERROR ==========")
    print(e)
    print("===========================\n")
    raise HTTPException(
        status_code=500,
        detail=str(e)
    )
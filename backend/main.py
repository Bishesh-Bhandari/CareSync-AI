from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os, json
import json
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")


app = FastAPI()

# Allow your frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class SymptomRequest(BaseModel):
    symptoms: str

@app.get("/")
def home():
    return {"message": "HealthSync Backend Running"}

@app.post("/analyze")
def analyze(data: SymptomRequest):
    prompt = f"""
    A patient describes their symptoms as: "{data.symptoms}"

    Respond ONLY with a JSON object — no markdown, no explanation — in this exact shape:
    {{
      "condition": "<most likely condition in plain language>",
      "severity": "<Mild | Moderate | Severe>",
      "recommendations": ["<step 1>", "<step 2>", "<step 3>"]
    }}
    """

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    result = json.loads(raw)  # safe because we prompted for pure JSON
    return result
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SymptomRequest(BaseModel):
    symptoms: str

@app.get("/")
def home():
    return {
        "message": "HealthSync Backend Running"
    }

@app.post("/analyze")
def analyze(data: SymptomRequest):

    print(data.symptoms)

    return {
        "received": data.symptoms
    }
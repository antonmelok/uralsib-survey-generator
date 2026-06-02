from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Any
from pathlib import Path
import uvicorn
import json
import csv
import io

from llm_client import generate_survey_from_journey
from prompts import SYSTEM_PROMPT
import database as db

app = FastAPI(title="Bank Survey Generator MVP")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД
@app.on_event("startup")
def startup_event():
    db.init_db()

class SurveyRequest(BaseModel):
    journey: Any
    hint: Optional[str] = None

class EditRequest(BaseModel):
    edited_result: dict

@app.post("/api/generate")
async def generate_survey(request: SurveyRequest):
    result = generate_survey_from_journey(request.journey, request.hint)
    survey_id = db.save_survey(
        journey=request.journey,
        hint=request.hint,
        result=result,
        prompt=SYSTEM_PROMPT,
        model_name="meta-llama-3.1-8b-instruct"
    )
    return {**result, "survey_id": survey_id}

@app.get("/api/surveys")
async def list_surveys(limit: int = 50):
    return db.get_all_surveys(limit)

@app.get("/api/surveys/{survey_id}")
async def get_survey(survey_id: int):
    surveys = db.get_all_surveys(limit=1000)
    for s in surveys:
        if s["id"] == survey_id:
            return s
    raise HTTPException(status_code=404, detail="Survey not found")

@app.get("/api/surveys/export/csv")
async def export_surveys_csv():
    surveys = db.get_all_surveys(limit=500)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "category", "relevance", "questions_count", "hint"])
    
    for s in surveys:
        try:
            res = json.loads(s["generated_result"])
            writer.writerow([
                s["id"], s["created_at"],
                res.get("category", " "),
                res.get("relevance", " "),
                len(res.get("questions", [])),
                s["hint"] or " "
            ])
        except Exception:
            continue
            
    return Response(
        output.getvalue(), 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=surveys.csv"}
    )

@app.put("/api/surveys/{survey_id}/edit")
async def save_survey_edit(survey_id: int, request: EditRequest):
    success = db.update_survey_edited_result(survey_id, request.edited_result)
    if not success:
        raise HTTPException(status_code=404, detail="Survey not found")
    return {"status": "ok", "message": "Edit saved"}

# Раздача фронтенда
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
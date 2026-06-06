from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel, validator, ValidationError
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

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД при старте
@app.on_event("startup")
def startup_event():
    db.init_db()

# Глобальный обработчик ошибок валидации
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return Response(
        status_code=422,
        content=json.dumps({
            "detail": "Ошибка валидации данных",
            "errors": exc.errors()
        }, ensure_ascii=False),
        media_type="application/json"
    )

class SurveyRequest(BaseModel):
    journey: Any
    hint: Optional[str] = None

    @validator('journey')
    def journey_not_empty(cls, v):
        if v is None:
            raise ValueError('Путь клиента не может быть пустым')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Путь клиента не может быть пустой строкой')
        if isinstance(v, (dict, list)) and len(v) == 0:
            raise ValueError('Путь клиента не может быть пустым объектом')
        return v

    class Config:
        extra = 'forbid'

class SurveyResponse(BaseModel):
    category: str
    relevance: float
    questions: List[str]
    survey_id: int

class EditRequest(BaseModel):
    edited_result: dict

    @validator('edited_result')
    def validate_edited_result(cls, v):
        if 'category' not in v:
            raise ValueError('Отсутствует поле category')
        if 'questions' not in v:
            raise ValueError('Отсутствует поле questions')
        if 'relevance' not in v:
            raise ValueError('Отсутствует поле relevance')
        
        if not isinstance(v['category'], str) or not v['category'].strip():
            raise ValueError('category должен быть непустой строкой')
        if not isinstance(v['questions'], list) or len(v['questions']) == 0:
            raise ValueError('questions должен быть непустым списком')
        if not isinstance(v['relevance'], (int, float)) or v['relevance'] < 0 or v['relevance'] > 1:
            raise ValueError('relevance должен быть числом от 0.0 до 1.0')
        
        for i, q in enumerate(v['questions']):
            if not isinstance(q, str) or not q.strip():
                raise ValueError(f'Вопрос #{i+1} должен быть непустой строкой')
        
        return v

@app.post("/api/generate", response_model=SurveyResponse)
async def generate_survey(request: SurveyRequest):
    if not request.journey:
        raise HTTPException(
            status_code=400,
            detail="Путь клиента не может быть пустым. Введите данные о действиях клиента."
        )
    
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
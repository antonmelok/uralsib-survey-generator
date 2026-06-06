import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "surveys.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                journey TEXT,
                hint TEXT,
                generated_result TEXT,
                prompt TEXT,
                model_name TEXT,
                edited_result TEXT
            )
        """)
        conn.commit()

def save_survey(journey, hint, result, prompt, model_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO surveys (created_at, journey, hint, generated_result, prompt, model_name)
            VALUES (datetime('now'), ?, ?, ?, ?, ?)
        """, (
            json.dumps(journey, ensure_ascii=False),
            hint,
            json.dumps(result, ensure_ascii=False),
            prompt,
            model_name
        ))
        conn.commit()
        return cursor.lastrowid

def get_all_surveys(limit=50):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM surveys ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def update_survey_edited_result(survey_id, edited_result):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE surveys SET edited_result = ? WHERE id = ?", 
                       (json.dumps(edited_result, ensure_ascii=False), survey_id))
        conn.commit()
        return cursor.rowcount > 0
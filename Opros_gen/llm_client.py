import requests
import json
import re
from prompts import SYSTEM_PROMPT

# Эндпоинт LM Studio (OpenAI совместимый)
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def generate_survey_from_journey(journey_data, hint=None):
    user_content = f"Данные клиентского пути:\n{json.dumps(journey_data, ensure_ascii=False)}"
    if hint:
        user_content += f"\n\nДополнительная подсказка от аналитика: {hint}"

    payload = {
        "model": "meta-llama-3.1-8b-instruct", # LM Studio подхватит загруженную модель
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.6,
        "max_tokens": 1024,
        "stream": False
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        # Извлечение JSON из ответа (убираем markdown-теги ```json и ```)
        match = re.search(r'\{[\s\S]*\}', answer)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        else:
            raise ValueError("JSON not found in response")

    except Exception as e:
        return {
            "category": "Ошибка",
            "relevance": 0.0,
            "questions": [f"Не удалось получить ответ от LLM. Проверьте, запущен ли LM Studio. Детали: {str(e)}"]
        }
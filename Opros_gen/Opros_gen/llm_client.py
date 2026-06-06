import requests
import json
import re
from prompts import SYSTEM_PROMPT

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MAX_JOURNEY_LENGTH = 10000

def generate_survey_from_journey(journey_data, hint=None):
    # Ограничение длины пути клиента
    if isinstance(journey_data, str) and len(journey_data) > MAX_JOURNEY_LENGTH:
        journey_data = journey_data[:MAX_JOURNEY_LENGTH] + "\n... [текст обрезан из-за превышения лимита]"
    
    user_content = f"Данные клиентского пути:\n{json.dumps(journey_data, ensure_ascii=False)}"
    if hint:
        user_content += f"\n\nДополнительная подсказка от аналитика: {hint}"

    payload = {
        "model": "meta-llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.6,
        "max_tokens": 2048,
        "stream": False
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        match = re.search(r'\{[\s\S]*\}', answer)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        else:
            raise ValueError("JSON not found in response")

    except requests.exceptions.Timeout:
        return {
            "category": "Ошибка",
            "relevance": 0.0,
            "questions": [
                "Превышено время ожидания ответа от модели. Попробуйте сократить путь клиента или повторить запрос."
            ]
        }
    except requests.exceptions.ConnectionError:
        return {
            "category": "Ошибка",
            "relevance": 0.0,
            "questions": [
                "Не удалось подключиться к LM Studio. Убедитесь, что приложение запущено и Local Server активен."
            ]
        }
    except Exception as e:
        return {
            "category": "Ошибка",
            "relevance": 0.0,
            "questions": [f"Ошибка генерации: {str(e)}"]
        }
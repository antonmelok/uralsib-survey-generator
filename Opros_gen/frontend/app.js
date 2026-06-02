document.addEventListener('DOMContentLoaded', () => {
    loadHistory();

    document.getElementById('generateBtn').addEventListener('click', generateSurvey);
    document.getElementById('saveEditBtn').addEventListener('click', saveEdits);
});

async function generateSurvey() {
    const btn = document.getElementById('generateBtn');
    btn.textContent = 'Генерация...';
    btn.disabled = true;

    try {
        const journey = document.getElementById('journeyInput').value;
        const hint = document.getElementById('hintInput').value;
        
        // Пытаемся распарсить как JSON, если не получится - отправим как текст
        let journeyParsed;
        try { journeyParsed = JSON.parse(journey); } catch { journeyParsed = journey; }

        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ journey: journeyParsed, hint: hint || null })
        });
        const data = await res.json();
        displayResult(data);
        loadHistory(); // Обновить список
    } catch (e) {
        alert('Ошибка: ' + e.message);
    } finally {
        btn.textContent = 'Сгенерировать';
        btn.disabled = false;
    }
}

function displayResult(data) {
    const section = document.getElementById('resultSection');
    section.style.display = 'block';
    document.getElementById('resCategory').textContent = data.category;
    document.getElementById('resRelevance').textContent = `Релевантность: ${data.relevance}`;
    
    const list = document.getElementById('resQuestions');
    list.innerHTML = data.questions.map(q => `<li>${q}</li>`).join('');
    section.dataset.surveyId = data.survey_id;
    section.dataset.originalResult = JSON.stringify(data);
    window.scrollTo(0, section.offsetTop);
}

async function saveEdits() {
    const section = document.getElementById('resultSection');
    const id = section.dataset.surveyId;
    // В MVP просто сохраняем тот же результат, в реальности тут была бы форма редактирования
    const original = JSON.parse(section.dataset.originalResult);
    
    await fetch(`/api/surveys/${id}/edit`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_result: original })
    });
    alert('Правки сохранены!');
}

async function loadHistory() {
    const res = await fetch('/api/surveys');
    const surveys = await res.json();
    const container = document.getElementById('historyList');
    
    container.innerHTML = surveys.map(s => {
        let parsed = {};
        try { parsed = JSON.parse(s.generated_result); } catch {}
        return `
            <div class="history-item" onclick="showHistoryItem(${s.id}, '${escapeHtml(JSON.stringify(parsed))}')">
                <div class="history-date">${new Date(s.created_at).toLocaleString()}</div>
                <strong>${parsed.category || 'Без категории'}</strong>
                <div style="font-size:12px; margin-top:5px;">Вопросов: ${parsed.questions ? parsed.questions.length : 0}</div>
            </div>
        `;
    }).join('');
}

function showHistoryItem(id, jsonString) {
    const data = JSON.parse(jsonString);
    data.survey_id = id;
    displayResult(data);
}

function escapeHtml(text) {
    return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
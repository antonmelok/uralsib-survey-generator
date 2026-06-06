document.addEventListener('DOMContentLoaded', () => {
    loadHistory();

    document.getElementById('generateBtn').addEventListener('click', generateSurvey);
    document.getElementById('saveEditBtn').addEventListener('click', saveEdits);
    
    // Ограничение длины ввода
    document.getElementById('journeyInput').addEventListener('input', function(e) {
        const maxLength = 10000;
        if (e.target.value.length > maxLength) {
            e.target.value = e.target.value.substring(0, maxLength);
            alert(`Максимальная длина пути клиента: ${maxLength} символов`);
        }
    });
});

async function generateSurvey() {
    const journeyInput = document.getElementById('journeyInput').value.trim();
    
    if (!journeyInput) {
        alert('️ Введите путь клиента перед генерацией опроса');
        document.getElementById('journeyInput').focus();
        return;
    }
    
    const btn = document.getElementById('generateBtn');
    btn.textContent = 'Генерация...';
    btn.disabled = true;

    try {
        let journeyParsed;
        try { 
            journeyParsed = JSON.parse(journeyInput); 
        } catch { 
            journeyParsed = journeyInput; 
        }

        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                journey: journeyParsed, 
                hint: document.getElementById('hintInput').value.trim() || null 
            })
        });
        
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Ошибка генерации');
        }
        
        const data = await res.json();
        displayResult(data);
        loadHistory();
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
    const original = JSON.parse(section.dataset.originalResult);
    
    await fetch(`/api/surveys/${id}/edit`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_result: original })
    });
    alert('Правки сохранены!');
}

let currentEditId = null;

async function loadHistory() {
    const res = await fetch('/api/surveys');
    const surveys = await res.json();
    const container = document.getElementById('historyList');
    
    container.innerHTML = surveys.map(s => {
        let parsed = {};
        try { parsed = JSON.parse(s.generated_result); } catch {}
        return `
            <div class="history-item">
                <button class="edit-btn" onclick="openEditModal(${s.id}, '${escapeHtml(JSON.stringify(parsed))}')">
                    Редактировать
                </button>
                <div class="history-date">${new Date(s.created_at).toLocaleString()}</div>
                <strong>${parsed.category || 'Без категории'}</strong>
                <div style="font-size:12px; margin-top:5px;">Вопросов: ${parsed.questions ? parsed.questions.length : 0}</div>
            </div>
        `;
    }).join('');
}

function openEditModal(id, jsonString) {
    const data = JSON.parse(jsonString);
    currentEditId = id;
    
    document.getElementById('editCategory').value = data.category || '';
    document.getElementById('editRelevance').value = data.relevance || 0;
    document.getElementById('editQuestions').value = (data.questions || []).join('\n');
    
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
    currentEditId = null;
}

async function saveEditFromModal() {
    if (!currentEditId) return;
    
    const category = document.getElementById('editCategory').value.trim();
    const relevance = parseFloat(document.getElementById('editRelevance').value);
    const questionsText = document.getElementById('editQuestions').value.trim();
    
    if (!category) {
        alert('Категория не может быть пустой');
        return;
    }
    if (isNaN(relevance) || relevance < 0 || relevance > 1) {
        alert('Релевантность должна быть от 0.0 до 1.0');
        return;
    }
    
    const questions = questionsText.split('\n').filter(q => q.trim());
    if (questions.length === 0) {
        alert('Добавьте хотя бы один вопрос');
        return;
    }
    
    const editedResult = {
        category,
        relevance,
        questions
    };
    
    try {
        const res = await fetch(`/api/surveys/${currentEditId}/edit`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ edited_result: editedResult })
        });
        
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Ошибка сохранения');
        }
        
        alert('Изменения сохранены');
        closeEditModal();
        loadHistory();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

function showHistoryItem(id, jsonString) {
    const data = JSON.parse(jsonString);
    data.survey_id = id;
    displayResult(data);
}

function escapeHtml(text) {
    return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
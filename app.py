import os
import threading
import time
import uuid
from flask import Flask, jsonify, render_template_string, request

# Для само-пингования
import requests

app = Flask(__name__)

tasks = {}


# --- НАЧАЛО БЛОКА АВТО-ПИНГЕРА ---
def self_pinger():
    """Фоновая функция, которая пингует сайт, чтобы Render не усыпил его"""
    # Ждем 10 секунд после старта сервера, чтобы он успел подняться
    time.sleep(10)
    print("[PINGER] Авто-пингер успешно запущен!")

    # Render выдает URL приложения в переменную окружения RENDER_EXTERNAL_URL
    # Если её нет (тест локально), используем локальный адрес
    self_url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")

    while True:
        try:
            # Делаем обычный GET запрос на главную страницу
            response = requests.get(self_url, timeout=10)
            print(
                f"[PINGER] Пинг выполнен успешно. Статус: {response.status_code}"
            )
        except Exception as e:
            print(f"[PINGER] Ошибка пинга: {e}")

        # Бесплатный Render засыпает после 15 минут простоя.
        # Будем будить его каждые 10 минут (600 секунд) с запасом.
        time.sleep(600)


# Запуск пингера в отдельном потоке, чтобы он не мешал основному сайту
pinger_thread = threading.Thread(target=self_pinger, daemon=True)
pinger_thread.start()
# --- КОНЕЦ БЛОКА АВТО-ПИНГЕРА ---


@app.route("/")
def index():
    # Твой HTML код остается точно таким же, как в первом ответе
    html_code = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Gemini Bridge Chat</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f4f4f9; }
            #chatbox { height: 300px; border: 1px solid #ccc; background: #fff; overflow-y: scroll; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
            .message { margin: 10px 0; padding: 8px 12px; border-radius: 5px; }
            .user { background: #e1f5fe; text-align: right; }
            .bot { background: #e8f5e9; text-align: left; }
            #input-area { display: flex; gap: 10px; }
            input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
            button { padding: 10px 20px; border: none; background: #007bff; color: white; border-radius: 5px; cursor: pointer; }
            button:disabled { background: #ccc; }
        </style>
    </head>
    <body>
        <h2>Чат с Gemini через домашний ПК</h2>
        <div id="chatbox"></div>
        <div id="input-area">
            <input type="text" id="user-input" placeholder="Введите ваш вопрос...">
            <button id="send-btn" onclick="sendQuestion()">Отправить</button>
        </div>

        <script>
            let currentRequestId = null;
            let checkAnswerInterval = null;

            function appendMessage(text, type) {
                const chatbox = document.getElementById('chatbox');
                const div = document.createElement('div');
                div.className = `message ${type}`;
                div.innerText = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }

            async function sendQuestion() {
                const input = document.getElementById('user-input');
                const btn = document.getElementById('send-btn');
                const text = input.value.trim();
                if (!text) return;

                appendMessage(text, 'user');
                input.value = '';
                input.disabled = true;
                btn.disabled = true;

                try {
                    let response = await fetch('/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: text })
                    });
                    let data = await response.json();
                    currentRequestId = data.id;

                    checkAnswerInterval = setInterval(checkAnswer, 2000);
                } catch (e) {
                    appendMessage("Ошибка отправки вопроса.", "bot");
                    input.disabled = false;
                    btn.disabled = false;
                }
            }

            async function checkAnswer() {
                if (!currentRequestId) return;
                
                try {
                    let response = await fetch(`/get_answer/${currentRequestId}`);
                    let data = await response.json();

                    if (data.status === "completed") {
                        clearInterval(checkAnswerInterval);
                        appendMessage(data.answer, 'bot');
                        
                        document.getElementById('user-input').disabled = false;
                        document.getElementById('send-btn').disabled = false;
                        currentRequestId = null;
                    }
                } catch (e) {
                    console.error("Ошибка проверки ответа", e);
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_code)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    req_id = str(uuid.uuid4())
    tasks[req_id] = {"question": data["question"], "answer": None}
    return jsonify({"id": req_id, "status": "pending"})


@app.route("/get_answer/<req_id>", methods=["GET"])
def get_answer(req_id):
    task = tasks.get(req_id)
    if not task:
        return jsonify({"status": "not_found"}), 404
    if task["answer"] is not None:
        return jsonify({"status": "completed", "answer": task["answer"]})
    return jsonify({"status": "pending"})


@app.route("/get_new_task", methods=["GET"])
def get_new_task():
    for req_id, task in tasks.items():
        if task["answer"] is None:
            return jsonify({"id": req_id, "question": task["question"]})
    return jsonify({"status": "no_tasks"})


@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.json
    req_id = data.get("id")
    answer = data.get("answer")

    if req_id in tasks:
        tasks[req_id]["answer"] = answer
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Task not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

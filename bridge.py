import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# НАСТРОЙКИ
RENDER_URL = "https://твой-субдомен.onrender.com"  # ЗАМЕНИ НА СВОЙ URL НА RENDER

# Подключаемся к твоему уже открытому браузеру Chrome
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

print("Успешно подключились к Chrome. Начинаем цикл проверки вопросов...")

while True:
    try:
        # 1. Проверяем наличие новых задач на Render
        response = requests.get(f"{RENDER_URL}/get_new_task")
        if response.status_code != 200:
            print("Ошибка связи с сервером Render. Пробуем снова...")
            time.sleep(3)
            continue
            
        data = response.json()

        if "id" in data:
            task_id = data["id"]
            question = data["question"]
            print(f"\n[!] Появился новый вопрос: {question}")

            # 2. Открываем новую вкладку Gemini, чтобы не засорять историю
            driver.execute_script("window.open('https://gemini.google.com/', '_blank');")
            # Переключаемся на неё
            driver.switch_to.window(driver.window_handles[-1])

            # Ждем загрузки поля ввода
            # Селектор поля ввода в Gemini часто меняется, text-area с ролью combobox — самый стабильный вариант
            wait = WebDriverWait(driver, 15)
            input_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'], textarea")))

            # Вводим текст вопроса
            input_box.click()
            input_box.send_keys(question)
            time.sleep(0.5)
            input_box.send_keys(Keys.ENTER)
            print("Вопрос отправлен в Gemini. Ждем ответа (12 секунд)...")

            # Ждем генерации ответа (10-12 секунд с запасом)
            time.sleep(12)

            # 3. Извлекаем ответ. Ищем блоки ответов модели.
            # Класс 'model-response' стабильно используется Google для контейнеров ответов Gemini.
            response_elements = driver.find_elements(By.CSS_SELECTOR, "div.model-response")
            
            if response_elements:
                # Берем самый последний элемент на странице (актуальный ответ)
                last_response = response_elements[-1]
                answer_text = last_response.text
                print("Ответ успешно скопирован!")
            else:
                answer_text = "Ошибка: Не удалось скопировать ответ со страницы Gemini."
                print("Критическая ошибка: Контейнер с ответом не найден.")

            # 4. Отправляем ответ обратно на Render
            payload = {"id": task_id, "answer": answer_text}
            res = requests.post(f"{RENDER_URL}/submit_answer", json=payload)
            if res.status_code == 200:
                print("Ответ успешно доставлен на сайт Render.")
            else:
                print("Не удалось отправить ответ обратно на Render.")

            # 5. Закрываем текущую вкладку чата и возвращаемся на исходную позицию
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        else:
            # Если вопросов нет, просто пишем в консоль точку раз в 3 секунды
            print(".", end="", flush=True)

    except Exception as e:
        print(f"\n[Ошибка в цикле скрипта]: {e}")
        # Если вкладка осталась открытой при ошибке, пробуем вернуться на главную
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

    # Задержка 3 секунды перед следующей проверкой Render
    time.sleep(3)

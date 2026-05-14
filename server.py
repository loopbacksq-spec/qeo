import uuid
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="P2P Signaling Server")

# Временная база данных в оперативной памяти (ОЗУ). Нагрузка на сервер = 0.
# Структура: { "api_key": {"username": "...", "ip": "...", "port": ...} }
users_db = {}


class RegisterRequest(BaseModel):
    username: str
    port: int  # Порт, который клиент открыл у себя для приема P2P сообщений


@app.get("/")
def read_root():
    return {"status": "online", "message": "P2P Signaling Server is running!"}


# 1. Регистрация нового пользователя и выдача API-ключа
@app.post("/api/register")
def register_user(data: RegisterRequest, request: Request):
    # Автоматически определяем публичный IP-адрес клиента
    client_ip = request.client.host

    # Генерируем уникальный API-ключ
    api_key = str(uuid.uuid4())

    users_db[api_key] = {
        "username": data.username,
        "ip": client_ip,
        "port": data.port,
        "status": "online",
    }

    return {
        "message": "Успешная регистрация!",
        "api_key": api_key,
        "your_detected_ip": client_ip,
    }


# 2. Обновление статуса/IP (пингующий эндпоинт, чтобы Render не спал)
@app.post("/api/ping")
def ping(api_key: str, port: int, request: Request):
    if api_key not in users_db:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")

    # Обновляем IP и порт на случай, если у пользователя изменился интернет
    users_db[api_key]["ip"] = request.client.host
    users_db[api_key]["port"] = port
    users_db[api_key]["status"] = "online"
    return {"status": "pong", "active_users": len(users_db)}


# 3. Поиск IP-адреса другого пользователя по его API-ключу
@app.get("/api/lookup/{target_api_key}")
def lookup_user(target_api_key: str, api_key: str):
    # Проверяем, что запрашивающий сам зарегистрирован
    if api_key not in users_db:
        raise HTTPException(status_code=401, detail="Доступ запрещен")

    if target_api_key not in users_db:
        raise HTTPException(
            status_code=404, detail="Пользователь с таким ключом не найден"
        )

    target = users_db[target_api_key]
    return {
        "username": target["username"],
        "ip": target["ip"],
        "port": target["port"],
        "status": target["status"],
    }

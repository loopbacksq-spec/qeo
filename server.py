import uuid
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="P2P Room Signaling Server")

# База данных комнат в ОЗУ. Нагрузка = 0.
# Структура: { "ОБЩИЙ_API_КЛЮЧ": [ {"username": "...", "ip": "...", "port": ...}, ... ] }
rooms_db = {}


class JoinRequest(BaseModel):
    api_key: str  # Общий ключ, к которому подключаются
    username: str
    port: int


@app.get("/")
def read_root():
    # Красивая статистика для главной страницы сайта
    total_rooms = len(rooms_db)
    total_users = sum(len(users) for users in rooms_db.values())

    return {
        "status": "online",
        "message": "P2P Room Server приветствует тебя!",
        "stats": {
            "активных_комнат (API ключей)": total_rooms,
            "всего_подключено_участников": total_users,
        },
        "instruction": "Чтобы создать новый общий API-ключ, сделай POST запрос на /api/create_room",
    }


# 1. Создать НОВЫЙ ОБЩИЙ API-ключ (Комнату)
@app.post("/api/create_room")
def create_room():
    shared_api_key = str(uuid.uuid4())[:8]  # Делаем короткий ключ из 8 символов для удобства в CMD
    rooms_db[shared_api_key] = []
    return {
        "message": "Общая сессия создана!",
        "shared_api_key": shared_api_key,
    }


# 2. Подключиться к существующему API-ключу
@app.post("/api/join")
def join_room(data: JoinRequest, request: Request):
    key = data.api_key
    if key not in rooms_db:
        raise HTTPException(
            status_code=404,
            detail="Такой API-ключ не найден. Сначала создайте его!",
        )

    client_ip = request.client.host

    # Удаляем старую запись этого юзера, если он переподключается
    rooms_db[key] = [u for u in rooms_db[key] if u["username"] != data.username]

    # Добавляем юзера в комнату
    user_info = {"username": data.username, "ip": client_ip, "port": data.port}
    rooms_db[key].append(user_info)

    # Возвращаем список ВСЕХ, кто сейчас в этой комнате, чтобы отправить им сообщения
    return {
        "message": f"Ты успешно подключился к комнате {key}!",
        "participants_count": len(rooms_db[key]),
        "peers": rooms_db[key],  # Список всех участников
    }

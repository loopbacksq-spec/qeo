import uuid
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Ultra-Optimized P2P Room Server")

# Хранилище комнат в ОЗУ
rooms_db = {}


class JoinRequest(BaseModel):
    api_key: str
    username: str
    port: int
    local_ip: str  # Клиент передает свой локальный IP для быстрой связи


class LeaveRequest(BaseModel):
    api_key: str
    username: str


@app.get("/")
def read_root():
    total_rooms = len(rooms_db)
    total_users = sum(len(users) for users in rooms_db.values())
    return {
        "status": "online",
        "stats": {
            "активных_сессий (API)": total_rooms,
            "участников_онлайн": total_users,
        },
    }


@app.post("/api/create_room")
def create_room():
    shared_api_key = str(uuid.uuid4())[:8]
    rooms_db[shared_api_key] = []
    return {"shared_api_key": shared_api_key}


@app.post("/api/join")
def join_room(data: JoinRequest, request: Request):
    key = data.api_key
    if key not in rooms_db:
        raise HTTPException(
            status_code=404, detail="API-ключ не найден или сессия закрыта."
        )

    # Запоминаем и внешний IP (от Render), и локальный IP (от самого ПК)
    user_info = {
        "username": data.username,
        "public_ip": request.client.host,
        "local_ip": data.local_ip,
        "port": data.port,
    }

    # Обновляем, если зашел заново
    rooms_db[key] = [u for u in rooms_db[key] if u["username"] != data.username]
    rooms_db[key].append(user_info)

    return {"participants_count": len(rooms_db[key]), "peers": rooms_db[key]}


# Эндпоинт для выхода: удаляет юзера, а если он был последним — удаляет ВСЮ комнату
@app.post("/api/leave")
def leave_room(data: LeaveRequest):
    key = data.api_key
    if key in rooms_db:
        # Удаляем пользователя из списка
        rooms_db[key] = [
            u for u in rooms_db[key] if u["username"] != data.username
        ]

        # Если в комнате никого не осталось — удаляем сессию из памяти!
        if len(rooms_db[key]) == 0:
            del rooms_db[key]
            return {"message": "Сессия успешно удалена, так как все вышли."}

        return {"message": "Вы вышли из сессии.", "left": len(rooms_db[key])}
    return {"message": "Сессия уже не существовала."}

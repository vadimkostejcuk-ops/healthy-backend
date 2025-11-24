from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import uvicorn
import os
import json

# --- БІБЛІОТЕКИ ДЛЯ БАЗИ ДАНИХ ---
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. НАЛАШТУВАННЯ БАЗИ ДАНИХ ---
# Якщо є посилання від Render (в інтернеті) - беремо його.
# Якщо немає (локально) - створюємо файл 'local.db' на комп'ютері.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Render іноді дає старий формат посилання, треба виправити на новий
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./local.db"  # Локальна база

# Створюємо двигун бази даних
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. МОДЕЛЬ ТАБЛИЦІ (Як виглядає рядок у базі) ---
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)  # Пошта має бути унікальною
    password = Column(String)  # У реальному проекті паролі треба хешувати!
    calories = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Створюємо таблицю, якщо її немає
Base.metadata.create_all(bind=engine)

# Функція для отримання доступу до бази (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- НАЛАШТУВАННЯ ШІ ---
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# --- МОДЕЛІ ДЛЯ ЗАПИТІВ ---
class UserParams(BaseModel):
    gender: str
    weight: float
    height: float
    age: int
    activity: float
    goal: str

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    calories: int


# --- ЕНДПОІНТИ (РУЧКИ) ---

@app.get("/")
def read_root():
    return {"message": "Database & AI Server is running!"}

# РОЗРАХУНОК (Без змін)
@app.post("/calculate")
def calculate_calories(user: UserParams):
    if user.gender == 'male':
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) + 5
    else:
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) - 161
    
    tdee = bmr * user.activity
    target_calories = tdee

    protein_ratio = 0.3
    fat_ratio = 0.3
    carb_ratio = 0.4

    if user.goal == 'lose':
        target_calories = tdee - 300
        protein_ratio = 0.35
        fat_ratio = 0.3
        carb_ratio = 0.35
    elif user.goal == 'gain':
        target_calories = tdee + 300
        protein_ratio = 0.3
        fat_ratio = 0.25
        carb_ratio = 0.45

    p_g = int((target_calories * protein_ratio) / 4)
    f_g = int((target_calories * fat_ratio) / 9)
    c_g = int((target_calories * carb_ratio) / 4)

    return {
        "bmr": int(bmr),
        "calories": int(target_calories),
        "macros": {"protein": p_g, "fat": f_g, "carbs": c_g}
    }

# ШІ ГЕНЕРАЦІЯ (Без змін)
@app.get("/get_meal")
def get_ai_meal(type: str):
    prompt = f"""
    Придумай одну смачну та просту страву для категорії '{type}'.
    JSON формат:
    {{
        "name": "Назва (укр)",
        "desc": "Склад (укр)",
        "cals": число,
        "p": число, "f": число, "c": число,
        "icon": "емодзі",
        "color": "HEX світлий фон"
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ти дієтолог. Відповідай JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9
        )
        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
        meal_data = json.loads(content)
        return meal_data
    except Exception as e:
        print(f"Error: {e}")
        return {
            "name": "Тимчасова страва", "desc": "ШІ відпочиває",
            "cals": 0, "p": 0, "f": 0, "c": 0, "icon": "🤖", "color": "#EEEEEE"
        }

# --- НОВА РУЧКА: РЕЄСТРАЦІЯ КОРИСТУВАЧА ---
@app.post("/register")
def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    # 1. Перевіряємо, чи є такий email
    existing_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Створюємо нового користувача
    new_user = UserDB(
        name=user.name,
        email=user.email,
        password=user.password, # Увага: тут треба хешувати в майбутньому!
        calories=user.calories
    )
    
    # 3. Записуємо в базу
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}

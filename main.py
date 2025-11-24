from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import uvicorn
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАЛАШТУВАННЯ OPENAI ---
# Ми беремо ключ зі "змінних середовища" (щоб не світити його в коді)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class UserParams(BaseModel):
    gender: str
    weight: float
    height: float
    age: int
    activity: float
    goal: str

@app.get("/")
def read_root():
    return {"message": "AI Server is running!"}

@app.post("/calculate")
def calculate_calories(user: UserParams):
    # (Тут стара логіка розрахунку залишається без змін)
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

# --- НОВА ШІ-РУЧКА ---
@app.get("/get_meal")
def get_ai_meal(type: str):
    
    # Промпт (Інструкція для ШІ)
    prompt = f"""
    Придумай одну смачну та просту страву для категорії '{type}' (сніданок, обід або вечеря).
    Відповідь МАЄ бути виключно у форматі JSON без зайвого тексту.
    Структура JSON:
    {{
        "name": "Назва страви (українською)",
        "desc": "Короткий склад інгредієнтів (українською)",
        "cals": приблизні калорії (число),
        "p": білки (число),
        "f": жири (число),
        "c": вуглеводи (число),
        "icon": "один емодзі, що підходить страві",
        "color": "світлий пастельний колір (HEX) для фону іконки (наприклад #FFF3E0)"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Використовуємо дешеву і швидку модель
            messages=[
                {"role": "system", "content": "Ти професійний дієтолог. Ти відповідаєш тільки чистим JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9 # Трішки креативності
        )
        
        # Отримуємо текст відповіді
        content = response.choices[0].message.content
        
        # Чистимо відповідь (іноді ШІ додає ```json ... ```)
        content = content.replace("```json", "").replace("```", "").strip()
        
        # Перетворюємо текст у справжній об'єкт Python
        meal_data = json.loads(content)
        
        return meal_data

    except Exception as e:
        print(f"Помилка OpenAI: {e}")
        # Якщо ШІ не спрацював (або закінчилися гроші), повертаємо "аварійну" страву
        return {
            "name": "Тимчасова страва",
            "desc": "ШІ відпочиває, спробуйте пізніше",
            "cals": 0, "p": 0, "f": 0, "c": 0,
            "icon": "🤖", "color": "#EEEEEE"
        }

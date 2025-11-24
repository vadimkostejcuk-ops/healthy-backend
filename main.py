from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import random  # <-- Підключили бібліотеку для випадкового вибору

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БАЗА ДАНИХ СТРАВ (Поки що проста) ---
meals_db = {
    "breakfast": [
        {"name": "Яєчня з тостами", "desc": "Яйця (2 шт), Хліб (2 шматка), Помідор", "cals": 450, "p": 20, "f": 25, "c": 40, "icon": "🍳", "color": "#FFF3E0"},
        {"name": "Сирники з ягодами", "desc": "Сир кисломолочний (200г), Яйце, Борошно, Ягоди", "cals": 520, "p": 35, "f": 15, "c": 45, "icon": "🥞", "color": "#FCE4EC"},
        {"name": "Авокадо-тост з рибою", "desc": "Хліб, Авокадо (50г), Червона риба (50г)", "cals": 480, "p": 20, "f": 25, "c": 30, "icon": "🥑", "color": "#E8F5E9"},
        {"name": "Вівсянка з бананом", "desc": "Вівсянка (80г), Молоко, Банан, Мед", "cals": 420, "p": 12, "f": 10, "c": 70, "icon": "🍌", "color": "#FFFDE7"}
    ],
    "lunch": [
        {"name": "Паста Болоньєзе", "desc": "Макарони, Фарш яловичий, Томатний соус", "cals": 700, "p": 35, "f": 25, "c": 70, "icon": "🍝", "color": "#FFEBEE"},
        {"name": "Борщ з пампушками", "desc": "Борщ український, Сметана, Часник", "cals": 550, "p": 20, "f": 25, "c": 50, "icon": "🥘", "color": "#FFEBEE"},
        {"name": "Стейк з картоплею", "desc": "Курячий стейк, Картопля запечена, Салат", "cals": 650, "p": 45, "f": 20, "c": 60, "icon": "🍗", "color": "#EFEBE9"},
        {"name": "Плов з куркою", "desc": "Рис, Куряче філе, Морква, Цибуля", "cals": 600, "p": 30, "f": 20, "c": 65, "icon": "🍚", "color": "#FFF3E0"}
    ],
    "dinner": [
        {"name": "Салат Цезар", "desc": "Курка, Салат айсберг, Сухарики, Соус", "cals": 450, "p": 30, "f": 20, "c": 15, "icon": "🥗", "color": "#E8F5E9"},
        {"name": "Риба з овочами", "desc": "Хек запечений, Броколі, Сметана", "cals": 400, "p": 35, "f": 10, "c": 15, "icon": "🐟", "color": "#E3F2FD"},
        {"name": "Піца (Cheat Meal)", "desc": "2 шматочки піци, сирний соус", "cals": 600, "p": 20, "f": 30, "c": 60, "icon": "🍕", "color": "#FFF3E0"},
        {"name": "Омлет з овочами", "desc": "3 яйця, Перець, Помідори, Зелень", "cals": 350, "p": 25, "f": 20, "c": 5, "icon": "🍳", "color": "#FFF8E1"}
    ]
}

class UserParams(BaseModel):
    gender: str
    weight: float
    height: float
    age: int
    activity: float
    goal: str

@app.get("/")
def read_root():
    return {"message": "Server is running!"}

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
        "macros": {
            "protein": p_g,
            "fat": f_g,
            "carbs": c_g
        }
    }

# --- НОВА РУЧКА: ОТРИМАТИ СТРАВУ ---
@app.get("/get_meal")
def get_random_meal(type: str):
    # type може бути: "breakfast", "lunch", "dinner"
    
    if type in meals_db:
        # Вибираємо випадкову страву зі списку
        meal = random.choice(meals_db[type])
        return meal
    else:
        return {"error": "Unknown meal type"}


import os
import asyncio
import logging
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, List, Optional
import copy

import matplotlib.pyplot as plt
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# --- КОНФИГУРАЦИЯ ---
YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
YANDEX_CLOUD_MODEL = os.getenv("YANDEX_CLOUD_MODEL", "yandexgpt-lite")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([YANDEX_CLOUD_FOLDER, YANDEX_CLOUD_API_KEY, BOT_TOKEN]):
    logger.error("Отсутствуют необходимые переменные окружения. Проверьте .env файл.")
    exit(1)

# Инициализация LLM
MODEL_NAME = f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}"
llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    temperature=0.1,
    timeout=60
)

# --- КАТАЛОГ ТОВАРОВ ---
CATALOG = [
    {"id": "p1",  "name": "Sony WH-1000XM5",            "category": "headphones", "brand": "Sony",     "price": 349, "color": "black",    "rating": 4.8, "tags": ["wireless", "noise-cancelling", "premium"]},
    {"id": "p2",  "name": "Sony WH-CH720N",              "category": "headphones", "brand": "Sony",     "price": 129, "color": "blue",     "rating": 4.4, "tags": ["wireless", "budget", "noise-cancelling"]},
    {"id": "p3",  "name": "Bose QuietComfort Ultra",     "category": "headphones", "brand": "Bose",     "price": 379, "color": "white",    "rating": 4.7, "tags": ["wireless", "noise-cancelling", "premium"]},
    {"id": "p4",  "name": "Apple AirPods Pro 2",         "category": "earbuds",     "brand": "Apple",    "price": 249, "color": "white",    "rating": 4.6, "tags": ["wireless", "noise-cancelling", "ios"]},
    {"id": "p5",  "name": "Anker Soundcore Liberty 4 NC","category": "earbuds",     "brand": "Anker",    "price": 99,  "color": "black",    "rating": 4.3, "tags": ["wireless", "budget", "noise-cancelling"]},
    {"id": "p6",  "name": "Logitech MX Master 3S",       "category": "mouse",       "brand": "Logitech", "price": 109, "color": "graphite", "rating": 4.8, "tags": ["wireless", "productivity", "premium"]},
    {"id": "p7",  "name": "Logitech Pebble 2",           "category": "mouse",       "brand": "Logitech", "price": 34,  "color": "white",    "rating": 4.2, "tags": ["wireless", "budget", "portable"]},
    {"id": "p8",  "name": "Keychron K2",                 "category": "keyboard",    "brand": "Keychron", "price": 89,  "color": "black",    "rating": 4.5, "tags": ["wireless", "mechanical", "compact"]},
    {"id": "p9",  "name": "NuPhy Air75",                 "category": "keyboard",    "brand": "NuPhy",    "price": 139, "color": "gray",     "rating": 4.6, "tags": ["wireless", "mechanical", "low-profile"]},
    {"id": "p10", "name": "Amazon Kindle Paperwhite",    "category": "ereader",     "brand": "Amazon",   "price": 149, "color": "black",    "rating": 4.7, "tags": ["reading", "portable", "gift"]},
]

# --- СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ (In-Memory) ---
user_states: dict[int, dict] = {}

def get_user_state(user_id: int) -> dict:
    if user_id not in user_states:
        user_states[user_id] = {
            "cart": [],
            "last_results": [],
            "current_candidate": None,
            "profile": {}
        }
    return user_states[user_id]

# --- ИНСТРУМЕНТЫ (TOOLS) ---

def find_products(
    query: str = "",
    category: Optional[str] = None,
    brand: Optional[str] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None
) -> List[dict]:
    """
    Search for products in the catalog matching the given criteria.
    Args:
        query: General search term.
        category: Product category (e.g., 'mouse', 'headphones').
        brand: Brand name.
        max_price: Maximum price limit.
        sort_by: Sorting option ('price_asc', 'price_desc', 'rating_desc').
    Returns:
        List of matching products.
    """
    results = []
    q_words = query.lower().split() if query else []
    
    for item in CATALOG:
        hay = f"{item['name']} {item['category']} {item['brand']} {' '.join(item['tags'])}".lower()
        if q_words and not all(w in hay for w in q_words):
            continue
        
        if category and item["category"] != category.lower():
            continue
        if brand and item["brand"].lower() != brand.lower():
            continue
        if max_price is not None and item["price"] > float(max_price):
            continue
            
        results.append(copy.deepcopy(item))
    
    if sort_by == "price_asc":
        results.sort(key=lambda x: x["price"])
    elif sort_by == "price_desc":
        results.sort(key=lambda x: -x["price"])
    elif sort_by == "rating_desc":
        results.sort(key=lambda x: -x["rating"])
        
    return results

def add_to_cart(product_id: str, quantity: int = 1) -> dict:
    """
    Add a specific product to the user's shopping cart by ID.
    Args:
        product_id: The unique ID of the product (e.g., 'p1').
        quantity: Number of items to add.
    Returns:
        Status dict.
    """
    # Эта функция используется только для схемы инструмента.
    # Реальная логика добавления выполняется вручную в коде бота.
    return {"ok": True, "message": "Added to cart logic."}

def update_user_profile(key: str, value: str) -> dict:
    """
    Save user preference to memory.
    """
    return {"ok": True, "key": key, "value": value}

# Схема инструментов для LLM
TOOLS_SCHEMA = [
    convert_to_openai_tool(find_products),
    convert_to_openai_tool(add_to_cart),
    convert_to_openai_tool(update_user_profile),
]

# --- АГЕНТЫ ---

@dataclass
class AgentContext:
    query: str
    max_price: Optional[float] = None
    candidates: List[dict] = field(default_factory=list)
    pros: dict = field(default_factory=dict)
    cons: dict = field(default_factory=dict)
    best: Optional[dict] = None
    auto_add: bool = False # Флаг для авто-добавления

class RetrieverAgent:
    def run(self, ctx: AgentContext, user_state: dict) -> AgentContext:
        sys_msg = SystemMessage(content=(
            "You are a product search assistant. Analyze the user request. "
            "1. Extract search parameters (category, brand, max_price). "
            "2. If user says 'cheapest' or 'самый дешевый', set sort_by='price_asc'. "
            "3. If user says 'best' or 'лучший', set sort_by='rating_desc'. "
            "4. If user explicitly asks to 'add to cart' or 'добавь в корзину', set a mental note, but still call find_products first to get the item."
        ))
        user_msg = HumanMessage(content=ctx.query)
        history = [sys_msg, user_msg]
        
        try:
            ai_msg = llm.bind_tools(TOOLS_SCHEMA).invoke(history)
        except Exception as e:
            logger.error(f"LLM Error in Retriever: {e}")
            ctx.candidates = find_products(query=ctx.query)
            return ctx

        tool_calls = getattr(ai_msg, "tool_calls", [])
        
        if tool_calls:
            for call in tool_calls:
                if call["name"] == "find_products":
                    args = call["args"]
                    results = find_products(**args)
                    
                    max_p = args.get("max_price")
                    if max_p:
                        ctx.max_price = float(max_p)
                        results = [p for p in results if p["price"] <= ctx.max_price]
                    
                    ctx.candidates = results[:5]
                    break
        else:
            logger.info("No tool call from LLM, attempting fallback search.")
            # Попытка определить категорию из запроса для фоллбэка
            ctx.candidates = find_products(query=ctx.query)

        return ctx

class ProsAgent:
    def run(self, ctx: AgentContext) -> AgentContext:
        ctx.pros = {}
        for prod in ctx.candidates:
            sys_msg = SystemMessage(content="List 1 short sentence about the main PRO of this product.")
            user_msg = HumanMessage(content=f"Product: {prod['name']}, Price: ${prod['price']}")
            try:
                ai_msg = llm.invoke([sys_msg, user_msg])
                ctx.pros[prod["id"]] = ai_msg.content
            except:
                ctx.pros[prod["id"]] = "High quality."
        return ctx

class ConsAgent:
    def run(self, ctx: AgentContext) -> AgentContext:
        ctx.cons = {}
        for prod in ctx.candidates:
            sys_msg = SystemMessage(content="List 1 short sentence about a potential CON of this product.")
            user_msg = HumanMessage(content=f"Product: {prod['name']}, Price: ${prod['price']}")
            try:
                ai_msg = llm.invoke([sys_msg, user_msg])
                ctx.cons[prod["id"]] = ai_msg.content
            except:
                ctx.cons[prod["id"]] = "None significant."
        return ctx

class RankerAgent:
    def run(self, ctx: AgentContext) -> AgentContext:
        candidates = ctx.candidates
        if ctx.max_price is not None:
            candidates = [p for p in candidates if p["price"] <= ctx.max_price]
        
        if not candidates:
            ctx.best = None
            return ctx
        
        # Сортировка: сначала рейтинг (убывание), потом цена (возрастание)
        # Если в запросе было "самый дешевый", LLM должен был передать sort_by='price_asc' в find_products,
        # но здесь мы перестраховываемся, если контекст потерян.
        # Однако, чтобы respects 'cheapest', мы полагаемся на то, что список уже отсортирован правильно из find_products.
        # Если sort_by не был применен, используем дефолт (рейтинг).
        
        # Простая эвристика: если в запросе есть "дешевый", сортируем по цене
        if "дешев" in ctx.query.lower() or "cheap" in ctx.query.lower():
             candidates = sorted(candidates, key=lambda x: x["price"])
        else:
             candidates = sorted(candidates, key=lambda x: (-x["rating"], x["price"]))
             
        ctx.best = candidates[0]
        return ctx

class CoordinatorAgent:
    def run(self, user_message: str, user_state: dict) -> tuple[str, Optional[dict], bool]:
        """
        Returns: (response_text, best_product_dict_or_None, should_auto_add)
        """
        ctx = AgentContext(query=user_message)
        
        # Проверка на интент добавления в корзину
        auto_add_intent = "добавь в корзину" in user_message.lower() or "add to cart" in user_message.lower() or "купи" in user_message.lower()
        
        # 1. Поиск
        ctx = RetrieverAgent().run(ctx, user_state)
        
        if not ctx.candidates:
            return "К сожалению, я не нашел товаров по вашему запросу. Попробуйте изменить параметры.", None, False

        # 2. Анализ (Плюсы/Минусы) - только для топ-3
        ctx.candidates = ctx.candidates[:3]
        ctx = ProsAgent().run(ctx)
        ctx = ConsAgent().run(ctx)

        # 3. Ранжирование
        ctx = RankerAgent().run(ctx)

        if not ctx.best:
            return "Товары найдены, но ни один не подходит под критерии.", None, False

        best = ctx.best
        pid = best["id"]
        
        # Формирование ответа
        text = (
            f"🏆 **Лучший вариант:** {best['name']}\n"
            f"💰 **Цена:** ${best['price']}\n"
            f"⭐ **Рейтинг:** {best['rating']}/5\n\n"
            f"✅ **Плюс:** {ctx.pros.get(pid, 'Отличное качество')}\n"
            f"❌ **Минус:** {ctx.cons.get(pid, 'Нет недостатков')}\n"
        )
        
        user_state["current_candidate"] = best
        
        if auto_add_intent:
            # Авто-добавление
            existing = next((i for i in user_state["cart"] if i["id"] == best["id"]), None)
            if existing:
                existing["quantity"] += 1
            else:
                user_state["cart"].append({
                    "id": best["id"],
                    "name": best["name"],
                    "price": best["price"],
                    "quantity": 1
                })
            
            final_text = f"✅ **Добавлено!**\n\n{text}\nТовар уже в корзине."
            return final_text, best, True
        else:
            final_text = f"{text}\n\nДобавить этот товар в корзину?"
            return final_text, best, False

# --- ФУНКЦИИ БОТА ---

def generate_catalog_image() -> str:
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.axis('off')
    
    y_pos = 0.95
    categories = {}
    
    for item in CATALOG:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    title_font = {'fontsize': 14, 'fontweight': 'bold'}
    item_font = {'fontsize': 10}
    
    for cat, items in categories.items():
        ax.text(0.05, y_pos, f"{cat.upper()}:", transform=ax.transAxes, **title_font, color='#2c3e50')
        y_pos -= 0.05
        
        for item in items:
            line = f"• {item['name']} — ${item['price']} ({item['rating']})"
            ax.text(0.1, y_pos, line, transform=ax.transAxes, **item_font, color='#34495e')
            y_pos -= 0.04
            
        y_pos -= 0.02
        
    plt.tight_layout()
    filename = "catalog.png"
    plt.savefig(filename, dpi=150)
    plt.close()
    return filename

async def send_progress(bot, chat_id, message_id, text):
    try:
        await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id)
    except:
        pass

# --- ОБРАБОТЧИКИ AIOPGRAM ---

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    get_user_state(user_id)
    
    caption = (
        "👋 Привет! Я умный помощник по магазину.\n\n"
        "Ищу товары, сравниваю плюсы/минусы и добавляю в корзину.\n"
        "✍️ Примеры запросов:\n"
        "_\"Найди лучшие наушники до 200$\"_\n"
        "_\"Мне нужна самая дешевая клавиатура\"_\n"
        "_\"Добавь в корзину лучшую мышь\"_"
    )
    
    photo_path = generate_catalog_image()
    photo = FSInputFile(photo_path)
    
    await message.answer_photo(photo, caption=caption, parse_mode="Markdown")

@dp.message(Command("cart"))
async def cmd_cart(message: types.Message):
    user_id = message.from_user.id
    state = get_user_state(user_id)
    cart = state["cart"]
    
    if not cart:
        await message.answer("🛒 Ваша корзина пуста.")
        return
    
    total = 0
    text = "🛒 **Ваша корзина:**\n\n"
    for item in cart:
        text += f"• {item['name']} x{item['quantity']} — ${item['price'] * item['quantity']}\n"
        total += item['price'] * item['quantity']
    
    text += f"\n💰 **Итого:** ${total}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")]
    ])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "clear_cart")
async def cb_clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    state["cart"] = []
    await callback.message.edit_text("🗑 Корзина очищена.")

@dp.callback_query(F.data.startswith("add_"))
async def cb_add_to_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    candidate = state.get("current_candidate")
    
    if not candidate:
        await callback.answer("Ошибка: товар не найден.", show_alert=True)
        return
    
    existing = next((i for i in state["cart"] if i["id"] == candidate["id"]), None)
    if existing:
        existing["quantity"] += 1
    else:
        state["cart"].append({
            "id": candidate["id"],
            "name": candidate["name"],
            "price": candidate["price"],
            "quantity": 1
        })
    
    await callback.answer(f"✅ {candidate['name']} добавлен!")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Посмотреть корзину", callback_data="view_cart_btn")]
    ])
    await callback.message.answer("Товар добавлен!", reply_markup=keyboard)

@dp.callback_query(F.data == "view_cart_btn")
async def cb_view_cart_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    cart = state["cart"]
    
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    
    total = 0
    text = "🛒 **Ваша корзина:**\n\n"
    for item in cart:
        text += f"• {item['name']} x{item['quantity']} — ${item['price'] * item['quantity']}\n"
        total += item['price'] * item['quantity']
    text += f"\n💰 **Итого:** ${total}"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")]
    ]))

@dp.callback_query(F.data == "remove_last")
async def cb_remove_last(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    candidate = state.get("current_candidate")
    
    if not candidate or not state["cart"]:
        await callback.answer("Нечего удалять.", show_alert=True)
        return
    
    # Удаляем последний добавленный товар с таким ID
    # В простой реализации удаляем просто последний элемент, если он совпадает, или ищем по ID
    # Для простоты: удаляем одну единицу последнего добавленного товара этого типа
    found = False
    for i in range(len(state["cart"]) - 1, -1, -1):
        if state["cart"][i]["id"] == candidate["id"]:
            if state["cart"][i]["quantity"] > 1:
                state["cart"][i]["quantity"] -= 1
            else:
                state["cart"].pop(i)
            found = True
            break
    
    if found:
        await callback.answer("🗑 Товар удален из корзины.")
        # Обновляем сообщение кнопки, если нужно, или просто оставляем алерт
    else:
        await callback.answer("Товара нет в корзине.", show_alert=True)

@dp.callback_query(F.data == "retry_search")
async def cb_retry(callback: types.CallbackQuery):
    await callback.message.delete()

@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    state = get_user_state(user_id)
    
    progress_msg = await message.answer("🔍 Ищу товары...")
    
    try:
        await asyncio.sleep(0.5)
        await send_progress(bot, message.chat.id, progress_msg.message_id, "🧐 Анализирую...")
        
        response_text, best_product, auto_added = CoordinatorAgent().run(user_text, state)
        
        await asyncio.sleep(0.5)
        await send_progress(bot, message.chat.id, progress_msg.message_id, "⚖️ Готово!")
        
        await progress_msg.delete()
        
        if best_product:
            if auto_added:
                # Кнопка только для удаления
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🗑 Убрать из корзины", callback_data="remove_last")],
                    [InlineKeyboardButton(text="🛒 Моя корзина", callback_data="view_cart_btn")]
                ])
            else:
                # Кнопки для добавления или отказа
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Подходит (В корзину)", callback_data="add_to_cart"),
                        InlineKeyboardButton(text="❌ Не подходит", callback_data="retry_search")
                    ],
                    [
                        InlineKeyboardButton(text="🛒 Моя корзина", callback_data="view_cart_btn")
                    ]
                ])
            await message.answer(response_text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await message.answer(response_text)
            
    except Exception as e:
        logger.error(f"Critical error in handle_text: {e}", exc_info=True)
        await progress_msg.delete()
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
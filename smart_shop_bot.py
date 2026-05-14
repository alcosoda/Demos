import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Telegram & AI libs
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
import matplotlib.pyplot as plt

# --- Load Env Variables ---
load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
YANDEX_CLOUD_MODEL = os.getenv("YANDEX_CLOUD_MODEL")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([YANDEX_CLOUD_FOLDER, YANDEX_CLOUD_API_KEY, YANDEX_CLOUD_MODEL, BOT_TOKEN]):
    raise ValueError("Missing environment variables. Check your .env file or GitHub Secrets.")

# --- Configuration ---
MODEL_NAME = f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}"
llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    temperature=0.3
)

# --- Catalog Data ---
CATALOG = [
    {"id": "p1",  "name": "Sony WH-1000XM5",            "category": "headphones", "brand": "Sony",     "price": 349, "color": "black",    "rating": 4.8, "tags": ["wireless", "noise-cancelling", "premium"]},
    {"id": "p2",  "name": "Sony WH-CH720N",              "category": "headphones", "brand": "Sony",     "price": 129, "color": "blue",     "rating": 4.4, "tags": ["wireless", "budget", "noise-cancelling"]},
    {"id": "p3",  "name": "Bose QuietComfort Ultra",     "category": "headphones", "brand": "Bose",     "price": 379, "color": "white",    "rating": 4.7, "tags": ["wireless", "noise-cancelling", "premium"]},
    {"id": "p4",  "name": "Apple AirPods Pro 2",         "category": "earbuds",    "brand": "Apple",    "price": 249, "color": "white",    "rating": 4.6, "tags": ["wireless", "noise-cancelling", "ios"]},
    {"id": "p5",  "name": "Anker Soundcore Liberty 4 NC","category": "earbuds",    "brand": "Anker",    "price": 99,  "color": "black",    "rating": 4.3, "tags": ["wireless", "budget", "noise-cancelling"]},
    {"id": "p6",  "name": "Logitech MX Master 3S",       "category": "mouse",      "brand": "Logitech", "price": 109, "color": "graphite", "rating": 4.8, "tags": ["wireless", "productivity", "premium"]},
    {"id": "p7",  "name": "Logitech Pebble 2",           "category": "mouse",      "brand": "Logitech", "price": 34,  "color": "white",    "rating": 4.2, "tags": ["wireless", "budget", "portable"]},
    {"id": "p8",  "name": "Keychron K2",                 "category": "keyboard",   "brand": "Keychron", "price": 89,  "color": "black",    "rating": 4.5, "tags": ["wireless", "mechanical", "compact"]},
    {"id": "p9",  "name": "NuPhy Air75",                 "category": "keyboard",   "brand": "NuPhy",    "price": 139, "color": "gray",     "rating": 4.6, "tags": ["wireless", "mechanical", "low-profile"]},
    {"id": "p10", "name": "Amazon Kindle Paperwhite",    "category": "ereader",    "brand": "Amazon",   "price": 149, "color": "black",    "rating": 4.7, "tags": ["reading", "portable", "gift"]},
]

# --- Shop Logic Tools ---
class ShopTools:
    def __init__(self, catalog):
        self.catalog = catalog

    def search_products(self, query: str = "", category: str | None = None,
                        brand: str | None = None, max_price: float | None = None,
                        sort_by: str | None = None) -> list:
        results = []
        q_words = query.lower().split() if query else []
        for item in self.catalog:
            hay = f"{item['name']} {item['category']} {item['brand']} {' '.join(item['tags'])}".lower()
            if q_words and not all(w in hay for w in q_words): continue
            if category and item["category"] != category: continue
            if brand and item["brand"].lower() != brand.lower(): continue
            if max_price is not None and item["price"] > float(max_price): continue
            results.append(item.copy())
        if sort_by == "price_asc": results.sort(key=lambda x: x["price"])
        elif sort_by == "rating_desc": results.sort(key=lambda x: -x["rating"])
        return results

    def add_to_cart(self, cart: list, product_id: str, quantity: int = 1) -> dict:
        product = next((p for p in self.catalog if p["id"] == product_id), None)
        if not product:
            return {"ok": False, "error": f"Product {product_id} not found"}
        existing = next((r for r in cart if r["product_id"] == product_id), None)
        if existing:
            existing["quantity"] += quantity
        else:
            cart.append({"product_id": product_id, "name": product["name"],
                         "price": product["price"], "quantity": quantity})
        return {"ok": True, "cart_size": len(cart)}

TOOLS = ShopTools(CATALOG)

def search_products(query: str = "", category: str | None = None, brand: str | None = None, max_price: float | None = None, sort_by: str | None = None) -> list:
    """
    Search for products in the catalog.
    Args:
        query: Text search query (e.g., 'wireless headphones').
        category: Product category (e.g., 'mouse', 'keyboard').
        brand: Brand name (e.g., 'Sony', 'Logitech').
        max_price: Maximum price limit.
        sort_by: Sorting option ('price_asc', 'rating_desc').
    Returns: List of matching products.
    """
    return TOOLS.search_products(query=query, category=category, brand=brand, max_price=max_price, sort_by=sort_by)

def add_to_cart(product_id: str, quantity: int = 1) -> dict:
    """
    Add a product to the shopping cart by its ID.
    Args:
        product_id: The ID of the product to add (e.g., 'p1').
        quantity: Number of items to add.
    Returns: Status of the operation.
    """
    # Заглушка, реальная логика будет в боте с передачей состояния корзины
    return {"ok": False, "error": "Use ShopTools.add_to_cart with state"}

SHOP_TOOLS_SCHEMA = [
    convert_to_openai_tool(search_products),
    convert_to_openai_tool(add_to_cart),
]

# --- Multi-Agent System Classes ---

@dataclass
class AgentContext:
    query: str
    max_price: float | None = None
    candidates: list[dict] = field(default_factory=list)
    pros: dict[str, str] = field(default_factory=dict)
    cons: dict[str, str] = field(default_factory=dict)
    best: dict | None = None
    cart_result: dict | None = None

class ToolTracer:
    def __init__(self):
        self.calls = []
    def record(self, name, args, result=None):
        self.calls.append({"name": name, "args": args, "result": result})

def llm_chat(messages: list, tools: list | None = None) -> AIMessage:
    if tools:
        return llm.bind_tools(tools).invoke(messages)
    return llm.invoke(messages)

class RetrieverAgent:
    def run(self, ctx: AgentContext, tools: ShopTools, tracer: ToolTracer) -> AgentContext:
        sys_msg = SystemMessage(content="You are a product search assistant. Find up to 5 relevant products. Extract max_price if mentioned.")
        user_msg = HumanMessage(content=ctx.query)
        history = [sys_msg, user_msg]
        ai_msg = llm_chat(history, [convert_to_openai_tool(search_products)])
        ctx.max_price = None
        for call in getattr(ai_msg, "tool_calls", []):
            if call["name"] == "search_products":
                result = tools.search_products(**call["args"])
                tracer.record("search_products", call["args"], result)
                max_price = call["args"].get("max_price")
                if max_price is not None:
                    try:
                        max_price = float(max_price)
                        result = [p for p in result if p["price"] <= max_price]
                        ctx.max_price = max_price
                    except Exception: pass
                ctx.candidates = result[:5]
        return ctx

class ProsAgent:
    def run(self, ctx: AgentContext, tracer: ToolTracer) -> AgentContext:
        ctx.pros = {}
        for prod in ctx.candidates:
            sys_msg = SystemMessage(content="List 1 sentence of main pros for this product.")
            user_msg = HumanMessage(content=json.dumps(prod, ensure_ascii=False))
            ai_msg = llm_chat([sys_msg, user_msg])
            ctx.pros[prod["id"]] = ai_msg.content
            tracer.record("analyze_pros", {"product_id": prod["id"]}, ai_msg.content)
        return ctx

class ConsAgent:
    def run(self, ctx: AgentContext, tracer: ToolTracer) -> AgentContext:
        ctx.cons = {}
        for prod in ctx.candidates:
            sys_msg = SystemMessage(content="List 1 sentence of main cons for this product.")
            user_msg = HumanMessage(content=json.dumps(prod, ensure_ascii=False))
            ai_msg = llm_chat([sys_msg, user_msg])
            ctx.cons[prod["id"]] = ai_msg.content
            tracer.record("analyze_cons", {"product_id": prod["id"]}, ai_msg.content)
        return ctx

class RankerAgent:
    def run(self, ctx: AgentContext, tracer: ToolTracer) -> AgentContext:
        candidates = ctx.candidates
        if ctx.max_price is not None:
            candidates = [p for p in candidates if p["price"] <= ctx.max_price]
        if not candidates:
            ctx.best = None
            return ctx
        
        # Определяем критерий сортировки на основе запроса пользователя
        query_lower = ctx.query.lower()
        
        # Сортировка по цене (возрастание) - для запросов типа "самый дешевый", "недорогой"
        if any(word in query_lower for word in ["дешев", "недорог", "бюджет", "минимал", "lowest", "cheapest"]):
            candidates = sorted(candidates, key=lambda x: (x["price"], -x["rating"]))
        # Сортировка по рейтингу (убывание) - для запросов типа "лучший", "топ", "highest rated"
        elif any(word in query_lower for word in ["лучш", "топ", "best", "top", "rating", "рейтинг"]):
            candidates = sorted(candidates, key=lambda x: (-x["rating"], x["price"]))
        # По умолчанию - баланс цены и рейтинга
        else:
            candidates = sorted(candidates, key=lambda x: (-x["rating"], x["price"]))
        
        ctx.best = candidates[0]
        tracer.record("rank_candidates", {"candidates": [p["id"] for p in candidates], "sort_criteria": "price" if "дешев" in query_lower else "rating"}, ctx.best)
        return ctx

class CoordinatorAgent:
    def __init__(self):
        self.retriever = RetrieverAgent()
        self.pros_agent = ProsAgent()
        self.cons_agent = ConsAgent()
        self.ranker = RankerAgent()

    def run(self, user_message: str, tools: ShopTools) -> AgentContext:
        ctx = AgentContext(query=user_message)
        tracer = ToolTracer()
        
        ctx = self.retriever.run(ctx, tools, tracer)
        if not ctx.candidates:
            return ctx
            
        ctx = self.pros_agent.run(ctx, tracer)
        ctx = self.cons_agent.run(ctx, tracer)
        ctx = self.ranker.run(ctx, tracer)
        
        return ctx

# --- Helper Functions ---

def create_catalog_image():
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis('off')
    
    y_pos = 0.95
    categories = {}
    for item in CATALOG:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    for cat, items in categories.items():
        ax.text(0.05, y_pos, f"{cat.upper()}:", fontsize=12, fontweight='bold', va='top')
        y_pos -= 0.05
        for item in items:
            line = f"• {item['name']} — ${item['price']} (⭐{item['rating']})"
            ax.text(0.1, y_pos, line, fontsize=10, va='top', family='monospace')
            y_pos -= 0.04
        y_pos -= 0.02
        
    plt.tight_layout()
    filename = "catalog.png"
    plt.savefig(filename)
    plt.close()
    return filename

# --- Bot States ---
class ShopStates(StatesGroup):
    waiting_for_choice = State()

# --- Bot Handlers ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# In-memory storage for demo (in prod use Redis/DB)
user_carts = {} 
user_contexts = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []
    
    catalog_file = create_catalog_image()
    await message.answer_photo(
        photo=types.FSInputFile(catalog_file),
        caption="👋 Привет! Это Smart Shop Bot.\n\nВот наш ассортимент. Напиши мне, что ты ищешь, например:\n'Мне нужны лучшие наушники до 260$'\n'Найди беспроводную мышь и добавь в корзину'"
    )
    if os.path.exists(catalog_file):
        os.remove(catalog_file)


@dp.message(~CommandStart())
async def handle_user_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_query = message.text
    
    # Если пользователь в состоянии ожидания выбора и отправляет текст - игнорируем (т.к. кнопки убраны)
    current_state = await state.get_state()
    if current_state == ShopStates.waiting_for_choice:
        return
    
    # Send progress messages
    progress_msg = await message.answer("🔍 Ищу подходящие товары...")
    
    try:
        # Run Multi-Agent System
        coordinator = CoordinatorAgent()
        ctx = coordinator.run(user_query, TOOLS)
        
        await progress_msg.edit_text("🧐 Анализирую плюсы и минусы...")
        await asyncio.sleep(0.5) # Just for effect
        
        if not ctx.best:
            await progress_msg.edit_text("😕 К сожалению, я не нашел подходящих товаров по вашему запросу.")
            return

        best = ctx.best
        pid = best['id']
        
        # Format response
        response_text = (
            f"🏆 <b>Лучший вариант:</b>\n"
            f"<b>{best['name']}</b>\n"
            f"💰 Цена: ${best['price']}\n"
            f"⭐ Рейтинг: {best['rating']}\n\n"
            f"➕ <b>Плюсы:</b>\n<i>{ctx.pros.get(pid, 'Нет данных')}</i>\n\n"
            f"➖ <b>Минусы:</b>\n<i>{ctx.cons.get(pid, 'Нет данных')}</i>"
        )
        
        # Save context for button handler
        await state.update_data(best_product=best)
        await state.set_state(ShopStates.waiting_for_choice)
        
        # Create keyboard
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data="accept")]
        ])
        
        await progress_msg.edit_text(response_text, parse_mode="HTML", reply_markup=kb)
        
        # Store context specifically for callback
        user_contexts[user_id] = {"best_product": best, "state": "waiting_choice"}

    except Exception as e:
        logging.error(e)
        await progress_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")

@dp.callback_query(F.data == "accept")
async def process_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer()
    
    context = user_contexts.get(user_id)
    if not context:
        await callback.message.answer("Сессия истекла. Пожалуйста, начните заново.")
        return

    best_product = context.get("best_product")
    
    if best_product:
        cart = user_carts.get(user_id, [])
        result = TOOLS.add_to_cart(cart, best_product['id'], 1)
        user_carts[user_id] = cart
        if result['ok']:
            # Keyboard with View Cart button
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Посмотреть корзину", callback_data="view_cart")]
            ])
            await callback.message.answer(f"✅ Товар '{best_product['name']}' добавлен в корзину!", reply_markup=kb)
        else:
            await callback.message.answer("❌ Ошибка при добавлении.", reply_markup=None)
    else:
        await callback.message.answer("❌ Ошибка: товар не найден.", reply_markup=None)
    
    user_contexts[user_id] = None
    await state.clear()

@dp.callback_query(F.data == "view_cart")
async def process_view_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer()
    await show_cart(callback.message, user_id)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []
    
    catalog_file = create_catalog_image()
    await message.answer_photo(
        photo=types.FSInputFile(catalog_file),
        caption="👋 Привет! Это Smart Shop Bot.\n\nВот наш ассортимент. Напиши мне, что ты ищешь, например:\n'Мне нужны лучшие наушники до 260$'\n'Найди беспроводную мышь и добавь в корзину'\n\nИспользуй команду /cart, чтобы посмотреть корзину."
    )
    if os.path.exists(catalog_file):
        os.remove(catalog_file)

@dp.message(Command("cart"))
async def cmd_cart(message: types.Message):
    user_id = message.from_user.id
    await show_cart(message, user_id)

async def show_cart(message: types.Message, user_id: int):
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("🛒 Ваша корзина пуста.")
        return
    
    total = 0
    items_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for item in cart:
        item_total = item['price'] * item['quantity']
        total += item_total
        items_text += f"• {item['name']} x{item['quantity']} — ${item_total}\n"
    
    items_text += f"\n<b>Итого: ${total}</b>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="clear_cart")]
    ])
    
    await message.answer(items_text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []
    await callback.answer("Корзина очищена!")
    await callback.message.edit_text("🛒 Корзина очищена.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile  # Импортируем правильный тип
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Не найден токен бота. Установите переменную окружения BOT_TOKEN.")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_city_coords(city_name):
    try:
        geolocator = Nominatim(user_agent="my_shop_demo_bot")
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        logging.error(f"Ошибка геокодирования: {e}")
        return None, None

def create_map(lat, lon, city_name):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    
    ax.add_feature(cfeature.LAND, color='#f5f5dc')
    ax.add_feature(cfeature.OCEAN, color='#aaddff')
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    
    ax.plot(lon, lat, 'ro', markersize=10, transform=ccrs.PlateCarree())
    ax.set_title(f"Город: {city_name}")
    
    # Центрируем карту на городе
    ax.set_extent([lon - 5, lon + 5, lat - 5, lat + 5], crs=ccrs.PlateCarree())
    
    filename = "city_map.png"
    plt.savefig(filename)
    plt.close()
    return filename

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Отправь мне название города на английском, и я пришлю карту с этим местом.")

@dp.message()
async def handle_city(message: types.Message):
    city_name = message.text
    await message.answer(f"Ищу город: {city_name}...")
    
    lat, lon = get_city_coords(city_name)
    
    if lat and lon:
        map_file = create_map(lat, lon, city_name)
        # Используем FSInputFile для корректной отправки
        photo = FSInputFile(map_file)
        await message.answer_photo(photo, caption=f"Вот карта города {city_name}")
        
        # Удаляем файл после отправки
        if os.path.exists(map_file):
            os.remove(map_file)
    else:
        await message.answer(f"Не удалось найти город '{city_name}'. Попробуй написать название на английском правильно.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
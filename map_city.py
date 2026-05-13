import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from geopy.geocoders import Nominatim

def get_city_location(city_name):
    locator = Nominatim(user_agent="my_geocoder")
    try:
        location = locator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None, None

def plot_city(city_name, lat, lon):
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Добавляем карту мира
    ax.stock_img()
    
    # Рисуем точку города
    ax.plot(lon, lat, 'ro', markersize=15, transform=ccrs.Geodetic(), label=city_name)
    
    # Добавляем подпись
    plt.title(f"Город: {city_name}")
    plt.legend()
    
    # Сохраняем в файл вместо показа окна
    output_file = "map.png"
    plt.savefig(output_file)
    print(f"Карта сохранена в файл: {output_file}")
    print("Открой этот файл в панели файлов слева (в VS Code), чтобы увидеть результат.")

if __name__ == "__main__":
    city = input("Введите название города на английском (например, London): ")
    lat, lon = get_city_location(city)
    
    if lat and lon:
        print(f"Координаты найдены: Широта {lat}, Долгота {lon}")
        plot_city(city, lat, lon)
    else:
        print("Город не найден. Проверьте правильность написания.")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from geopy.geocoders import Nominatim

def get_city_coordinates(city_name):
    """Получает координаты города по названию."""
    geolocator = Nominatim(user_agent="city_mapper")
    try:
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Ошибка при поиске города: {e}")
        return None, None

def plot_city_on_map(lat, lon, city_name):
    """Рисует карту мира с точкой города."""
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    
    # Добавляем границы стран и океаны
    ax.stock_img()
    
    # Рисуем точку города
    ax.plot(lon, lat, marker='o', color='red', markersize=15, transform=ccrs.PlateCarree(), label=city_name)
    
    # Добавляем легенду и заголовок
    ax.legend(loc='upper left')
    plt.title(f"Город: {city_name}\nКоординаты: {lat:.4f}, {lon:.4f}")
    
    plt.show()

if __name__ == "__main__":
    city = input("Введите название города на английском: ")
    lat, lon = get_city_coordinates(city)
    
    if lat is not None and lon is not None:
        print(f"Найден город: {city} ({lat}, {lon})")
        plot_city_on_map(lat, lon, city)
    else:
        print(f"Город '{city}' не найден. Проверьте правильность названия.")

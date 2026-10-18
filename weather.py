"""Погода и геопозиция. Геопозиция — через Windows (Geolocator, спросит разрешение Windows).
Если она недоступна — город из настроек. Погода — Open-Meteo (без ключа, нужен интернет)."""
import re
import requests

from winctl import _WINRT, ps

WMO = {0: "ясно", 1: "в основном ясно", 2: "переменная облачность", 3: "пасмурно", 45: "туман",
       48: "изморозь", 51: "лёгкая морось", 53: "морось", 55: "сильная морось", 61: "небольшой дождь",
       63: "дождь", 65: "сильный дождь", 71: "небольшой снег", 73: "снег", 75: "сильный снег",
       77: "снежная крупа", 80: "ливень", 81: "ливень", 82: "сильный ливень", 85: "снегопад",
       86: "сильный снегопад", 95: "гроза", 96: "гроза с градом", 99: "сильная гроза"}

_GEO = _WINRT + r"""
$null=[Windows.Devices.Geolocation.Geolocator,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
$g=New-Object Windows.Devices.Geolocation.Geolocator
$p=Await ($g.GetGeopositionAsync()) ([Windows.Devices.Geolocation.Geoposition])
Write-Output ("POS={0};{1}" -f $p.Coordinate.Point.Position.Latitude,$p.Coordinate.Point.Position.Longitude)
"""


def windows_location():
    """(lat, lon) или (None, причина). Windows сама покажет запрос доступа к местоположению."""
    ok, out = ps(_GEO, timeout=25)
    m = re.search(r"POS=(-?\d+[.,]?\d*);(-?\d+[.,]?\d*)", out)
    if not ok or not m:
        return None, "Windows не отдала местоположение (выключена геолокация или нет разрешения)"
    return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))


def geocode(city):
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1, "language": "ru", "format": "json"}, timeout=10)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return None
    x = res[0]
    return x["latitude"], x["longitude"], x.get("name", city)


def forecast(lat, lon, place=""):
    r = requests.get("https://api.open-meteo.com/v1/forecast",
                     params={"latitude": lat, "longitude": lon, "timezone": "auto",
                             "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m"},
                     timeout=10)
    r.raise_for_status()
    c = r.json()["current"]
    desc = WMO.get(int(c.get("weather_code", 0)), "")
    where = f" в {place}" if place else ""
    return (f"Сейчас{where} {c['temperature_2m']:+.0f}°C (ощущается как {c['apparent_temperature']:+.0f}°C), "
            f"{desc}, ветер {c['wind_speed_10m']:.0f} км/ч.").replace("+-", "-")


# Координаты крупных городов: работают без интернета у поиска города. Можно ввести и координаты «55.75,37.62».
CITIES = {
    "москва": (55.7558, 37.6173), "санкт-петербург": (59.9343, 30.3351), "питер": (59.9343, 30.3351),
    "новосибирск": (55.0084, 82.9357), "екатеринбург": (56.8389, 60.6057), "казань": (55.7887, 49.1221),
    "нижний новгород": (56.2965, 43.9361), "челябинск": (55.1644, 61.4368), "самара": (53.1959, 50.1002),
    "омск": (54.9885, 73.3242), "ростов-на-дону": (47.2357, 39.7015), "ростов": (47.2357, 39.7015),
    "уфа": (54.7388, 55.9721), "красноярск": (56.0153, 92.8932), "воронеж": (51.6720, 39.1843),
    "пермь": (58.0105, 56.2502), "волгоград": (48.7080, 44.5133), "краснодар": (45.0355, 38.9753),
    "саратов": (51.5331, 46.0342), "тюмень": (57.1530, 65.5343), "тольятти": (53.5303, 49.3461),
    "ижевск": (56.8498, 53.2045), "барнаул": (53.3478, 83.7798), "иркутск": (52.2870, 104.3050),
    "владивосток": (43.1155, 131.8855), "хабаровск": (48.4802, 135.0719), "калининград": (54.7104, 20.4522),
    "сочи": (43.5855, 39.7231), "минск": (53.9045, 27.5615),
}

def _coords_for_city(text):
    """(lat, lon, название) из таблицы городов или из строки «lat,lon»; иначе None."""
    t = text.strip().lower().replace("ё", "е")
    m = re.fullmatch(r"(-?\d+(?:[.,]\d+)?)\s*,\s*(-?\d+(?:[.,]\d+)?)", t)
    if m:
        return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", ".")), text.strip()
    if t in CITIES:
        lat, lon = CITIES[t]
        return lat, lon, text.strip().title()
    return None


def get_weather(cfg, use_windows=True):
    """Текст погоды или (None, причина). Геолокация Windows — если разрешена; иначе город из настроек."""
    lat = lon = None
    place = cfg.get("city", "").strip()
    if use_windows and cfg.get("loc_consent"):
        la, lo_or_err = windows_location()
        if la is not None:
            lat, lon, place = la, lo_or_err, ""
    if lat is None:
        if not place:
            return None, "нет геопозиции и не указан город (укажи его в ⚙ Настройки → Умное)"
        found = _coords_for_city(place)
        if found is None:
            try:
                g = geocode(place)
            except requests.RequestException:
                g = None
            if not g:
                return None, (f"не знаю координаты «{place}» — введи город из списка или координаты вида 55.75,37.62")
            found = g
        lat, lon, place = found
    try:
        return forecast(lat, lon, place), ""
    except requests.RequestException as e:
        return None, f"нет связи с сервисом погоды: {e.__class__.__name__}: {str(e)[:150]}"
    except (ValueError, KeyError) as e:
        return None, f"сервис погоды ответил ошибкой: {e}"

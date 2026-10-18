"""Знания о Windows: где находится настройка и открыть её, какая версия и сборка установлена.
Адреса настроек — из официального справочника Microsoft «Launch Windows Settings» (ms-settings:).
Версии и сборки — со страницы Microsoft «Windows 11 release information». Что нового — только проверенные записи."""
import os, re

SOURCE_SETTINGS = "справочник Microsoft: Launch Windows Settings (ms-settings:)"

# (ключевые слова, название, путь в интерфейсе Windows 11, адрес ms-settings:)
SETTINGS = [
    (["wifi", "вай фай", "вайфай", "wi-fi", "сеть", "интернет"], "Wi-Fi", "Сеть и Интернет → Wi-Fi", "ms-settings:network-wifi"),
    (["сетевые настройки", "сеть и интернет", "network"], "Сеть и Интернет", "Сеть и Интернет", "ms-settings:network-status"),
    (["ethernet", "кабель", "проводное подключение"], "Ethernet", "Сеть и Интернет → Ethernet", "ms-settings:network-ethernet"),
    (["vpn", "впн"], "VPN", "Сеть и Интернет → VPN", "ms-settings:network-vpn"),
    (["прокси", "proxy"], "Прокси", "Сеть и Интернет → Прокси", "ms-settings:network-proxy"),
    (["хотспот", "точка доступа", "мобильный хот-спот", "раздача интернета"], "Мобильный хот-спот", "Сеть и Интернет → Мобильный хот-спот", "ms-settings:network-mobilehotspot"),
    (["режим полёта", "режим полета", "самолет", "авиарежим"], "Режим полёта", "Сеть и Интернет → Режим «в самолёте»", "ms-settings:network-airplanemode"),
    (["bluetooth", "блютуз", "блютус"], "Bluetooth", "Bluetooth и устройства", "ms-settings:bluetooth"),
    (["принтер", "принтеры", "сканер"], "Принтеры и сканеры", "Bluetooth и устройства → Принтеры и сканеры", "ms-settings:printers"),
    (["мышь", "мышка", "тачпад", "touchpad"], "Мышь и сенсорная панель", "Bluetooth и устройства → Мышь", "ms-settings:mousetouchpad"),
    (["usb", "юсб"], "USB", "Bluetooth и устройства → USB", "ms-settings:usb"),
    (["камера", "вебкамера", "веб-камера"], "Камера", "Bluetooth и устройства → Камера", "ms-settings:camera"),
    (["звук", "громкость", "динамики", "наушники"], "Звук", "Система → Звук", "ms-settings:sound"),
    (["устройства вывода звука", "выход звука", "динамики устройство"], "Устройства вывода звука", "Система → Звук → Устройства вывода", "ms-settings:sound-defaultoutputproperties"),
    (["экран", "дисплей", "разрешение", "масштаб", "монитор", "display"], "Экран", "Система → Экран", "ms-settings:display"),
    (["ночной свет", "ночной режим"], "Ночной свет", "Система → Экран → Ночной свет", "ms-settings:nightlight"),
    (["уведомления", "notifications"], "Уведомления", "Система → Уведомления", "ms-settings:notifications"),
    (["не беспокоить", "фокусировка", "фокус", "тихие часы"], "Фокусировка (не беспокоить)", "Система → Фокусировка", "ms-settings:quiethours"),
    (["питание", "сон", "спящий режим", "экран выключается"], "Питание и сон", "Система → Питание и батарея", "ms-settings:powersleep"),
    (["батарея", "заряд", "экономия энергии", "экономия заряда"], "Экономия заряда", "Система → Питание и батарея → Экономия заряда", "ms-settings:batterysaver"),
    (["хранилище", "место на диске", "память диска", "очистка диска", "контроль памяти"], "Хранилище", "Система → Память", "ms-settings:storagesense"),
    (["буфер обмена", "буфер", "история буфера"], "Буфер обмена", "Система → Буфер обмена", "ms-settings:clipboard"),
    (["многозадачность", "окна рабочие столы", "виртуальные рабочие столы"], "Многозадачность", "Система → Многозадачность", "ms-settings:multitasking"),
    (["о системе", "характеристики", "версия windows", "сборка", "about"], "О системе", "Система → О системе", "ms-settings:about"),
    (["восстановление", "сброс windows", "вернуть компьютер"], "Восстановление", "Система → Восстановление", "ms-settings:recovery"),
    (["активация", "активировать windows", "ключ продукта"], "Активация", "Система → Активация", "ms-settings:activation"),
    (["для разработчиков", "разработчики"], "Для разработчиков", "Система → Для разработчиков", "ms-settings:developers"),
    (["персонализация", "оформление", "фон", "обои"], "Персонализация", "Персонализация", "ms-settings:personalization"),
    (["тема", "тему", "темы", "темная тема", "тёмная тема", "темную", "тёмную", "светлая тема", "светлую", "цвета", "акцентный цвет"], "Цвета", "Персонализация → Цвета", "ms-settings:colors"),
    (["пуск", "меню пуск", "start"], "Меню «Пуск»", "Персонализация → Пуск", "ms-settings:personalization-start"),
    (["панель задач", "таскбар", "taskbar"], "Панель задач", "Персонализация → Панель задач", "ms-settings:taskbar"),
    (["экран блокировки", "блокировка", "lock screen"], "Экран блокировки", "Персонализация → Экран блокировки", "ms-settings:lockscreen"),
    (["шрифты", "шрифт"], "Шрифты", "Персонализация → Шрифты", "ms-settings:fonts"),
    (["приложения по умолчанию", "программы по умолчанию", "браузер по умолчанию"], "Приложения по умолчанию", "Приложения → Приложения по умолчанию", "ms-settings:defaultapps"),
    (["установленные приложения", "удалить программу", "удалить приложение", "программы и компоненты"], "Установленные приложения", "Приложения → Установленные приложения", "ms-settings:appsfeatures"),
    (["автозапуск", "запуск при старте", "автозагрузка"], "Автозапуск приложений", "Приложения → Автозапуск", "ms-settings:startupapps"),
    (["дополнительные компоненты", "компоненты windows", "включить компонент"], "Дополнительные компоненты", "Приложения → Дополнительные компоненты", "ms-settings:optionalfeatures"),
    (["учётные записи", "учетные записи", "аккаунт", "аккаунты"], "Учётные записи", "Учётные записи", "ms-settings:yourinfo"),
    (["вход", "пароль", "пин", "pin", "windows hello", "отпечаток"], "Параметры входа", "Учётные записи → Параметры входа", "ms-settings:signinoptions"),
    (["дата", "время", "часовой пояс", "дата и время"], "Дата и время", "Время и язык → Дата и время", "ms-settings:dateandtime"),
    (["язык", "раскладка", "клавиатура", "языки"], "Язык и клавиатура", "Время и язык → Язык и регион", "ms-settings:regionlanguage"),
    (["специальные возможности", "лупа", "высокая контрастность", "контраст"], "Специальные возможности", "Специальные возможности", "ms-settings:easeofaccess"),
    (["экранная клавиатура"], "Экранная клавиатура", "Специальные возможности → Клавиатура", "ms-settings:easeofaccess-keyboard"),
    (["конфиденциальность", "приватность", "privacy"], "Конфиденциальность", "Конфиденциальность и безопасность", "ms-settings:privacy"),
    (["геолокация", "местоположение", "локация"], "Геолокация", "Конфиденциальность и безопасность → Расположение", "ms-settings:privacy-location"),
    (["защитник", "безопасность windows", "антивирус", "брандмауэр"], "Безопасность Windows", "Конфиденциальность и безопасность → Безопасность Windows", "ms-settings:windowsdefender"),
    (["обновление", "обновления", "центр обновления", "windows update"], "Центр обновления Windows", "Центр обновления Windows", "ms-settings:windowsupdate"),
    (["история обновлений", "журнал обновлений"], "История обновлений", "Центр обновления Windows → Журнал обновлений", "ms-settings:windowsupdate-history"),
    (["поиск windows", "поиск в windows", "поиск"], "Поиск Windows", "Конфиденциальность и безопасность → Поиск Windows", "ms-settings:search"),
    (["найти устройство", "поиск устройства"], "Найти устройство", "Найти устройство", "ms-settings:findmydevice"),
]


# Полный справочник страниц «Параметров» (Microsoft). Добавляем то, чего ещё нет в таблице выше.
from windows_settings_full import FULL as _FULL  # noqa: E402

_known = {uri for _, _, _, uri in SETTINGS}
for _uri, _cat, _title, _keys in _FULL:
    if _uri not in _known:
        _known.add(_uri)
        SETTINGS.append((list(_keys) + [_title.lower()], _title, f"{_cat} → {_title}" if _cat else _title, _uri))


def find_setting(query):
    """Лучшая настройка по запросу или None. Совпадение по словам запроса с ключевыми словами."""
    q = query.lower().replace("ё", "е")
    words = re.findall(r"[а-яa-z0-9\-]+", q)
    best, best_score = None, 0
    for keys, title, path, uri in SETTINGS:
        score = 0
        for k in keys:
            if k in q:
                score = max(score, len(k))            # точное вхождение: длинные ключи важнее коротких
            elif " " not in k and len(k) >= 5 and any(x.startswith(k[:5]) for x in words if len(x) >= 5):
                score = max(score, 2)                 # одиночное слово в другой форме: «обновления» → «обновление»
        if score > best_score:
            best, best_score = (title, path, uri), score
    return best


def open_setting(uri):
    try:
        os.startfile(uri)
        return True
    except OSError:
        return False


def current_build():
    """(номер сборки, UBR) текущей Windows, например (26200, 6899). Нет данных — (None, None)."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        build = int(winreg.QueryValueEx(k, "CurrentBuild")[0])
        try:
            ubr = int(winreg.QueryValueEx(k, "UBR")[0])
        except OSError:
            ubr = None
        return build, ubr
    except Exception:
        return None, None


# Версии Windows 11 по основной сборке (Microsoft). 26H1 — отдельная версия Windows 11.
VERSIONS = {22000: "Windows 11 21H2", 22621: "Windows 11 22H2", 22631: "Windows 11 23H2",
            26100: "Windows 11 24H2", 26200: "Windows 11 25H2", 26300: "Windows 11 26H2", 28000: "Windows 11 26H1"}


def version_of(build):
    if build is None:
        return "неизвестно"
    if build in VERSIONS:
        return VERSIONS[build]
    if build >= 22000:
        return f"Windows 11 (сборка {build})"
    return f"Windows 10 (сборка {build})"

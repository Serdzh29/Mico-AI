"""Системные компоненты Windows, которыми может управлять Mico, и системные действия.
Каждый переключатель знает свой способ: реестр, служба, компонент Windows, брандмауэр, Защитник,
страница настроек или программа. Всё, что требует прав администратора, идёт через запрос UAC.
Команды в этом файле задаются разработчиком — пользовательский текст в команду не попадает."""
import difflib
import re, subprocess

import winctl as W

NOWIN = 0x08000000


class Toggle:
    def __init__(self, keys, name, fn=None, page=None, combo=None, proc=None, note="", note_on_only=False,
                 admin=False, get=None, confirm_on="", confirm_off=""):
        self.keys, self.name, self.fn, self.page, self.combo, self.proc = keys, name, fn, page, combo, proc
        self.note, self.note_on_only, self.admin = note, note_on_only, admin
        self.confirm_on, self.confirm_off = confirm_on, confirm_off     # вопрос «да/нет» перед действием
        self.get = get or getattr(fn, "get", None)          # чтение текущего состояния (True/False/None)


class Adjust:
    """Настройка с числом или шкалой: «скорость указателя на 15», «строки прокрутки на 5».
    lo/hi — допустимые пределы, step — шаг при «больше/меньше», unit — подпись (%, мин, стр.).
    set(value) -> (ok, сообщение); get() -> текущее значение или None."""
    def __init__(self, keys, name, set, get, lo, hi, step=1, unit="", labels=None, note=""):
        self.keys, self.name, self.set, self.get = keys, name, set, get
        self.lo, self.hi, self.step, self.unit, self.labels, self.note = lo, hi, step, unit, labels or {}, note

    def label(self, v):
        return self.labels.get(v, f"{v}{' ' + self.unit if self.unit else ''}")


# ---------- способы включения ----------
def reg_toggle(path, name, on_val, off_val, kind="dword", refresh=False, hive="HKCU"):
    def fn(on):
        W.reg_set(path, name, on_val if on else off_val, kind, hive=hive)
        if refresh:
            W.shell_refresh()
        W.broadcast_setting("Policy")
        return True, ""

    def get():
        v = W.reg_get(path, name, None, hive=hive)
        if v is None:
            return None
        if str(v) == str(on_val):
            return True
        if str(v) == str(off_val):
            return False
        return None
    fn.get = get
    return fn


def reg_admin(path, name, on_val, off_val):
    """Реестр HKLM — нужны права администратора."""
    def fn(on):
        v = on_val if on else off_val
        return W.run_elevated(f'reg add "HKLM\\{path}" /v {name} /t REG_DWORD /d {v} /f')
    return fn


def cmd_admin(on_cmd, off_cmd):
    def fn(on):
        return W.run_elevated(on_cmd if on else off_cmd)
    return fn


def shell(on_cmd, off_cmd):
    """Обычная команда без прав администратора (например powercfg). Команды задаёт только разработчик."""
    def fn(on):
        r = subprocess.run(on_cmd if on else off_cmd, shell=True, capture_output=True, creationflags=NOWIN)
        return r.returncode == 0, "" if r.returncode == 0 else "команда не сработала"
    return fn


def ui(page, label, mode="toggle", admin=False):
    """Переключатель или кнопка на странице «Параметров», которые Windows не даёт менять из программы напрямую:
    Mico открывает страницу и сам нажимает нужный элемент через UI Automation."""
    def fn(on):
        if mode == "click":
            return W.ui_setting(page, label, True, mode="click")
        return W.ui_setting(page, label, on, mode=mode)
    return fn


def ui_select(page, choices):
    """Выбор варианта (радиокнопки). choices = {True: 'что выбрать для «включено»', False: '…для «выключено»'}."""
    def fn(on):
        return W.ui_setting(page, choices[bool(on)], True, mode="select")
    return fn


def service(name):
    return lambda on: W.set_service(name, on)


def feature(name):
    return lambda on: W.set_feature(name, on)


def _dnd(on):
    W.reg_set(r"Software\Microsoft\Windows\CurrentVersion\PushNotifications", "ToastEnabled", 0 if on else 1)
    W.broadcast_setting("Policy")
    return True, ""


def _wifi(on):
    return W.radio(["WiFi"], on)


def _bt(on):
    return W.radio(["Bluetooth"], on)


def _mouse_swap(on):
    W.swap_mouse_buttons(on)
    return True, ""


def adapter(kind_filter, media):
    """Включить/выключить физический сетевой адаптер по типу (Ethernet — 802.3, Wi-Fi — Native 802.11)."""
    def fn(on):
        verb = "Enable" if on else "Disable"
        script = (f"Get-NetAdapter -Physical | Where-Object {{ $_.PhysicalMediaType -eq '{media}' }} "
                  f"| {verb}-NetAdapter -Confirm:$false")
        return W.run_elevated(f'powershell -NoProfile -Command "{script}"')
    return fn




ADV = W.EXPLORER_ADV
CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
REG_CLIP = r"Software\Microsoft\Clipboard"

TOGGLES = [
    # ---- связь ----
    Toggle(("wi-fi", "wifi", "wi fi", "вай-фай", "вайфай", "вай фай", "интернет"), "Wi-Fi", _wifi),
    Toggle(("bluetooth", "блютуз", "блютус", "блутуз"), "Bluetooth", _bt),
    Toggle(("режим полет", "режим в самолет", "авиарежим", "в самолет"), "Режим полёта", W.airplane),
    Toggle(("точка доступа", "точку доступа", "хот-спот", "хотспот", "мобильный хот", "раздач"),
           "Мобильный хот-спот", W.hotspot),
    # ---- уведомления и режимы ----
    Toggle(("не беспокоить", "не беспокой"), "Режим «Не беспокоить»", _dnd,
           note="Баннеры уведомлений отключены (напрямую системный DND Windows приложениям не доступен).",
           note_on_only=True),
    Toggle(("уведомлен",), "Уведомления", lambda on: _dnd(not on)),
    Toggle(("эффекты прозрачност", "прозрачност"), "Эффекты прозрачности",
           reg_toggle(W.PERSONALIZE, "EnableTransparency", 1, 0)),
    Toggle(("игровой режим", "режим игры"), "Игровой режим", reg_toggle(r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1, 0)),
    Toggle(("запись игр", "game dvr", "записи игр", "game bar"), "Запись игр (Game DVR)",
           reg_toggle(r"System\GameConfigStore", "GameDVR_Enabled", 1, 0)),
    Toggle(("история буфера", "журнал буфера", "историю буфера"), "История буфера обмена",
           reg_toggle(REG_CLIP, "EnableClipboardHistory", 1, 0)),
    # ---- проводник и папки ----
    Toggle(("скрытые файлы", "скрытые папки", "показ скрытых"), "Показ скрытых файлов",
           reg_toggle(ADV, "Hidden", 1, 2, refresh=True), note="Обнови папку (F5), чтобы увидеть."),
    Toggle(("расширения файлов", "расширения имен", "расширения"), "Показ расширений файлов",
           reg_toggle(ADV, "HideFileExt", 0, 1, refresh=True), note="Обнови папку (F5), чтобы увидеть."),
    Toggle(("анимации окон", "анимации панели", "анимации"), "Анимации Windows",
           reg_toggle(ADV, "TaskbarAnimations", 1, 0, refresh=True)),
    # ---- панель задач ----
    Toggle(("поиск на панели", "строку поиска", "поиск на панели задач"), "Поиск на панели задач",
           reg_toggle(r"Software\Microsoft\Windows\CurrentVersion\Search", "SearchboxTaskbarMode", 2, 0, refresh=True)),
    Toggle(("виджет",), "Виджеты на панели задач", reg_toggle(ADV, "TaskbarDa", 1, 0, refresh=True)),
    Toggle(("чат на панели", "значок чата", "чат windows"), "Чат на панели задач",
           reg_toggle(ADV, "TaskbarMn", 1, 0, refresh=True)),
    Toggle(("представление задач", "просмотр задач", "кнопку задач"), "Кнопка «Представление задач»",
           reg_toggle(ADV, "ShowTaskViewButton", 1, 0, refresh=True)),
    Toggle(("секунды в часах", "секунды на часах", "секунды"), "Секунды в часах",
           reg_toggle(ADV, "ShowSecondsInSystemClock", 1, 0, refresh=True)),
    Toggle(("выравнивание панели", "панель по центру", "панели по центру", "иконки по центру"),
           "Значки панели задач по центру", reg_toggle(ADV, "TaskbarAl", 1, 0, refresh=True)),
    # ---- безопасность ----
    Toggle(("защитник", "защиту в реальном времени", "антивирус"), "Защита Защитника в реальном времени",
           lambda on: W.set_defender_realtime(on), admin=True,
           note="Если не получилось — включена «Защита от подделки» Windows, её нужно выключить вручную."),
    Toggle(("брандмауэр", "фаервол", "firewall"), "Брандмауэр Windows", lambda on: W.set_firewall(on), admin=True),
    # ---- питание ----
    Toggle(("быстрый запуск", "быстрый старт"), "Быстрый запуск",
           reg_admin(r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", 1, 0), admin=True),
    Toggle(("гибернаци", "режим гибернации"), "Режим гибернации",
           cmd_admin("powercfg /hibernate on", "powercfg /hibernate off"), admin=True),
    Toggle(("ночной свет", "ночной режим"), "Ночной свет", page="nightlight"),
    Toggle(("экономия заряда", "экономию заряда", "экономия батаре"), "Экономия заряда", page="batterysaver"),
    # ---- специальные возможности и ввод ----
    Toggle(("кнопки мыши", "левша", "левой рукой"), "Обмен кнопок мыши", _mouse_swap),
    Toggle(("живые субтитры", "живые титры"), "Живые субтитры", combo=("win", "ctrl", "l")),
    Toggle(("лупа", "лупу", "увеличитель"), "Лупа", proc="magnify.exe"),
    Toggle(("экранная клавиатура", "экранную клавиатуру"), "Экранная клавиатура", proc="osk.exe"),
    Toggle(("залипани",), "Залипание клавиш", page="easeofaccess-keyboard"),
    Toggle(("цветовые фильтры", "цветовой фильтр"), "Цветовые фильтры", page="easeofaccess-colorfilter"),
    Toggle(("высокий контраст",), "Высокий контраст", page="easeofaccess-highcontrast"),
    Toggle(("автояркост", "адаптивную яркость"), "Автояркость", page="display"),
    Toggle(("тачпад", "сенсорную панель"), "Сенсорная панель", page="devices-touchpad"),
    Toggle(("vpn", "впн"), "VPN", page="network-vpn"),
    Toggle(("геолокац", "местоположен", "определение местоположения"), "Доступ к геолокации",
           reg_toggle(W.CONSENT.format("location"), "Value", "Allow", "Deny", "str")),
    Toggle(("доступ к камер", "вебкамер", "веб-камер"), "Доступ приложений к камере",
           reg_toggle(W.CONSENT.format("webcam"), "Value", "Allow", "Deny", "str")),
    # ---- службы Windows (нужны права администратора) ----
    Toggle(("служба поиска", "службу поиска", "поиск windows", "индексирование", "индексацию"), "Служба поиска Windows",
           service("WSearch"), admin=True),
    Toggle(("диспетчер печати", "служба печати", "службу печати", "печать"), "Диспетчер печати", service("Spooler"), admin=True),
    Toggle(("удаленный реестр", "удалённый реестр", "удалённый реестр", "службу удаленного реестра"), "Удалённый реестр", service("RemoteRegistry"), admin=True),
    Toggle(("sysmain", "superfetch", "суперпоиск", "службу sysmain"), "Служба SysMain (Superfetch)", service("SysMain"), admin=True),
    Toggle(("телеметрия", "диагностика windows", "телеметрию"), "Телеметрия Windows (DiagTrack)", service("DiagTrack"),
           admin=True),
    Toggle(("служба факса", "службу факса", "факс"), "Служба факса", service("Fax"), admin=True),
    Toggle(("служба геолокации", "службу геолокации", "lfsvc"), "Служба геолокации Windows", service("lfsvc"), admin=True),
    Toggle(("удаленный рабочий стол", "удалённый рабочий стол"), "Удалённый рабочий стол",
           reg_admin(r"SYSTEM\CurrentControlSet\Control\Terminal Server", "fDenyTSConnections", 0, 1), admin=True),
    # ---- компоненты Windows (Turn Windows features on/off) ----
    Toggle(("hyper-v", "hyperv", "гипер-в", "гипер в"), "Hyper-V", feature("Microsoft-Hyper-V-All"), admin=True,
           note="Для Hyper-V может понадобиться перезагрузка."),
    Toggle(("wsl", "подсистему linux", "подсистема linux", "линукс"), "Подсистема Windows для Linux",
           feature("Microsoft-Windows-Subsystem-Linux"), admin=True, note="Нужна перезагрузка."),
    Toggle(("платформу виртуальных машин", "виртуальную машину платформу", "virtual machine platform"),
           "Платформа виртуальных машин", feature("VirtualMachinePlatform"), admin=True),
    Toggle(("песочниц", "windows sandbox", "виндовс песочниц"), "Песочница Windows",
           feature("Containers-DisposableClientVM"), admin=True),
    Toggle((".net framework 3.5", "net framework", "net 3.5", "дотнет 3.5"), ".NET Framework 3.5",
           feature("NetFx3"), admin=True),
    Toggle(("smb 1", "smb1", "протокол smb 1"), "Протокол SMB 1", feature("SMB1Protocol"), admin=True,
           note="SMB 1 считается небезопасным — лучше не включать."),
    Toggle(("telnet", "тельнет"), "Клиент Telnet", feature("TelnetClient"), admin=True),
    Toggle(("печать в pdf", "печать pdf", "microsoft print to pdf"), "Печать в PDF",
           feature("Printing-PrintToPDFServices-Features"), admin=True),
    Toggle(("windows media player", "медиаплеер windows", "проигрыватель windows"), "Проигрыватель Windows Media",
           feature("WindowsMediaPlayer"), admin=True),
    # ---- фон, советы и уведомления Windows ----
    Toggle(("фоновые приложения", "фоновых приложений", "работу в фоне", "фоновую работу"), "Фоновые приложения",
           reg_toggle(r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
                      "GlobalUserDisabled", 0, 1)),
    Toggle(("советы windows", "советы виндовс", "советы и рекомендации", "рекомендации windows"),
           "Советы и рекомендации Windows", reg_toggle(CDM, "SubscribedContent-338389Enabled", 1, 0)),
    Toggle(("уведомления синхронизации", "синхронизации в проводнике", "предложения проводника"),
           "Уведомления синхронизации в Проводнике", reg_toggle(ADV, "ShowSyncProviderNotifications", 1, 0, refresh=True)),
    # ---- служебные службы и функции (нужны права администратора) ----
    Toggle(("удалённый помощник", "удаленный помощник", "удалённую помощь", "удаленную помощь"), "Удалённый помощник",
           reg_admin(r"SYSTEM\CurrentControlSet\Control\Remote Assistance", "fAllowToGetHelp", 1, 0), admin=True),
    Toggle(("отчёты об ошибках", "отчеты об ошибках", "отправку ошибок", "отчёты windows"),
           "Отчёты об ошибках Windows", service("WerSvc"), admin=True),
    Toggle(("службы xbox", "службу xbox", "xbox live"), "Службы Xbox Live", service("XblAuthManager"), admin=True),
    Toggle(("службу биометрии", "биометрию windows", "биометрию", "распознавание отпечатка"),
           "Служба биометрии Windows", service("WbioSrvc"), admin=True,
           note="Без неё не работают вход по отпечатку и распознаванием лица Windows Hello."),
    Toggle(("службу обновлений windows", "службу центра обновления", "автообновления windows"),
           "Служба обновлений Windows", service("wuauserv"), admin=True,
           note="Без неё Windows не получит обновления безопасности. Включай обратно, как только нужно."),
    Toggle(("службу bluetooth", "службу блютуз", "поддержку bluetooth"), "Служба поддержки Bluetooth",
           service("bthserv"), admin=True,
           note="Без неё Bluetooth-устройства не подключатся, даже если сам Bluetooth включён."),
    Toggle(("синхронизацию времени", "службу времени", "синхронизацию часов"), "Синхронизация времени Windows",
           service("W32Time"), admin=True),
    Toggle(("сжатие памяти", "компрессию памяти", "memory compression"), "Сжатие памяти",
           cmd_admin("powershell -NoProfile -Command Enable-MMAgent -MemoryCompression",
                     "powershell -NoProfile -Command Disable-MMAgent -MemoryCompression"), admin=True),
    Toggle(("аппаратное планирование gpu", "планирование gpu", "hardware scheduling", "аппаратное ускорение gpu"),
           "Аппаратное планирование GPU",
           reg_admin(r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 2, 1), admin=True,
           note="Нужна перезагрузка ПК, чтобы изменение применилось."),

    # ---- со скриншотов «Параметры → Система / Конфиденциальность» ----
    Toggle(("режим разработчика", "режим разработчиков", "developer mode"), "Режим разработчика",
           reg_admin(r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock",
                     "AllowDevelopmentWithoutDevLicense", 1, 0), admin=True,
           note="Теперь можно ставить приложения из любого источника."),
    Toggle(("портал устройств", "device portal"), "Портал устройств",
           ui("ms-settings:developers", "Портал устройств"),
           note="Переключатель на странице «Для разработчиков» — Mico нажал его сам."),
    Toggle(("обнаружение устройств", "обнаружение устройства"), "Обнаружение устройств",
           ui("ms-settings:developers", "Обнаружение устройств")),
    Toggle(("длинные пути", "длинные имена файлов", "длинные пути файлов", "max_path"),
           "Длинные пути файлов",
           reg_admin(r"SYSTEM\CurrentControlSet\Control\FileSystem", "LongPathsEnabled", 1, 0), admin=True),
    Toggle(("sudo", "судо"), "sudo для Windows",
           cmd_admin("sudo config --enable normal", "sudo config --enable disable"), admin=True,
           note="Команда sudo работает только в новых сборках Windows 11."),
    Toggle(("завершение задачи", "завершить задачу", "end task"), "Завершение задачи на панели задач",
           reg_toggle(ADV, "TaskbarEndTask", 1, 0, refresh=True)),
    Toggle(("прикреплять окна", "прикрепление окон", "прикрепить окна", "snap", "привязка окон",
            "прикрепление окна"), "Прикрепление окон",
           reg_toggle(r"Control Panel\Desktop", "WindowArrangementActive", "1", "0", kind="str")),
    Toggle(("встряхивание заголовка", "встряхивание окна", "встряхивание", "встряхивания"),
           "Встряхивание заголовка окна",
           reg_toggle(ADV, "DisallowShaking", 0, 1), note="Включено — встряхивание сворачивает остальные окна."),
    Toggle(("монозвук", "моно звук", "монорежим", "объединение каналов"), "Монозвук",
           reg_toggle(r"Software\Microsoft\Multimedia\Audio", "AccessibilityMonoMixState", 1, 0)),
    Toggle(("журнал буфера обмена на ваших устройствах", "журнал буфера обмена на устройствах",
            "буфер обмена на ваших устройствах", "журнал буфера на устройствах", "буфер на ваших устройствах",
            "синхронизацию буфера", "синхронизация буфера"), "Журнал буфера обмена на ваших устройствах",
           reg_toggle(REG_CLIP, "CloudClipboardAutomaticUpload", 1, 0),
           note="Работает только при входе в учётную запись Microsoft."),
    Toggle(("обмен с устройствами поблизости", "обмен поблизости", "устройства поблизости", "nearby sharing"),
           "Обмен с устройствами поблизости",
           ui_select("ms-settings:crossdevice", {True: "Только мои устройства", False: "Отключено"}),
           note="Для обмена может понадобиться вход в учётную запись Microsoft."),
    Toggle(("alt+tab вкладки", "вкладки alt+tab", "вкладки alt tab", "вкладки alt", "показывать вкладки",
            "вкладки при alt", "вкладки при alt+tab"),
           "Показ вкладок браузера при Alt+Tab", page="multitasking"),
    Toggle(("автоотключение экрана", "отключать экран", "гашение экрана", "экран гаснет"), "Отключение экрана по таймеру",
           shell("powercfg /change monitor-timeout-ac 15 & powercfg /change monitor-timeout-dc 5",
                 "powercfg /change monitor-timeout-ac 0 & powercfg /change monitor-timeout-dc 0"),
           note="Включено: через 15 мин от сети и 5 мин от батареи. Выключено: никогда."),
    Toggle(("спящий режим по таймеру", "автосон", "автоматический сон", "перевод в спящий режим"),
           "Переход в спящий режим по таймеру",
           shell("powercfg /change standby-timeout-ac 30 & powercfg /change standby-timeout-dc 15",
                 "powercfg /change standby-timeout-ac 0 & powercfg /change standby-timeout-dc 0"),
           note="Включено: через 30 мин от сети и 15 мин от батареи. Выключено: никогда."),
    Toggle(("гибернация по таймеру", "гибернацию по таймеру"), "Гибернация по таймеру",
           shell("powercfg /change hibernate-timeout-ac 60", "powercfg /change hibernate-timeout-ac 0"),
           note="Включено: через 60 мин от сети. Выключено: никогда."),
    Toggle(("уведомления в играх", "уведомления в полноэкранных"), "Уведомления в полноэкранных играх",
           page="quietmomentsgame"),
    Toggle(("фокусировку", "фокусировка", "режим фокуса"), "Фокусировка", page="focus"),
    Toggle(("автоматически не беспокоить", "не беспокоить автоматически"), "Автоматический режим «Не беспокоить»",
           page="notifications"),
    Toggle(("подключённые устройства", "подключенные устройства"), "Подключённые устройства", page="connecteddevices"),
    Toggle(("win+r", "win r", "диалоговое окно выполнить", "окно выполнить", "диалог выполнить"),
           "Современное окно «Выполнить» (Win+R)", page="system",
           note="Windows не даёт переключить его из программы — открыл «Систему», дальше «Дополнительно»."),
    Toggle(("терминал по умолчанию", "терминал windows"), "Терминал по умолчанию", page="developers"),


    # ---- со скриншотов: VPN, Wi-Fi, Ethernet, мышь, клавиатура, принтеры, прокси, мобильные устройства ----
    Toggle(("vpn в лимитных сетях", "vpn в сетях с лимитным", "лимитные сети vpn", "лимитным тарифным"),
           "VPN в сетях с лимитным тарифным планом",
           ui("ms-settings:network-vpn", "Разрешить VPN в сетях с лимитным тарифным планом")),
    Toggle(("vpn в роуминге", "роуминг vpn", "впн в роуминге"), "VPN в роуминге",
           ui("ms-settings:network-vpn", "Разрешить VPN в роуминге")),
    Toggle(("случайные аппаратные адреса", "случайный mac", "случайные mac", "случайный адрес wi-fi",
            "случайные адреса"), "Случайные аппаратные адреса Wi-Fi",
           ui("ms-settings:network-wifi", "Случайные аппаратные адреса"),
           note="Помогает не давать отслеживать устройство по адресу. Иногда нужно переподключиться к сети."),
    Toggle(("лимитное подключение", "лимитное ethernet", "лимитный ethernet", "лимит трафика ethernet"),
           "Лимитное подключение (Ethernet)",
           ui("ms-settings:network-ethernet", "Лимитное подключение")),
    Toggle(("адаптер ethernet", "проводной адаптер", "сетевую карту ethernet"), "Адаптер Ethernet",
           adapter("Physical", "802.3"), admin=True,
           note="Выключен адаптер — проводного интернета не будет, пока не включишь обратно.",
           confirm_off="Отключить адаптер Ethernet? Проводной интернет пропадёт."),
    Toggle(("адаптер wi-fi", "адаптер вайфай", "беспроводной адаптер", "сетевой адаптер wi-fi"),
           "Адаптер Wi-Fi", adapter("Physical", "Native 802.11"), admin=True,
           note="Выключен адаптер — Wi-Fi пропадёт, пока не включишь обратно.",
           confirm_off="Отключить адаптер Wi-Fi? Интернет по Wi-Fi пропадёт."),
    Toggle(("прокручивать неактивные", "неактивные окна при наведении", "прокрутка неактивных окон",
            "прокрутку неактивных"), "Прокрутка неактивных окон при наведении",
           ui("ms-settings:mousetouchpad", "Прокручивать неактивные окна при наведении на них")),
    Toggle(("повышение точности указателя", "точность указателя", "повышенную точность", "ускорение мыши"),
           "Повышение точности указателя", lambda on: W.set_mouse_precision(on)),
    Toggle(("print screen", "принтскрин", "prtscn", "клавишу print screen", "кнопку print screen"),
           "PrintScreen открывает захват экрана",
           reg_toggle(r"Control Panel\Keyboard", "PrintScreenKeyForSnippingEnabled", 1, 0),
           note="Теперь PrintScreen открывает «Ножницы» (захват экрана)."),
    Toggle(("автоматическое определение прокси", "определять прокси", "автоопределение прокси",
            "определять параметры прокси"), "Автоматическое определение прокси",
           reg_toggle(r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "AutoDetect", 1, 0),
           note="Прокси подбирается автоматически. Если интернет стал медленным — выключи."),
    Toggle(("ручной прокси", "прокси вручную", "прокси-сервер вручную", "использовать прокси",
            "использовать прокси-сервер"), "Прокси-сервер вручную",
           reg_toggle(r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyEnable", 1, 0),
           note="Адрес прокси задаётся в «Параметрах» → «Прокси-сервер» → «Настройка»."),
    Toggle(("ready print", "windows ready print", "устанавливать принтеры по умолчанию"),
           "Установка принтеров через Windows Ready Print",
           ui("ms-settings:printers", "Устанавливать принтеры по умолчанию с помощью Windows Ready Print")),
    Toggle(("управление принтером по умолчанию", "управлять принтером по умолчанию", "управляет принтером по умолчанию",
            "windows управляет принтером", "принтер по умолчанию windows"),
           "Windows управляет принтером по умолчанию",
           reg_toggle(r"Software\Microsoft\Windows NT\CurrentVersion\Windows", "LegacyDefaultPrinterMode", 0, 1),
           note="Выключено — принтер по умолчанию будет последним использованным."),
    Toggle(("драйверы через лимитные", "драйверы принтера через лимитные", "драйверы через лимит"),
           "Драйверы принтеров через лимитные подключения",
           ui("ms-settings:printers", "Загружать драйверы и программное обеспечение устройства через лимитные подключения")),
    Toggle(("доступ к мобильным устройствам", "мобильные устройства", "телефон к компьютеру", "доступ к телефону"),
           "Доступ этого ПК к мобильным устройствам",
           ui("ms-settings:mobile-devices", "Разрешить этому компьютеру доступ к содержимому и возможностям с ваших мобильных устройств")),
    Toggle(("предложения по мобильному", "предложения по телефону"), "Предложения по использованию мобильного устройства",
           ui("ms-settings:mobile-devices", "Показать предложения по использованию мобильного устройства с Windows")),


    # ---- персонализация: цвета, Пуск, панель задач ----
    Toggle(("цвет на пуск и панель задач", "акцентный цвет на пуск", "цвет элементов в меню пуск",
            "цвет на панели задач", "цвет в пуск и на панели"), "Акцентный цвет в меню «Пуск» и на панели задач",
           reg_toggle(r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "ColorPrevalence", 1, 0)),
    Toggle(("цвет заголовков", "цвет заголовков окон", "цвет границ окон", "контрастный цвет заголовков",
            "цвет границ"), "Акцентный цвет заголовков и границ окон",
           reg_toggle(r"Software\Microsoft\Windows\DWM", "ColorPrevalence", 1, 0)),
    Toggle(("недавние приложения в пуск", "недавно добавленные приложения", "недавние приложения"),
           "Недавно добавленные приложения в «Пуске»",
           reg_toggle(ADV, "Start_TrackProgs", 1, 0)),
    Toggle(("недавние файлы в пуск", "недавние элементы в списках переходов", "списки переходов",
            "недавние файлы", "недавние элементы"), "Недавние элементы в списках переходов и проводнике",
           reg_toggle(ADV, "Start_TrackDocs", 1, 0), note="Перезапусти проводник, чтобы изменения увидеть сразу."),
    Toggle(("имя и аватар на начальном экране", "скрыть имя", "скрыть аватар"), "Скрыть имя и аватар на начальном экране",
           ui("ms-settings:personalization-start", "Скрыть свое имя и аватар на начальном экране")),
    Toggle(("уведомления учётной записи", "уведомления учетной записи", "уведомления касающиеся учётной записи"),
           "Уведомления, касающиеся учётной записи",
           ui("ms-settings:personalization-start", "Отображать уведомления, касающиеся учетной записи")),
    Toggle(("все приложения в пуск", "список всех приложений", "все установленные приложения в пуск"),
           "Все приложения в меню «Пуск»",
           ui("ms-settings:personalization-start", "Все")),
    Toggle(("мобильное устройство в пуск", "телефон в пуск"), "Мобильное устройство в меню «Пуск»",
           ui("ms-settings:personalization-start", "Показывать мобильное устройство в меню")),
    Toggle(("автоскрытие панели задач", "автоматически скрывать панель задач", "скрывать панель задач",
            "скрывать панель"), "Автоматически скрывать панель задач",
           ui("ms-settings:taskbar", "Автоматически скрывать панель задач")),
    Toggle(("значки приложений на панели", "значки в приложениях на панели задач"), "Значки приложений на панели задач",
           ui("ms-settings:taskbar", "Показывать значки в приложениях на панели задач")),
    Toggle(("мигание значков", "мигание на панели задач", "мигание значков приложений"),
           "Мигание значков приложений на панели задач",
           ui("ms-settings:taskbar", "Показывать мигание значков приложений на панели задач")),
    Toggle(("дальний угол панели", "рабочий стол в дальнем углу", "показать рабочий стол в углу",
            "дальний угол"), "Показ рабочего стола в дальнем углу панели задач",
           reg_toggle(ADV, "TaskbarSd", 1, 0, refresh=True)),
    Toggle(("мини-приложения", "мини приложения", "мини-приложение"), "Мини-приложения на панели задач",
           ui("ms-settings:taskbar", "Мини-приложения")),
    Toggle(("возобновить на панели", "кнопка возобновить", "значок возобновить"), "Значок «Возобновить» на панели задач",
           ui("ms-settings:taskbar", "Возобновить")),
    Toggle(("эмодзи на панели", "панель эмодзи", "значок эмодзи"), "Значок эмодзи на панели задач",
           ui("ms-settings:taskbar", "Эмодзи и другие элементы")),
    Toggle(("меню пера", "значок пера"), "Меню пера на панели задач",
           ui("ms-settings:taskbar", "Меню пера")),
    Toggle(("классическое контекстное меню", "полное контекстное меню", "старое контекстное меню",
            "контекстное меню прежних версий", "дополнительные параметры в контекстном меню"),
           "Классическое контекстное меню", lambda on: W.classic_context_menu(on),
           note="Изменение появится после перезапуска проводника — скажи «перезапусти проводник»."),

    # ---- ввод текста ----
    Toggle(("автоисправление слов", "автоматически исправлять слова", "автоисправление", "исправлять слова с ошибками"),
           "Автоматически исправлять слова с ошибками",
           reg_toggle(r"Software\Microsoft\TabletTip\1.7", "EnableAutocorrection", 1, 0)),
    Toggle(("выделять слова с ошибками", "подчёркивать ошибки", "подчеркивать ошибки", "проверка орфографии"),
           "Выделять слова с ошибками",
           reg_toggle(r"Software\Microsoft\TabletTip\1.7", "EnableSpellchecking", 1, 0)),
    Toggle(("текстовые предложения при вводе", "предложения при вводе", "подсказки при наборе",
            "текстовые предложения на физической клавиатуре"), "Текстовые предложения при вводе на физической клавиатуре",
           ui("ms-settings:typing", "Показывать текстовые предложения при вводе на физической клавиатуре")),
    Toggle(("многоязычные предложения", "многоязычные текстовые предложения"), "Многоязычные текстовые предложения",
           ui("ms-settings:typing", "Многоязычные текстовые предложения")),

    # ---- видео и игры ----
    Toggle(("автоулучшение видео", "улучшать видео", "автоматически обрабатывать видео", "обработка видео",
            "автоматическую обработку видео", "обработку видео"),
           "Автоматическая обработка видео",
           ui("ms-settings:videoplayback", "Автоматически обрабатывать видео для его улучшения")),
    Toggle(("экономия трафика видео", "видео с низким разрешением", "низкое разрешение видео"),
           "Видео с более низким разрешением для экономии сети",
           ui("ms-settings:videoplayback", "Экономьте пропускную способность сети")),
    Toggle(("геймпад открывает game bar", "геймпад game bar", "игровая панель геймпадом"),
           "Геймпад открывает Game Bar",
           ui("ms-settings:gaming-gamebar", "Разрешить геймпаду открывать Game Bar")),
    Toggle(("кнопка гида", "кнопка гида в приложениях", "кнопка xbox в приложениях"),
           "Кнопка «Гид» в приложениях",
           ui("ms-settings:gaming-gamebar", "Используйте")),
    Toggle(("запись событий", "запись моментов", "запись событий в игре"), "Запись событий в играх",
           ui("ms-settings:gaming-gamedvr", "Запись событий")),
    Toggle(("звук при записи игры", "запись звука игры", "звук при записи"), "Запись звука при записи игры",
           ui("ms-settings:gaming-gamedvr", "Запись звука при записи игры")),
    Toggle(("курсор при записи", "курсор мыши при записи игры", "курсор в записи"), "Курсор мыши при записи игры",
           ui("ms-settings:gaming-gamedvr", "Отображать курсор мыши при записи игры")),

    # ---- дата и время ----
    Toggle(("часовой пояс автоматически", "автоматический часовой пояс", "устанавливать часовой пояс"),
           "Устанавливать часовой пояс автоматически",
           ui("ms-settings:dateandtime", "Устанавливать часовой пояс автоматически")),
    Toggle(("время автоматически", "устанавливать время автоматически", "автоматическое время", "время по сети"),
           "Устанавливать время автоматически",
           ui("ms-settings:dateandtime", "Устанавливать время автоматически")),
    Toggle(("время в области уведомлений", "время и дату в области уведомлений", "часы на панели",
            "дата на панели", "часы на панели задач"), "Показывать время и дату на панели задач",
           ui("ms-settings:dateandtime", "Показывать время и дату в области уведомлений")),
    Toggle(("время в центре уведомлений", "время в уведомлениях"), "Показывать время в центре уведомлений",
           ui("ms-settings:dateandtime", "Показывать время в центре уведомлений")),

    # ---- освещение ----
    Toggle(("динамическое освещение", "подсветка устройств", "rgb подсветка"), "Динамическое освещение на моих устройствах",
           ui("ms-settings:personalization-lighting", "Использовать динамическое освещение на моих устройствах")),

]

_TOGGLE_KEYS = sorted(((k, t) for t in TOGGLES for k in t.keys), key=lambda kt: -len(kt[0]))


ADJUSTS = [
    Adjust(("скорость указателя", "скорость мыши", "чувствительность мыши", "скорость курсора", "скорость указателя мыши"),
           "Скорость указателя мыши", W.set_mouse_speed,
           lambda: (lambda v: None if v is None else int(v))(W.reg_get(r"Control Panel\Mouse", "MouseSensitivity")),
           1, 20, step=2, unit="из 20"),
    Adjust(("строки прокрутки", "строк прокрутки", "прокрутку строк", "строк за раз", "строк при прокрутке",
            "строки для прокрутки"), "Строки прокрутки за раз", W.set_wheel_lines,
           lambda: (lambda v: None if v is None else int(v))(W.reg_get(r"Control Panel\Desktop", "WheelScrollLines")),
           1, 100, step=1, unit=""),
    Adjust(("задержка повтора", "задержку повтора", "задержка повтора символов"), "Задержка повтора символов",
           W.set_key_delay, lambda: (lambda v: None if v is None else int(v))(
               W.reg_get(r"Control Panel\Keyboard", "KeyboardDelay")),
           0, 3, step=1, labels={0: "короткая", 1: "немного длиннее", 2: "длинная", 3: "самая длинная"}),
    Adjust(("частота повтора", "частоту повтора", "скорость повтора", "частота повтора символов"),
           "Частота повтора символов", W.set_key_speed,
           lambda: (lambda v: None if v is None else int(v))(W.reg_get(r"Control Panel\Keyboard", "KeyboardSpeed")),
           0, 31, step=4, labels={0: "очень медленно", 31: "очень быстро"}),
    Adjust(("через сколько гаснет экран", "время гашения экрана", "таймаут экрана", "отключать экран через",
            "экран гаснет через", "отключение экрана через"), "Отключение экрана через",
           lambda n: W.set_powercfg("monitor-timeout", n), lambda: None, 0, 240, step=5, unit="мин",
           labels={0: "никогда"}),
    Adjust(("через сколько спящий режим", "время до сна", "таймаут сна", "спящий режим через",
            "перевод в спящий режим через", "сон через"), "Спящий режим через",
           lambda n: W.set_powercfg("standby-timeout", n), lambda: None, 0, 480, step=10, unit="мин",
           labels={0: "никогда"}),
    Adjust(("гибернация через", "гибернацию через", "ввод в гибернацию через", "гибернация по таймеру через"),
           "Гибернация через", lambda n: W.set_powercfg("hibernate-timeout", n), lambda: None, 0, 1440, step=30,
           unit="мин", labels={0: "никогда"}),
]



class Choice:
    """Настройка с вариантами: «размер панели задач — большая». options — [(слова-признаки, подпись, значение)].
    set(value) -> (ok, сообщение); get() -> значение или None."""
    def __init__(self, keys, name, options, set, get=None, note=""):
        self.keys, self.name, self.options, self.set, self.get, self.note = keys, name, options, set, get, note

    def find_option(self, ql):
        """Самый длинный совпавший признак побеждает: «2 часа» важнее «час»."""
        best, best_len = None, 0
        for stems, label, value in self.options:
            for st in stems:
                if re.search(r"(?<![\w-])" + re.escape(st), ql) and len(st) > best_len:
                    best, best_len = (label, value), len(st)
        return best


CHOICES = [
    Choice(("размер панели задач", "размер панели", "размер значков панели"), "Размер панели задач",
           [(("маленьк", "мелк"), "маленькая", 0), (("по умолчанию", "обычн", "стандартн"), "по умолчанию", 1),
            (("больш", "крупн"), "большая", 2)],
           set=lambda v: (W.reg_set(ADV, "TaskbarSi", v), W.broadcast_setting("Policy"), (True, ""))[2],
           get=lambda: W.reg_get(ADV, "TaskbarSi"),
           note="Изменение может появиться не сразу — если панель не изменилась, скажи «перезапусти проводник»."),
    Choice(("объединение кнопок", "объединить кнопки панели", "объединить кнопки", "группировка кнопок"),
           "Объединение кнопок панели задач",
           [(("всегда",), "всегда", 2), (("переполнен", "заполнен"), "при переполнении", 1),
            (("никогда",), "никогда", 0)],
           set=lambda v: (W.reg_set(ADV, "TaskbarGlomLevel", v), W.broadcast_setting("Policy"), (True, ""))[2],
           get=lambda: W.reg_get(ADV, "TaskbarGlomLevel")),
    Choice(("размер меню пуск", "размер меню", "размер пуск"), "Размер меню «Пуск»",
           [(("автоматическ", "по умолчанию"), "автоматически", "Автоматически (по умолчанию)"),
            (("меньш", "маленьк"), "меньше", "Меньше"), (("больш",), "больше", "Больше")],
           set=lambda v: W.ui_choose("ms-settings:personalization-start", "Размер меню \"Пуск\"", v),
           note="Выбор делается на странице «Пуск» через её список."),
    Choice(("качество видео записи", "качество записи", "качество видео игры"), "Качество видео записи игр",
           [(("стандартн",), "стандартное", "Стандартное"), (("высок", "лучш"), "высокое", "Высокое")],
           set=lambda v: W.ui_choose("ms-settings:gaming-gamedvr", "Качество видео", v)),
    Choice(("частота кадров записи", "частоту кадров записи", "кадров записи", "fps записи",
            "частота видеокадров", "частоту видеокадров", "частоту видеокадров записи"),
           "Частота видеокадров записи",
           [(("30",), "30 кадров в секунду", "30 кадр/с (рекомендуется)"),
            (("60",), "60 кадров в секунду", "60 кадр/с")],
           set=lambda v: W.ui_choose("ms-settings:gaming-gamedvr", "Частота видеокадров", v)),
    Choice(("максимальная длина записи", "максимальную длину записи", "длина записи", "длительность записи"),
           "Максимальная длина записи",
           [(("30 минут", "полчаса", "30 мин"), "30 минут", "30 минут"),
            (("1 час", "час"), "1 час", "1 час"), (("2 часа", "два часа"), "2 часа", "2 часа"),
            (("4 часа", "четыре часа"), "4 часа", "4 часа")],
           set=lambda v: W.ui_choose("ms-settings:gaming-gamedvr", "Максимальная длина записи", v)),
]


_ADJ_KEYS = sorted(((k, a) for a in ADJUSTS for k in a.keys), key=lambda kv: -len(kv[0]))


def find_adjust(ql):
    """Настройка с регулировкой по фразе: «скорость указателя», «строки прокрутки», «через сколько гаснет экран»."""
    for k, a in _ADJ_KEYS:
        if re.search(r"(?<![\w-])" + re.escape(k), ql):
            return a
    return None


def find_choice(ql):
    """Выбор варианта: («размер панели задач большая») -> (Choice, (подпись, значение)) или None."""
    for c in CHOICES:
        if any(re.search(r"(?<![\w-])" + re.escape(k), ql) for k in c.keys):
            opt = c.find_option(ql)
            return c, opt
    return None


def find_toggle_or_adjust(ql):
    """Что названо во фразе: ('toggle', t) | ('adjust', a) | (None, None)."""
    a = find_adjust(ql)
    if a:
        return "adjust", a
    t = find_toggle(ql)
    return ("toggle", t) if t else (None, None)

def find_toggle(ql):
    """Переключатель по фразе. Сначала точное совпадение ключевых слов, потом — с опечатками."""
    for k, t in _TOGGLE_KEYS:
        if re.search(r"(?<![\w-])" + re.escape(k), ql):
            return t
    return _fuzzy_toggle(ql, cutoff=0.85)


_WORD = re.compile(r"[а-яёa-z][а-яёa-z\-]*", re.IGNORECASE)


def _fuzzy_toggle(ql, cutoff):
    """«гибергацию» → «гибернаци»: сравниваем начало слова с ключевым словом той же длины."""
    best, score = None, cutoff
    for word in _WORD.findall(ql.lower().replace("ё", "е")):
        if len(word) < 6:
            continue
        for k, t in _TOGGLE_KEYS:
            if len(k) < 6 or " " in k:
                continue
            r = difflib.SequenceMatcher(None, word[:len(k)], k).ratio()
            if r >= score:
                best, score = t, r
    return best


def suggest(ql, limit=3):
    """Похожие названия переключателей, если точного нет (для подсказки «возможно, вы имели в виду»)."""
    found = []
    for word in _WORD.findall(ql.lower().replace("ё", "е")):
        if len(word) < 5:
            continue
        for k, t in _TOGGLE_KEYS:
            if len(k) >= 6 and len(word) >= 6 and difflib.SequenceMatcher(None, word[:len(k)], k).ratio() >= 0.75:
                if t.name not in found:
                    found.append(t.name)
    return found[:limit]


# ============================ Системные действия (без «включи/выключи») ============================
def _open(target):
    def fn():
        W.open_path(target)
        return True, ""
    return fn


def _cmd(cmdline, admin=False):
    def fn():
        if admin:
            return W.run_elevated(cmdline)
        r = subprocess.run(cmdline, shell=True, capture_output=True, creationflags=NOWIN)
        return r.returncode == 0, ""
    return fn


ACTIONS = [
    (r"провер\w*\s+обновлени|поищи\s+обновлени|поиск\s+обновлени|обнови\s+windows|обновления\s+windows",
     "Проверяю обновления Windows — открыл «Центр обновления» 🔄", W.check_updates),
    (r"очисти\w*\s+(кэш|кеш)\s+dns|сбрось\s+dns|очисти\w*\s+dns", "Кэш DNS очищен 🧹", _cmd("ipconfig /flushdns")),
    (r"перезапусти\s+проводник", "Перезапускаю проводник 🗂", _cmd("taskkill /f /im explorer.exe & start explorer")),
    (r"диспетчер\s+задач", "Открываю диспетчер задач 📊", _open("taskmgr")),
    (r"диспетчер\s+устройств", "Открываю диспетчер устройств 🔧", _open("devmgmt.msc")),
    (r"управлени\w+\s+дисками", "Открываю управление дисками 💽", _open("diskmgmt.msc")),
    (r"монитор\s+ресурсов", "Открываю монитор ресурсов 📈", _open("resmon")),
    (r"(оснастк\w*\s+)?служб\w*\s+windows|открой\s+службы\b", "Открываю службы Windows ⚙", _open("services.msc")),
    (r"панель\s+управления", "Открываю панель управления 🛠", _open("control")),
    (r"очисти\w*\s+временн\w*\s+файлы|почисти\s+диск", "Открываю очистку диска 🧹", _open("cleanmgr")),
    (r"восстановлени\w+\s+системы", "Открываю восстановление системы ⏪", _open("rstrui")),
    (r"проверь\s+целостност\w*\s+(системы|windows)|sfc", "Проверяю целостность системных файлов (sfc /scannow) 🩺",
     _cmd("sfc /scannow", admin=True)),
    (r"сбрось\s+(сеть|сетевые\s+настройки)|сброс\s+сети", "Сбрасываю сетевые настройки (потом нужна перезагрузка) 🌐",
     _cmd("netsh winsock reset & netsh int ip reset", admin=True)),
    (r"очисти\w*\s+(данные\s+)?буфер\w*\s+обмена|очисти\w*\s+журнал\w*\s+буфера|почисти\s+буфер",
     "Очистил данные буфера обмена (закреплённые элементы остались) 📋",
     lambda: W.ui_setting("ms-settings:clipboard", "Очистить", mode="click")),
    (r"начни\w*\s+(период\s+)?фокусировк\w*|запусти\s+фокусировк\w*|фокусировк\w*\s+на\s+30",
     "Запустил период фокусировки на 30 минут 🎯",
     lambda: W.ui_setting("ms-settings:focus", "Начать период фокусировки", mode="click")),
    (r"сбрось\s+(пк|компьютер|windows|виндовс)|верни\w*\s+(пк|компьютер)\s+в\s+исходн|переустанови\w*\s+(windows|виндовс)",
     "Сброс и переустановку я не запускаю — открыл страницу восстановления, решай там сам(а) ⚠️",
     _open("ms-settings:recovery")),
    (r"обнови\s+драйвер", "Открываю обновления драйверов 🧩",
     _open("ms-settings:windowsupdate-optionaldownloads")),
]

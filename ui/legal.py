"""Тексты ссылок под приветствием чата: «Подробнее», «Условия использования», «Конфиденциальность».
Опираются на PRIVACY.md и LICENSE (MIT). Меняешь поведение с данными — поправь и эти тексты. Только текст, без Qt."""
import i18n

_CSS = "<style>h3{margin:14px 0 4px 0;font-size:14px;} p,li{line-height:145%;} ul{margin-left:-14px;}</style>"

RU = {
    "about": ("О Mico AI", """
<p><b>Mico AI</b> — ИИ-компаньон для Windows 11. Он живёт на рабочем столе, отвечает на вопросы и помогает с делами на компьютере.</p>
<h3>Как Mico отвечает</h3>
<ul>
<li>По умолчанию — <b>локальная модель</b> на твоём ПК. Интернет для этого не нужен.</li>
<li>По умолчанию Mico отвечает через <b>облако Mico</b>: текст чата уходит на сервер Mico AI (Cloudflare), ключей нет. В «Настройки → Модели и ключи» можно выбрать локальную модель, если она скачана.</li>
<li>Стиль общения меняет манеру ответа: <b>творческий</b> — свободнее и с идеями, <b>сбалансированный</b> — посередине, <b>точный</b> — коротко и по делу.</li>
</ul>
<h3>Что Mico умеет</h3>
<ul>
<li>Открывать программы, папки и сайты; искать файлы.</li>
<li>Менять громкость, яркость, тему Windows; делать скриншоты.</li>
<li>Ставить таймеры, будильники и напоминания, вести календарь.</li>
<li>Рассказывать погоду, искать в интернете, включать видео.</li>
<li>Разговаривать голосом: распознавание и озвучка работают на ПК.</li>
<li>Помнить разговор и рассказывать, что ты делал («что я делал час назад?»).</li>
</ul>
<h3>Быстрые действия</h3>
<p>В пустом чате Mico предлагает то, что ты делаешь чаще всего: команды, которые ты просишь в это время дня, и программы, в которых ты больше всего работал за две недели. Отключить: «Настройки → Общение → Быстрые действия».</p>
<h3>Безопасность</h3>
<p>Действия, которые меняют систему (выключение, службы, PowerShell, удаление), Mico выполняет только после твоего «да».</p>
<h3>Важно</h3>
<p>Ответы составляет ИИ, и он может ошибаться. Проверяй важное: цифры, даты, советы по здоровью, деньгам и закону.</p>
"""),
    "terms": ("Условия использования", """
<h3>1. Лицензия</h3>
<p>Mico AI распространяется по лицензии <b>MIT</b> (файл LICENSE). Программой можно пользоваться, копировать и изменять бесплатно. Она предоставляется «как есть», без гарантий: автор не отвечает за ущерб от её использования.</p>
<h3>2. Ответы ИИ</h3>
<p>Ответы генерирует модель искусственного интеллекта. Они могут быть неточными или устаревшими. Не используй их вместо совета врача, юриста или финансового специалиста.</p>
<h3>3. Действия на компьютере</h3>
<p>Mico действует по твоим просьбам. Перед опасными действиями он спрашивает «да», и ответственность за подтверждённые команды лежит на тебе. Режим агента — эксперимент и по умолчанию выключен.</p>
<h3>4. Что нельзя</h3>
<p>Не используй Mico для незаконных действий, обхода защиты, доступа к чужим данным и рассылки спама.</p>
<h3>5. Сторонние сервисы</h3>
<p>Если ты используешь облако Mico, поиск (DuckDuckGo, YouTube) или погоду (Open-Meteo), действуют ещё и правила этих сервисов.</p>
<h3>6. Обновления</h3>
<p>Раз в сутки Mico проверяет на GitHub, вышла ли новая версия. Проверку можно выключить в настройках. Условия могут меняться вместе с новыми версиями.</p>
"""),
    "privacy": ("Конфиденциальность", """
<p>Mico AI работает на твоём компьютере. У Mico нет аккаунтов и регистрации, он не отправляет статистику разработчику.</p>
<h3>Что хранится на ПК</h3>
<p>Всё лежит в папке <b>%APPDATA%\\Mico</b>.</p>
<ul>
<li><b>История чатов, журнал команд, заметки, напоминания, календарь</b> — зашифрованы.</li>
<li><b>Журнал окон и программ</b> (какое окно было активно и сколько времени) зашифрован ключом Windows (DPAPI) и Fernet. Он нужен для «что я делал?» и быстрых действий по привычкам. Окна из списка исключений записываются как «[скрыто]».</li>
<li><b>Факты о тебе.</b> То, что ты сам сказал («запомни, что…»), и привычки, которые повторились не меньше трёх раз. Фразы про здоровье, деньги, адрес, семью и пароли не сохраняются.</li>
<li><b>Настройки</b> (config.json) и журналы запуска лежат открытым текстом: в них нет переписок и паролей.</li>
<li><b>Скриншоты</b>, которые ты просил, — в папке «Изображения\\Mico».</li>
</ul>
<h3>Что уходит в интернет</h3>
<p>Только то, что нужно для включённой функции:</p>
<ul>
<li><b>Облако Mico (Cloudflare)</b> — если выбран облачный источник ответов: уходит текст чата и его короткая история. Ответ формирует Cloudflare Workers AI, Groq, Google Gemini или NVIDIA, в зависимости от уровня. Снимки экрана в облако не отправляются. Если включён режим агента, в облако уходят ещё названия кнопок и полей активного окна и сама задача.</li>
<li><b>Поиск</b> — текст запроса в DuckDuckGo или YouTube.</li>
<li><b>Погода</b> — координаты в Open-Meteo.</li>
<li><b>Проверка версии</b> — запрос номера релиза на GitHub раз в сутки.</li>
</ul>
<p>Голос распознаётся и озвучивается на ПК, записи звука не сохраняются.</p>
<h3>Как управлять данными</h3>
<ul>
<li>«Настройки → Данные»: срок хранения истории и список «Что Mico AI знает», где можно удалить записи.</li>
<li>Скажи «что ты обо мне знаешь», «забудь факт N» или «забудь всё обо мне».</li>
<li>Быстрые действия по привычкам выключаются в «Настройки → Общение».</li>
<li>Удаление Mico может стереть и все данные — если отметишь это в мастере удаления.</li>
</ul>
<p>Полный текст — в файле PRIVACY.md в папке программы.</p>
"""),
}

EN = {
    "about": ("About Mico AI", """
<p><b>Mico AI</b> is an AI companion for Windows 11. It lives on your desktop, answers questions and helps with everyday tasks on your PC.</p>
<h3>How Mico answers</h3>
<ul>
<li>By default it uses a <b>local model</b> on your PC. No internet is needed for that.</li>
<li>By default Mico answers through <b>Mico Cloud</b>: chat text goes to the Mico AI server (Cloudflare), there are no keys. In “Settings → Models and keys” you can choose the local model if it is downloaded.</li>
<li>The conversation style changes the tone: <b>creative</b> is freer and full of ideas, <b>balanced</b> sits in between, <b>precise</b> is short and to the point.</li>
</ul>
<h3>What Mico can do</h3>
<ul>
<li>Open apps, folders and websites; find files.</li>
<li>Change volume, brightness and the Windows theme; take screenshots.</li>
<li>Set timers, alarms and reminders, keep a calendar.</li>
<li>Tell the weather, search the web, play videos.</li>
<li>Talk by voice: speech recognition and speech run on your PC.</li>
<li>Remember the conversation and tell you what you were doing (“what was I doing an hour ago?”).</li>
</ul>
<h3>Quick actions</h3>
<p>In an empty chat Mico suggests what you do most often: commands you ask for at this time of day and the apps you used most over the last two weeks. Turn it off in “Settings → Conversation → Quick actions”.</p>
<h3>Safety</h3>
<p>Actions that change your system (shutdown, services, PowerShell, deleting) run only after you say “yes”.</p>
<h3>Important</h3>
<p>Answers are written by AI and can be wrong. Double-check what matters: numbers, dates, and advice on health, money or law.</p>
"""),
    "terms": ("Terms of use", """
<h3>1. License</h3>
<p>Mico AI is distributed under the <b>MIT</b> license (see LICENSE). You may use, copy and modify it for free. It is provided “as is”, without warranty; the author is not liable for damage caused by its use.</p>
<h3>2. AI answers</h3>
<p>Answers are generated by an AI model and may be inaccurate or outdated. Do not use them instead of advice from a doctor, lawyer or financial professional.</p>
<h3>3. Actions on your PC</h3>
<p>Mico acts on your requests. It asks for “yes” before risky actions, and you are responsible for the commands you confirm. Agent mode is in BETA and off by default.</p>
<h3>4. Not allowed</h3>
<p>Do not use Mico for illegal activity, bypassing security, accessing other people’s data or sending spam.</p>
<h3>5. Third-party services</h3>
<p>If you use Mico Cloud, web search (DuckDuckGo, YouTube) or weather (Open-Meteo), their own terms apply too.</p>
<h3>6. Updates</h3>
<p>Once a day Mico checks GitHub for a new version. You can turn this off in settings. These terms may change with new versions.</p>
"""),
    "privacy": ("Privacy statement", """
<p>Mico AI runs on your computer. It has no accounts or sign-up and sends no statistics to the developer.</p>
<h3>What is stored on your PC</h3>
<p>Everything is kept in <b>%APPDATA%\\Mico</b>.</p>
<ul>
<li><b>Chat history, command log, notes, reminders and calendar</b> are encrypted.</li>
<li><b>The window and app log</b> (which window was active and for how long) is encrypted with a Windows key (DPAPI) and Fernet. It powers “what was I doing?” and habit-based quick actions. Windows on your exclusion list are saved as “[hidden]”.</li>
<li><b>Facts about you.</b> Things you said yourself (“remember that…”) and habits repeated at least three times. Phrases about health, money, address, family and passwords are not saved.</li>
<li><b>Settings</b> (config.json) and startup logs are plain text; they contain no chats or passwords.</li>
<li><b>Screenshots</b> you asked for are saved in “Pictures\\Mico”.</li>
</ul>
<h3>What goes online</h3>
<p>Only what an enabled feature needs:</p>
<ul>
<li><b>Mico Cloud (Cloudflare)</b> — if you chose the cloud answer source: chat text and its short history are sent. Screenshots are never sent to the cloud.</li>
<li><b>Search</b> — the query text goes to DuckDuckGo or YouTube.</li>
<li><b>Weather</b> — coordinates go to Open-Meteo.</li>
<li><b>Version check</b> — a request for the latest release number to GitHub once a day.</li>
</ul>
<p>Voice is recognized and spoken on your PC; audio is not recorded.</p>
<h3>Managing your data</h3>
<ul>
<li>“Settings → Data”: how long history is kept and “What Mico AI knows”, where you can delete entries.</li>
<li>Say “what do you know about me”, “forget fact N” or “forget everything about me”.</li>
<li>Habit-based quick actions can be turned off in “Settings → Conversation”.</li>
<li>Uninstalling can also erase all data if you tick it in the uninstaller.</li>
</ul>
<p>The full text is in PRIVACY.md in the program folder.</p>
"""),
}


def page(kind):
    """(заголовок, HTML) для «about», «terms» или «privacy» на языке интерфейса."""
    pages = EN if getattr(i18n, "LANG", "ru") == "en" else RU
    title, body = pages.get(kind, pages["about"])
    return title, _CSS + body

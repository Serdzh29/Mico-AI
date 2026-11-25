/* Настройки сайта Mico AI. Меняется только этот файл: новая версия, ссылка на загрузку, список выпусков.
   Номер версии в "version" должен совпадать с version.json: именно его проверяет сама программа при каждом запуске. */
window.MICOSITE = {
  version: 2513,
  /* Откуда скачивается программа. Сейчас: файл Mico.exe лежит рядом с сайтом.
     Если он хранится в другом месте (облако, хранилище R2, GitHub), впиши сюда полный адрес, например "https://…/Mico.exe". */
  download: "https://github.com/Serdzh29/Mico-AI/releases/latest/download/Mico.exe",
  /* Все выпуски: сверху самый новый. Для каждого можно указать свою ссылку url; нет ссылки: берётся download. */
  releases: [
    { version: 2513, date: "2026-11-23", current: true,
      ru: ["Mico Cloud: 16 лучших ИИ-моделей в трёх уровнях Lite, Plus и Max и режим «Авто», показ остатка нейронов и запросов, без ключей и без нагрузки на процессор",
           "В первой настройке можно по-настоящему задать вопрос Mico Cloud и увидеть, какая модель ответила",
           "Зима: снег в настройках и чате, сугробы, ёлки, снеговик, снежные значки и красный колпак с живым помпоном на Mico",
           "Рука в первой настройке тычет прямо в Mico, а он отзывается; новое оформление агента с плитками примеров",
           "Исправлено: при удалении не мигают окна терминала, кнопка «Закрыть» не меняет цвет при наведении"],
      en: ["Mico Cloud: 16 top AI models in three tiers Lite, Plus and Max plus Auto mode, with a live count of the neurons and requests left, no keys and no processor load",
           "In first-run setup you can really ask Mico Cloud a question and see which model answered",
           "Winter: snow in settings and chat, snowdrifts, fir trees, a snowman, snowy icons and a red hat with a live pompom on Mico",
           "In first-run setup the hand taps Mico himself and he reacts; a new agent look with example tiles",
           "Fixed: no terminal windows flash during uninstall, the Close button keeps its colour on hover"] },
    { version: 2512, date: "2026-11-22",
      ru: ["Новая первая настройка: выбор, где отвечает Mico (на компьютере или в облаке), и яркое знакомство с режимом агента",
           "Значок Mico в области уведомлений рядом с часами: нажми, чтобы открыть чат",
           "Проверка версии при запуске: если вышла новая, чат просит обновить Mico",
           "Агент аккуратнее ищет контакт в Telegram и MAX и просит проверить открытый чат",
           "Новые анимации разделов настроек, плавное переключение, круглые кнопки, настоящий значок Mico"],
      en: ["New first-run setup: choose where Mico answers (this PC or the cloud) and a bright introduction to agent mode",
           "Mico icon in the notification area next to the clock: click to open the chat",
           "Version check on launch: when a new version is out, the chat asks you to update Mico",
           "The agent finds contacts in Telegram and MAX more carefully and asks you to check the opened chat",
           "New settings animations, smooth section switching, round buttons, the real Mico icon"] }
  ]
};

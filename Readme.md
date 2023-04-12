Бот для отправки пиццы и приема платежей через Телеграм.

## Запуск бота локально
Для запуска бота на вашем сервере необходимо выполнить следующие действия:

1. Cоздать бота в Телеграмм  [см.тут](https://core.telegram.org/bots).
2. Инициализировать с вашим ботом чат.
3. Склонировать себе файлы репозитория выполнив команду **https://github.com/milov52/pizza_bot**.
4. Установить необходимы зависимости **pip install -r requirements.txt**.
5. В директории с проектом создать файл **.env** со следующим содержимом:
 ```
    CLIENT_ID=апра3jmMOxhZEXLAY5yhUMZ1MFOFTWQXCFPdIsv
    CLIENT_SECRET=12313
    TELEGRAM_TOKEN=536291вапрвар
    DATABASE_PASSWORD=fghfghjg6c55fJA
    DATABASE_HOST = fghjgfhjfghj
    DATABASE_PORT=13552
    GRANT_TYPE=client_credentials
    API_YANDEX_GEO_KEY=786f873c-64bf-4694-a6d3-1cf070b03c9d
    PAYMENT_TOKEN=401643678:TEST:4774330b-009e-4015-aeac-2e82633e0e6c
    PROMOTIONAL_MESSAGE=Какое то рекламное сообщение
    PROBLEM_MESSAGE=*Cообщение что делать если пицца не пришла*
    PAGE_ACCESS_TOKEN=123123
    VERIFY_TOKEN=123123
 ```
   - **CLIENT_ID** токен к CMS (В данном боте используется moltin)
   - **CLIENT_SECRET** секретный ключ для получения кода авторизации к CMS (В данном боте используется moltin)
   - **TELEGRAM_TOKEN** токен к вашему телеграмм боту
   - **DATABASE_HOST** хост к базе данных Redit
   - **DATABASE_PASSWORD** пароль Redis
   - **DATABASE_PORT** port Redis
   - **API_YANDEX_GEO_KEY** API key от Yandex Geocoder
   - **PAYMENT_TOKEN** Token вашей платежный системы для принятия платежей
   - **PROMOTIONAL_MESSAGE** Рекламное сообщение, которое посылается клиенту после 1 часа после оплаты
   - **PROBLEM_MESSAGE** Сообщение, которое посылается клиенту после 1 часа после оплаты 
   - **PAGE_ACCESS_TOKEN** Token для приложения в facebook
   - **VERIFY_TOKEN=123123** Проверочный token для авторизации приложения

6запустить бота **.\pizza_bot.py**

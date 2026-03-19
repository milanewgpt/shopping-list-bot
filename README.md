# Shopping List Telegram Bot

Telegram-бот для ведения списка покупок на русском языке.
Принимает голосовые и текстовые сообщения, извлекает товары, группирует по категориям, хранит в SQLite.

## Возможности

- Добавление товаров текстом или голосом
- Распознавание нескольких товаров в одном сообщении
- Автоматическая группировка по 11 категориям
- Защита от дублей
- Показ и очистка списка

## Переменные окружения

Создайте файл `.env` в корне проекта:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
OPENAI_API_KEY=sk-...
```

### Как получить TELEGRAM_BOT_TOKEN

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Следуйте инструкциям: задайте имя и username
4. Скопируйте полученный токен

### Как получить OPENAI_API_KEY

1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Перейдите в раздел API keys
3. Создайте новый ключ и скопируйте его

## Установка

```bash
# Клонируйте репозиторий или скопируйте файлы
cd shopping_list_bot

# Создайте виртуальное окружение
python -m venv venv

# Активируйте
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt

# Создайте .env и заполните токены
cp .env.example .env
```

## Запуск

```bash
python main.py
```

Бот работает в режиме long polling — не требует webhook или внешнего HTTP-сервера.

## Запуск на VPS

```bash
# Установите Python 3.11+, создайте venv, установите зависимости (см. выше)

# Простой запуск в фоне через nohup:
nohup python main.py > bot.log 2>&1 &

# Или через systemd (создайте /etc/systemd/system/shopping-bot.service):
# [Unit]
# Description=Shopping List Bot
# After=network.target
#
# [Service]
# WorkingDirectory=/path/to/shopping_list_bot
# ExecStart=/path/to/venv/bin/python main.py
# Restart=always
# User=youruser
#
# [Install]
# WantedBy=multi-user.target

# Затем:
# sudo systemctl enable shopping-bot
# sudo systemctl start shopping-bot
```

## Использование бота

### Добавление товаров

Просто напишите или надиктуйте:
- `молоко, хлеб, яблоки`
- `купи бананы и творог`
- `картошка, морковь, лук, курица`

### Показать список

- `/list`
- `покажи список`
- `что купить`

### Очистить список

- `/clear`
- `очисти список`
- `обнули список покупок`

### Справка

- `/start`
- `/help`

## Структура проекта

```
shopping_list_bot/
├── main.py              # Точка входа
├── bot/
│   ├── __init__.py
│   ├── config.py        # Конфигурация, env, логирование
│   ├── db.py            # SQLite хранилище
│   ├── categories.py    # Словарь категорий
│   ├── parsing.py       # Парсинг товаров, определение intent
│   ├── speech.py        # Транскрибация голоса через OpenAI
│   └── handlers.py      # Обработчики Telegram
├── .env.example
├── requirements.txt
└── README.md
```

## Категории товаров

Фрукты · Овощи · Молочка · Бакалея · Мясо · Рыба · Заморозка · Напитки · Хлеб · Сладкое · Прочее

# Математический Telegram-бот

Бот решает математические выражения и задачи с подробными объяснениями.

## Возможности

- **Арифметика:** `2 + 3 * 4`, `sqrt(144)`, `2^10`
- **Уравнения:** `x^2 - 4 = 0`, `2x + 5 = 0`
- **Производные:** `производная x^3` или `/diff x^3`
- **Интегралы:** `интеграл x^2` или `/integrate x^2`

Поддерживаются: sin, cos, tan, log, exp, pi, sqrt и др.

## Установка

1. Создай бота через [@BotFather](https://t.me/BotFather) в Telegram
2. Скопируй токен и создай файл `.env`:

```bash
cp .env.example .env
# Отредактируй .env и вставь свой TELEGRAM_BOT_TOKEN
```

3. Установи зависимости:

```bash
pip install -r requirements.txt
```

4. Запусти бота:

```bash
python bot.py
```

## Структура проекта

- `bot.py` — логика Telegram-бота
- `math_solver.py` — решение математики через SymPy
- `requirements.txt` — зависимости

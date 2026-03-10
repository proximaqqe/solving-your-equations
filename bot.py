"""
Telegram-бот для решения математических выражений и задач с объяснениями.
"""

import os
import logging
import tempfile
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

from math_solver import solve_math, _fix_ocr_math
from image_ocr import extract_text_from_image, is_ocr_available, get_ocr_error

# Загружаем токен из .env или .env.example
load_dotenv(".env")
if not os.getenv("TELEGRAM_BOT_TOKEN"):
    load_dotenv(".env.example")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Максимальная длина сообщения в Telegram
MAX_MESSAGE_LENGTH = 4000


def _truncate(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> str:
    """Обрезает текст до максимальной длины."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 50] + "\n\n... (сообщение обрезано)"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    welcome = """
🔢 <b>Математический бот</b>

Отправь мне любое математическое выражение или задачу — я решу её с подробным объяснением!

<b>Примеры:</b>
• <code>2 + 3 * 4</code> — арифметика
• <code>sqrt(144) + 2^5</code> — степени и корни
• <code>x^2 - 4 = 0</code> — уравнения
• <code>производная x^3</code> или <code>/diff x^3</code> — производная
• <code>интеграл x^2</code> или <code>/integrate x^2</code> — интеграл

• <b>Фото</b> — отправь скриншот или фото с примером, бот распознает и решит

Поддерживаются: +, -, *, /, ^, sqrt(), sin(), cos(), log(), exp(), pi и др.
"""
    await update.message.reply_text(welcome, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = """
📚 <b>Справка по командам</b>

<b>Выражения</b> — просто отправь выражение:
<code>(2+3)*4</code>, <code>2^10</code>, <code>sqrt(16)</code>, <code>sin(pi/2)</code>

<b>Уравнения</b> — используй знак =:
<code>x^2 - 5x + 6 = 0</code>, <code>2x + 1 = 7</code>

<b>Производная:</b> <code>/diff x^2</code> или <code>производная x^2</code>

<b>Интеграл:</b> <code>/integrate x^2</code> или <code>интеграл x^2</code>

<b>Символы:</b> π (pi), e (число Эйлера), x — переменная

<b>По фото:</b> отправь изображение с примером — бот распознает текст и решит
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


async def solve_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик математических сообщений."""
    if not update.message or not update.message.text:
        return
    user_text = update.message.text
    if not user_text or not user_text.strip():
        return

    # Показываем, что бот "печатает"
    await update.message.chat.send_action("typing")

    try:
        result, explanation = solve_math(user_text)

        if explanation:
            response = explanation
        else:
            from html import escape
            response = f"❌ Ошибка: {escape(str(result))}"

        response = _truncate(response)
        await update.message.reply_text(response, parse_mode="HTML")

    except Exception as e:
        logger.exception("Ошибка при решении: %s", e)
        await update.message.reply_text(
            f"❌ Произошла ошибка при решении. Проверьте правильность выражения.\n\n"
            f"Детали: {str(e)[:200]}"
        )


def _get_photo_file_id(update: Update):
    """Получает file_id фото (из message.photo или message.document)."""
    if not update.message:
        return None
    if update.message.photo:
        return update.message.photo[-1].file_id
    doc = update.message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        return doc.file_id
    return None


async def solve_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фото — OCR и решение."""
    file_id = _get_photo_file_id(update)
    if not file_id:
        return

    await update.message.chat.send_action("typing")

    if not is_ocr_available():
        from html import escape
        err = escape((get_ocr_error() or "неизвестная ошибка")[:300])
        await update.message.reply_text(
            "❌ OCR недоступен.\n\n"
            "Запусти <b>install.bat</b> для установки easyocr и pillow.\n"
            "Или вручную: <code>python -m pip install easyocr pillow</code>\n\n"
            f"Детали: {err}"
        )
        return

    try:
        file = await context.bot.get_file(file_id)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            path = tmp.name
        try:
            await file.download_to_drive(path)
            with open(path, "rb") as f:
                image_bytes = f.read()
        finally:
            os.unlink(path)

        text = extract_text_from_image(image_bytes)
        if not text or len(text.strip()) < 2:
            await update.message.reply_text(
                "❌ Не удалось распознать текст на изображении.\n\n"
                "Попробуй:\n"
                "• Фото с чётким, крупным текстом\n"
                "• Хорошее освещение, без бликов\n"
                "• Или напиши выражение вручную"
            )
            return

        # Исправляем OCR и решаем
        text = _fix_ocr_math(text)
        result, explanation = solve_math(text)

        if explanation:
            from html import escape
            text_preview = escape(text[:100]) + ("..." if len(text) > 100 else "")
            header = f"📷 <b>Распознано:</b> <code>{text_preview}</code>\n\n"
            response = header + explanation
        else:
            from html import escape
            response = f"📷 Распознано: <code>{escape(text[:100])}</code>\n\n❌ Ошибка: {escape(str(result))}"

        response = _truncate(response)
        await update.message.reply_text(response, parse_mode="HTML")

    except Exception as e:
        logger.exception("Ошибка при обработке фото: %s", e)
        await update.message.reply_text(
            f"❌ Ошибка при обработке фото. Попробуй другое изображение."
        )


def main() -> None:
    """Запуск бота."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: токен не найден!")
        print("Создай файл .env в папке проекта с содержимым:")
        print("  TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather")
        return

    # Убираем пробелы и кавычки на случай копипаста
    token = token.strip().strip('"').strip("'")

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, solve_photo))
    # Документы-изображения (когда юзер отправляет картинку как файл)
    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            solve_photo,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, solve_message)
    )

    if not is_ocr_available():
        print("ВНИМАНИЕ: OCR (распознавание фото) недоступен.")
        print("  Запусти install.bat для установки easyocr и pillow.")
    else:
        print("OCR включен — можно отправлять фото с примерами.")
    print()
    print("Бот запущен! Напиши боту в Telegram.")
    print("(Для остановки нажми Ctrl+C)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

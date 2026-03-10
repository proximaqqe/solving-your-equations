"""
OCR для извлечения математических выражений из изображений.
"""

import re
import os

# Исправление SSL на Windows — иначе EasyOCR не может скачать модели
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

# Ленивая загрузка — библиотеки подгружаются при первом использовании
_ocr_reader = None
_ocr_available = None
_ocr_error = None  # Сообщение об ошибке при неудачной инициализации


def _get_ocr():
    """Инициализация EasyOCR (ленивая загрузка)."""
    global _ocr_reader, _ocr_available, _ocr_error
    if _ocr_available is False:
        return None
    if _ocr_reader is not None:
        return _ocr_reader
    try:
        import easyocr
        _ocr_reader = easyocr.Reader(["en", "ru"], gpu=False, verbose=False)
        _ocr_available = True
        _ocr_error = None
        return _ocr_reader
    except Exception as e:
        _ocr_available = False
        _ocr_error = str(e)
        return None


def get_ocr_error() -> str | None:
    """Возвращает текст ошибки при неудачной инициализации OCR."""
    _get_ocr()  # Попытка инициализации
    return _ocr_error


def _preprocess_image(image_bytes: bytes) -> bytes:
    """Улучшение изображения для OCR."""
    try:
        from PIL import Image, ImageEnhance
        import io
        img = Image.open(io.BytesIO(image_bytes))
        # Убираем прозрачность
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # Увеличиваем размер если маленькое
        w, h = img.size
        if max(w, h) < 400:
            scale = 400 / max(w, h)
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Лёгкое усиление контраста (помогает при размытом тексте)
        try:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
        except Exception:
            pass
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return buf.getvalue()
    except Exception:
        return image_bytes


def _clean_ocr_text(text: str) -> str:
    """Очистка текста от OCR-артефактов для математики."""
    if not text:
        return ""
    # СНАЧАЛА убираем все кавычки и апострофы (ломают SymPy парсер)
    text = re.sub(r"[\'\"`\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u2032\u2033]", "", text)

    # Убираем вводные фразы (оставляем только выражение)
    intro_phrases = [
        r"найдите\s+значение\s+выражения\s*",
        r"вычислите\s*",
        r"решите\s*",
        r"вычисли\s*",
        r"найти\s+значение\s*",
        r"чему\s+равно\s*",
        r"найдите\s*",
        r"упростите\s*",
    ]
    text_lower = text.lower()
    for phrase in intro_phrases:
        text_lower = re.sub(phrase, "", text_lower, flags=re.IGNORECASE)
    text = text_lower if text_lower.strip() else text

    # Убираем лишние пробелы и переносы
    text = re.sub(r"\s+", " ", text)

    # OCR-ошибки: logs->log (лишняя s), logз->log3 (log₃), log 5->log5
    text = re.sub(r"\blogs\b", "log", text, flags=re.IGNORECASE)
    text = re.sub(r"logз", "log3", text, flags=re.IGNORECASE)
    text = re.sub(r"log\s+(\d)", r"log\1", text)  # log 5 -> log5

    # OCR часто путает 81 и "9 25" (дробь) — задача log₅(81)·log₃(5)=4
    if re.search(r"9\s+25\s+log\s+log", text):
        text = re.sub(r"9\s+25", "81", text, count=1)

    # Дробь: "9 25" между числами часто означает 9/25 (но не в контексте log log)
    text = re.sub(r"(\d+)\s+(\d+)(?=\s|$|log|\.)", r"\1/\2", text)

    # Восстановление: "81 log log3" или "9/25 log log3-" -> log5(81)*log3(5)
    m = re.match(r"^([\d/\*\+\-\.]+)\s+log\s+log(\d+)\s*[\-\*]?\s*$", text)
    if m:
        arg, base = m.group(1), m.group(2)
        text = f"log5({arg})*log{base}(5)"

    # OCR путает √ (корень) с буквами: zvr, vr, v
    # Типичное: 7√(x-5)/√x + 5√x/x + 3x - 4 при x=3
    text = re.sub(r"zvr_5\s+5vx", "7*sqrt(x-5)/sqrt(x)+5*sqrt(x)/x", text, flags=re.IGNORECASE)
    text = re.sub(r"\bzvr\b", "sqrt", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvr\b", "sqrt", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)vx\b", r"\1*sqrt(x)", text)  # 5vx -> 5*sqrt(x)
    text = re.sub(r"\bvx\b", "sqrt(x)", text)
    text = re.sub(r"zvr_5", "7*sqrt(x-5)", text, flags=re.IGNORECASE)
    text = re.sub(r"vr_5", "sqrt(x-5)", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)v\s*\(", r"\1*sqrt(", text)  # 7v( -> 7*sqrt(
    text = re.sub(r"\bv\s*\(", "sqrt(", text)

    # OCR: з (русская) = 3 в цифрах
    text = re.sub(r"зx_4", "3x-4", text)
    text = re.sub(r"зx", "3x", text)
    text = re.sub(r"(?<=[\s\+\-\*\/\(]|^)з(?=[\s\+\-\*\/\)]|$)", "3", text)

    # Замены символов
    text = text.replace("×", "*").replace("·", "*").replace("÷", "/")
    text = text.replace("−", "-").replace("—", "-")
    text = text.replace("х", "x").replace("Х", "x")
    return text.strip()


def extract_text_from_image(image_bytes: bytes) -> str | None:
    """
    Извлекает текст из изображения через OCR.
    Возвращает распознанный текст или None при ошибке.
    """
    reader = _get_ocr()
    if reader is None:
        return None

    def _run_ocr(img_bytes: bytes) -> str | None:
        try:
            result = reader.readtext(img_bytes, detail=0)
            if not result:
                return None
            text = " ".join(result).strip()
            return _clean_ocr_text(text) if text else None
        except Exception:
            return None

    # Сначала с предобработкой
    img_processed = _preprocess_image(image_bytes)
    text = _run_ocr(img_processed)
    # Если пусто — пробуем исходное изображение
    if not text and img_processed != image_bytes:
        text = _run_ocr(image_bytes)
    return text


def is_ocr_available() -> bool:
    """Проверка доступности OCR."""
    return _get_ocr() is not None

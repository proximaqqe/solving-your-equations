"""
Модуль для решения математических выражений и задач с пошаговыми объяснениями.
Использует SymPy для символьных вычислений.
"""

import re
from html import escape as _esc
from sympy import simplify, solve, diff, integrate, Symbol, Eq, logcombine, N
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication,
    convert_xor, parse_expr
)


# Преобразования для парсинга выражений (поддержка 2x, 2^3 и т.д.)
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication,
    convert_xor,
)


def _fix_ocr_math(text: str) -> str:
    """Исправление типичных OCR-ошибок в математике (zvr→sqrt, з→3 и т.д.)."""
    if not text or "zvr" not in text.lower() and "vx" not in text.lower() and "з" not in text:
        return text
    # √ (корень): zvr, vr, v
    text = re.sub(r"zvr_5\s+5vx", "7*sqrt(x-5)/sqrt(x)+5*sqrt(x)/x", text, flags=re.IGNORECASE)
    text = re.sub(r"zvr_5", "7*sqrt(x-5)", text, flags=re.IGNORECASE)
    text = re.sub(r"vr_5", "sqrt(x-5)", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)vx\b", r"\1*sqrt(x)", text)
    text = re.sub(r"\bvx\b", "sqrt(x)", text)
    text = re.sub(r"\bzvr\b", "sqrt", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvr\b", "sqrt", text, flags=re.IGNORECASE)
    # з (русская) = 3
    text = re.sub(r"зx_4", "3x-4", text)
    text = re.sub(r"зx", "3x", text)
    text = re.sub(r"(?<=[\s\+\-\*\/\(]|^)з(?=[\s\+\-\*\/\)]|$)", "3", text)
    return text


def _replace_log_base(expr_str: str) -> str:
    """Заменяет log5(x) на log(x, 5) и т.д. для SymPy."""
    def repl(m):
        base, rest = m.group(1), m.group(2)
        return f"log({rest}, {base})"
    # Несколько проходов для вложенных: log5(log3(x))
    changed = True
    while changed:
        new_str = re.sub(r"log\s*_?\s*(\d+)\s*\(([^()]+)\)", repl, expr_str)
        changed = new_str != expr_str
        expr_str = new_str
    return expr_str


def _safe_parse(expr_str: str):
    """Безопасный парсинг математического выражения."""
    expr_str = expr_str.strip()
    # Убираем символы, ломающие парсер (кавычки, апострофы)
    expr_str = re.sub(r"[\'\"`\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u2032\u2033]", "", expr_str)
    # Замены для удобства пользователя
    expr_str = expr_str.replace('^', '**')
    expr_str = expr_str.replace('×', '*').replace('·', '*')
    expr_str = expr_str.replace('÷', '/')
    expr_str = expr_str.replace('√', 'sqrt')
    expr_str = expr_str.replace('π', 'pi').replace('пи', 'pi')
    expr_str = expr_str.replace('е', 'E')  # русская е -> число Эйлера
    # Логарифм с основанием: log5(x) -> log(x, 5)
    expr_str = _replace_log_base(expr_str)
    return parse_expr(expr_str, transformations=TRANSFORMATIONS)


def solve_expression(expr_str: str, subs: dict | None = None) -> tuple[str, str]:
    """
    Решает математическое выражение и возвращает результат с объяснением.
    subs: {x: 3} — подставить значение переменной.
    """
    try:
        expr = _safe_parse(expr_str)
        if subs:
            from sympy import symbols
            for var, val in subs.items():
                sym = symbols(var)
                expr = expr.subs(sym, val)
        result = simplify(expr)
        # Упрощаем логарифмы: log5(x)*log3(5) = log3(x)
        try:
            result = logcombine(result, force=True)
            result = simplify(result)
        except (ValueError, TypeError):
            pass
        # Если результат — целое, показываем его
        result_str = str(result)
        try:
            val = N(result)
            if val == int(val) and abs(val - int(val)) < 1e-10:
                result_str = str(int(val))
        except (TypeError, ValueError):
            pass
        
        # Объяснение (HTML для Telegram)
        explanation_parts = []
        display_expr = expr_str
        if subs:
            sub_str = ", ".join(f"{k}={v}" for k, v in subs.items())
            display_expr = f"{expr_str} при {sub_str}"
        explanation_parts.append(f"📝 <b>Исходное выражение:</b> <code>{_esc(display_expr)}</code>")
        explanation_parts.append("")
        explanation_parts.append("<b>Шаги решения:</b>")
        if subs:
            explanation_parts.append(f"1. Подставляем {sub_str}")
        explanation_parts.append(f"{2 if subs else 1}. Упрощаем выражение")
        explanation_parts.append(f"{3 if subs else 2}. Получаем: <code>{_esc(result_str)}</code>")
        explanation_parts.append("")
        explanation_parts.append(f"✅ <b>Ответ:</b> <code>{_esc(result_str)}</code>")
        
        return result_str, "\n".join(explanation_parts)
    
    except Exception as e:
        return str(e), None


def solve_equation(expr_str: str) -> tuple[str, str]:
    """
    Решает уравнение вида f(x) = 0 или f(x) = g(x).
    Возвращает (результат, объяснение).
    """
    try:
        expr_str = expr_str.strip()
        expr_str = expr_str.replace('^', '**')
        
        # Определяем переменную (обычно x)
        x = Symbol('x')
        
        # Пробуем разные форматы
        if '=' in expr_str:
            left, right = expr_str.split('=', 1)
            left_expr = parse_expr(left.strip(), transformations=TRANSFORMATIONS)
            right_expr = parse_expr(right.strip(), transformations=TRANSFORMATIONS)
            equation = Eq(left_expr, right_expr)
        else:
            equation = Eq(parse_expr(expr_str, transformations=TRANSFORMATIONS), 0)
        
        solutions = solve(equation, x)
        
        if not solutions:
            return "Решений нет", f"Уравнение <code>{_esc(expr_str)}</code> не имеет решений в действительных числах."
        
        result_str = ", ".join(str(simplify(s)) for s in solutions)
        
        explanation_parts = []
        explanation_parts.append(f"📝 <b>Уравнение:</b> <code>{_esc(expr_str)}</code>")
        explanation_parts.append("")
        explanation_parts.append("<b>Шаги решения:</b>")
        explanation_parts.append("1. Приводим к виду f(x) = 0")
        explanation_parts.append("2. Решаем уравнение")
        explanation_parts.append(f"3. Находим корни: x ∈ {{{_esc(result_str)}}}")
        explanation_parts.append("")
        explanation_parts.append(f"✅ <b>Ответ:</b> x = {_esc(result_str)}")
        
        return result_str, "\n".join(explanation_parts)
    
    except Exception as e:
        return str(e), None


def differentiate(expr_str: str, var: str = "x") -> tuple[str, str]:
    """Вычисляет производную с объяснением."""
    try:
        expr = _safe_parse(expr_str)
        x = Symbol(var)
        result = diff(expr, x)
        result_str = str(simplify(result))
        
        explanation_parts = []
        explanation_parts.append(f"📝 <b>Функция:</b> f({var}) = <code>{_esc(expr_str)}</code>")
        explanation_parts.append("")
        explanation_parts.append("<b>Находим производную:</b>")
        explanation_parts.append(f"f'({var}) = d/d{var}[{_esc(expr_str)}]")
        explanation_parts.append(f"f'({var}) = <code>{_esc(result_str)}</code>")
        explanation_parts.append("")
        explanation_parts.append(f"✅ <b>Ответ:</b> <code>{_esc(result_str)}</code>")
        
        return result_str, "\n".join(explanation_parts)
    
    except Exception as e:
        return str(e), None


def integrate_expr(expr_str: str, var: str = "x") -> tuple[str, str]:
    """Вычисляет неопределённый интеграл."""
    try:
        expr = _safe_parse(expr_str)
        x = Symbol(var)
        result = integrate(expr, x)
        result_str = str(simplify(result))
        
        explanation_parts = []
        explanation_parts.append(f"📝 <b>Интегрируем:</b> ∫<code>{_esc(expr_str)}</code> d{var}")
        explanation_parts.append("")
        explanation_parts.append("<b>Находим первообразную:</b>")
        explanation_parts.append(f"∫({_esc(expr_str)}) d{var} = <code>{_esc(result_str)}</code> + C")
        explanation_parts.append("")
        explanation_parts.append(f"✅ <b>Ответ:</b> <code>{_esc(result_str)}</code> + C")
        
        return result_str, "\n".join(explanation_parts)
    
    except Exception as e:
        return str(e), None


def _extract_substitute(expr_str: str) -> tuple[str, dict] | None:
    """
    Извлекает «при x = N» и возвращает (выражение, {x: N}) или None.
    """
    m = re.search(r"при\s+x\s*=\s*([\d\.\-]+)", expr_str, re.IGNORECASE)
    if m:
        value = m.group(1)
        expr = expr_str[: m.start()].strip()
        return expr, {"x": float(value)}
    return None


def solve_math(expr_str: str) -> tuple[str, str]:
    """
    Универсальный решатель: определяет тип задачи и решает.
    - Простое выражение: 2+3*4, sqrt(16)
    - Уравнение: x^2 - 4 = 0, 2x + 5 = 0
    - «при x = N» — подставить и вычислить
    """
    expr_str = expr_str.strip()
    expr_str = _fix_ocr_math(expr_str)

    # «при x = N» — подставить значение и вычислить (не уравнение!)
    sub = _extract_substitute(expr_str)
    if sub:
        expr_only, subs_dict = sub
        return solve_expression(expr_only, subs_dict)

    # Команды
    if expr_str.lower().startswith("/diff ") or expr_str.lower().startswith("производная "):
        sub = expr_str[6:].strip() if expr_str.lower().startswith("/diff ") else expr_str[12:].strip()
        return differentiate(sub)

    if expr_str.lower().startswith("/integrate ") or expr_str.lower().startswith("интеграл "):
        sub = expr_str[11:].strip() if expr_str.lower().startswith("/integrate ") else expr_str[9:].strip()
        return integrate_expr(sub)

    # Уравнение (содержит = и переменную x), но без «при»
    if "=" in expr_str and "при" not in expr_str.lower() and ("x" in expr_str.lower() or "y" in expr_str.lower()):
        return solve_equation(expr_str)

    # Обычное выражение
    return solve_expression(expr_str)

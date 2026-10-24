"""Дизайн-токены Mico AI: один источник для цветов, скруглений, отступов, шрифтов и движения.

Все окна (чат, настройки, голос, мастер установки и удаления) берут значения отсюда,
чтобы выглядеть одинаково. Цвета поверхностей — в theme.fluent(), здесь — всё остальное.
"""

# Скругления: 6 — кнопки и поля, 8 — карточки поменьше, 12 — крупные карточки и окна.
RADIUS = {"hair": 2, "s": 6, "m": 8, "l": 12, "pill": 11}

# Отступы: шкала 4/8/12/16/24/32 px.
SPACE = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}

# Размеры текста, px: подпись, основной, крупный, заголовок, экран.
TYPE = {"caption": 11, "body": 13, "body_l": 14, "title": 20, "display": 26}

# Движение, мс. Всё короче 320 мс; ease-out для появления, ease-in-out для переключений.
MOTION = {"fast": 150, "base": 220, "slow": 320}

# Минимальный контраст текста на акценте (WCAG AA для обычного текста).
MIN_CONTRAST = 4.5


def accent_hover(hex_color, dark):
    """Акцент для наведения: чуть светлее в тёмной теме, чуть темнее в светлой."""
    from intel import hex_rgb
    r, g, b = hex_rgb(hex_color)
    k = 0.10 if dark else -0.08
    f = lambda c: max(0, min(255, round(c + (255 - c) * k if k > 0 else c * (1 + k))))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"


def contrast_ratio(fg_hex, bg_hex):
    """Контраст по WCAG между двумя цветами."""
    from intel import hex_rgb

    def lum(hex_color):
        out = []
        for c in hex_rgb(hex_color):
            c = c / 255
            out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = out
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    a, b = lum(fg_hex), lum(bg_hex)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)

"""KEEPER — Design System centralizado.

Fonte única de verdade para cores, tipografia, espaçamentos, raios,
sombras e componentes reutilizáveis (botões, inputs, cards, pills,
topbars, navegação, diálogos e estados).

Paleta oficial do produto (claro, corporativo, minimalista).
Os nomes históricos (OLIVE, BEIGE, BROWN...) são mantidos como aliases
para compatibilidade com as três visões do app.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import flet as ft

# Logging técnico (INFO / WARNING / ERROR). Nunca exibir stack ao usuário.
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s %(message)s")
log = logging.getLogger("keeper")

# ---------------------------------------------------------------------------
# Paleta oficial
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tipografia (Google Fonts: Poppins, embutida em assets/fonts) e ícones (Font Awesome 6 Free)
# ---------------------------------------------------------------------------
from fa_icons import FA as _FA

_Text, _Icon, _IconButton = ft.Text, ft.Icon, ft.IconButton
_FAMILIA = {"W_500": "Poppins Medium", "W_600": "Poppins SemiBold", "W_700": "Poppins Bold", "BOLD": "Poppins Bold",
            "W_800": "Poppins ExtraBold", "W_900": "Poppins ExtraBold"}
FONTS = {"Poppins": "/fonts/Poppins-Regular.ttf", "Poppins Medium": "/fonts/Poppins-Medium.ttf", "Poppins SemiBold": "/fonts/Poppins-SemiBold.ttf",
         "Poppins Bold": "/fonts/Poppins-Bold.ttf", "Poppins ExtraBold": "/fonts/Poppins-ExtraBold.ttf", "FA": "/fonts/fa-solid-900.ttf"}


class KText(_Text):
    """ft.Text com Poppins: o peso pedido vira o arquivo correto da família (sem negrito sintético)."""
    def __init__(self, *a, weight=None, font_family=None, **k):
        fam = font_family or _FAMILIA.get(getattr(weight, "name", str(weight or "")), "Poppins")
        super().__init__(*a, font_family=fam, weight=None, **k)


def _glifo(name):
    return _FA.get(str(getattr(name, "value", name) or "").lower())


def fa(name, size=18, color=None):
    """Ícone Font Awesome a partir do nome Material (ft.Icons.X) usado no projeto."""
    g = _glifo(name)
    return _Text(g, font_family="FA", size=size, color=color, no_wrap=True, text_align=ft.TextAlign.CENTER) if g else _Icon(name, size=size, color=color)


def _icon(name=None, color=None, size=None, **k):
    g = _glifo(name)
    if g:
        return _Text(g, font_family="FA", size=(size or 24) * 0.82, color=color, no_wrap=True, text_align=ft.TextAlign.CENTER, **{x: v for x, v in k.items() if x in ("opacity", "tooltip")})
    return _Icon(name, color=color, size=size, **k)


def _icon_button(icon=None, *a, **k):
    if _glifo(icon):
        c = k.pop("icon_color", None); sz = k.pop("icon_size", 20)
        return _IconButton(content=fa(icon, sz, c), *a, **k)
    return _IconButton(icon, *a, **k)


def _wrap_button(cls):
    class B(cls):
        def __init__(self, *a, **k):
            ic = k.get("icon"); txt = k.pop("text", None) if k.get("text") is not None else (a[0] if a and isinstance(a[0], str) else None)
            if _glifo(ic) and txt is not None:
                st = k.get("style"); col = (st.color if st is not None and st.color else PRIMARY)
                k.pop("icon"); a = a[1:] if a and isinstance(a[0], str) else a
                k["content"] = ft.Row([fa(ic, 16, col), KText(txt, color=col, weight=ft.FontWeight.W_600, size=14)], tight=True, spacing=9, alignment=ft.MainAxisAlignment.CENTER)
            elif txt is not None and "text" not in k and not (a and isinstance(a[0], str)):
                k["text"] = txt
            super().__init__(*a, **k)
    return B


ft.Text, ft.Icon, ft.IconButton = KText, _icon, _icon_button
ft.FilledButton, ft.OutlinedButton, ft.TextButton, ft.ElevatedButton = (_wrap_button(c) for c in (ft.FilledButton, ft.OutlinedButton, ft.TextButton, ft.ElevatedButton))

# Cores = nomes de TEMA do Flet. Os valores reais (claro/escuro) estão em LIGHT/DARK abaixo,
# então qualquer tela troca de tema na hora, sem reconstruir nada.
BG = "surface"                      # fundo da página
SURFACE = "surface_container_low"     # cards
SURFACE_2 = "surface_container_high"  # áreas de apoio
INK = "onsurface"                   # texto principal
TEXT = "onsurface"
MUTED = "onsurfacevariant"          # texto secundário
OLIVE = "primary"                   # botões / marca
OLIVE_DARK = "onprimarycontainer"
OLIVE_SOFT = "primarycontainer"     # badge/seleção (texto INK)
KHAKI = "secondary"                 # destaque areia
BEIGE = "secondarycontainer"
BROWN = "tertiary"
BROWN_SOFT = "tertiarycontainer"
GREEN = "#3F9A73"                   # sucesso (legível nos 2 temas)
RED = "#D0605A"                     # erro (legível nos 2 temas)
LINE = "outlinevariant"
WHITE = "#FFFFFF"
ON_PRIMARY = "onprimary"
SHADOW = "#0A0F0833"

LIGHT = dict(primary="#647332", on_primary="#FBF8EE", primary_container="#DCE3C2", on_primary_container="#2E401C",
             secondary="#BFAB67", on_secondary="#2E401C", secondary_container="#F0E6C4", tertiary="#AD8042", tertiary_container="#EADBC0",
             surface="#F4EFE0", on_surface="#1F2A14", on_surface_variant="#6B6E5C", surface_container_low="#FBF8EE",
             surface_container_high="#EBE4CF", outline_variant="#DDD5BC", error="#D0605A")
DARK = dict(primary="#6B7D36", on_primary="#F4EFE0", primary_container="#34431F", on_primary_container="#DCD7A8",
            secondary="#BFAB67", on_secondary="#1B2410", secondary_container="#3B3A22", tertiary="#D0A25E", tertiary_container="#3B3020",
            surface="#161D0D", on_surface="#EBE5CC", on_surface_variant="#A6A88F", surface_container_low="#212B15",
            surface_container_high="#2C3A1D", outline_variant="#38462B", error="#D0605A")
_THEME_FILE = Path(__file__).resolve().parent / "storage" / "theme.txt"


def saved_mode() -> str:
    try:
        return "dark" if _THEME_FILE.read_text().strip() == "dark" else "light"
    except OSError:
        return "light"


def apply_theme(page: ft.Page) -> None:
    """Define os dois temas (paleta do protótipo) e o modo salvo. Idempotente."""
    page.theme = ft.Theme(color_scheme=ft.ColorScheme(**LIGHT), use_material3=True)
    page.dark_theme = ft.Theme(color_scheme=ft.ColorScheme(**DARK), use_material3=True)
    page.theme_mode = ft.ThemeMode.DARK if saved_mode() == "dark" else ft.ThemeMode.LIGHT
    page.fonts = FONTS
    page.theme.font_family = page.dark_theme.font_family = "Poppins"
    page.bgcolor = BG
    page.padding = 0


def toggle_theme(page: ft.Page) -> None:
    novo = "light" if page.theme_mode == ft.ThemeMode.DARK else "dark"
    try:
        _THEME_FILE.parent.mkdir(exist_ok=True); _THEME_FILE.write_text(novo)
    except OSError:
        pass
    page.theme_mode = ft.ThemeMode.DARK if novo == "dark" else ft.ThemeMode.LIGHT
    page.update()


def theme_button():
    return icon_button(ft.Icons.BRIGHTNESS_6_OUTLINED, lambda e: toggle_theme(e.page), "Tema claro/escuro", MUTED)


# Aliases semânticos (preferir estes em código novo).
PRIMARY = OLIVE
PRIMARY_DARK = OLIVE_DARK
PRIMARY_SOFT = OLIVE_SOFT
ACCENT = KHAKI
ACCENT_SOFT = BEIGE
ACCENT_DARK = BROWN
SUCCESS = GREEN
ERROR = RED
BORDER = LINE
TEXT_SECONDARY = MUTED
SURFACE_ALT = SURFACE_2

# ---------------------------------------------------------------------------
# Tipografia (hierarquia única)
# ---------------------------------------------------------------------------
FS_DISPLAY = 27   # Display (títulos de entrada)
FS_TITLE = 24     # Títulos de tela grandes
FS_HEADING = 18   # Heading (cabeçalhos de seção/card)
FS_SUB = 15       # Subheading
FS_BODY = 13      # Body
FS_SMALL = 11     # Small
FS_CAPTION = 10   # Caption
FS_TINY = 9       # Micro labels

# ---------------------------------------------------------------------------
# Espaçamento (escala 4/8/12/16/20/24/32/40/48)
# ---------------------------------------------------------------------------
SP1, SP2, SP3, SP4, SP5, SP6, SP8, SP10, SP12 = 4, 8, 12, 16, 20, 24, 32, 40, 48

# ---------------------------------------------------------------------------
# Raios e sombra padrão
# ---------------------------------------------------------------------------
R_SM = 10
R_MD = 14
R_LG = 18
R_PILL = 20

CARD_SHADOW = ft.BoxShadow(blur_radius=18, color=SHADOW, offset=ft.Offset(0, 7))

BASE = Path(__file__).resolve().parent
LOGO = str(BASE / "assets" / "brand" / "logo-claro.png")
try:
    import base64 as _b64
    _LOGO_B64 = _b64.b64encode(open(LOGO, "rb").read()).decode()
except OSError:
    _LOGO_B64 = None


def init_page(page: ft.Page, title: str):
    page.title = title
    page.bgcolor = BG
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PRIMARY)
    page.window.min_width = 480
    page.window.min_height = 720
    page.scroll = ft.ScrollMode.AUTO


def notify(page: ft.Page, text: str, ok: bool = True):
    """Feedback visual global (sucesso/erro). Usa a API atual do Flet."""
    sb = ft.SnackBar(
        content=ft.Text(text, color=WHITE, size=FS_SMALL, weight=ft.FontWeight.W_600),
        bgcolor=SUCCESS if ok else ERROR,
        duration=3200,
        behavior=ft.SnackBarBehavior.FLOATING,
    )
    try:
        previous = getattr(page, "_keeper_snack", None)
        if previous is not None:
            try:
                page.close(previous)
            except Exception:
                pass
        page._keeper_snack = sb
        page.open(sb)
    except Exception:
        log.warning("notify falhou: %s", text)


def text_field(label: str, password: bool = False, value: str = "", hint: str | None = None, icon: str | None = None):
    return ft.TextField(
        label=label, value=value, hint_text=hint, password=password, can_reveal_password=password,
        prefix=ft.Container(fa(icon, 16, MUTED), padding=ft.padding.only(left=4, right=10)) if icon else None,
        border_radius=14, border_color=LINE, focused_border_color=PRIMARY, border_width=1, focused_border_width=1.8,
        filled=True, fill_color=SURFACE, text_size=FS_BODY, content_padding=ft.padding.symmetric(horizontal=16, vertical=15),
        text_style=ft.TextStyle(color=TEXT, font_family="Poppins"), label_style=ft.TextStyle(color=MUTED, font_family="Poppins", size=13),
        hint_style=ft.TextStyle(color=MUTED, font_family="Poppins"),
    )


def card(content, padding=SP4 + 2, width=None, on_click=None, bgcolor=SURFACE):
    return ft.Container(width=width, bgcolor=bgcolor, border=ft.border.all(1, LINE), border_radius=20, padding=padding,
                        shadow=ft.BoxShadow(blur_radius=24, spread_radius=-4, color=SHADOW, offset=ft.Offset(0, 8)),
                        content=content, on_click=on_click, ink=bool(on_click))


def pill(text: str, icon: str | None = None, bgcolor=PRIMARY_SOFT, color=INK):
    items = []
    if icon:
        items.append(ft.Icon(icon, size=13, color=color))
    items.append(ft.Text(text, size=FS_SMALL, weight=ft.FontWeight.W_700, color=color))
    return ft.Container(
        content=ft.Row(items, tight=True, spacing=SP1),
        bgcolor=bgcolor,
        border_radius=R_PILL,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )


def status_pill(text: str, ok: bool | None):
    """Badge de estado: True=sucesso, False=erro, None=neutro/aviso."""
    if ok is True:
        return pill(text, ft.Icons.CHECK_CIRCLE, PRIMARY_SOFT, INK)
    if ok is False:
        return pill(text, ft.Icons.CANCEL, BROWN_SOFT, BROWN)
    return pill(text, ft.Icons.SCHEDULE, ACCENT_SOFT, INK)


def _btn_row(text, icon, color):
    items = ([fa(icon, 16, color)] if icon else []) + [ft.Text(text, color=color, size=14, weight=ft.FontWeight.W_600)]
    return ft.Row(items, tight=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER)


def primary(text: str, callback, icon: str | None = None, width=None):
    return ft.FilledButton(content=_btn_row(text, icon, ON_PRIMARY), on_click=callback, width=width, height=54, style=ft.ButtonStyle(bgcolor=PRIMARY, color=ON_PRIMARY, overlay_color=PRIMARY_DARK, elevation=0, shape=ft.RoundedRectangleBorder(radius=14)))


def secondary(text: str, callback, icon: str | None = None, width=None):
    return ft.OutlinedButton(content=_btn_row(text, icon, PRIMARY_DARK), on_click=callback, width=width, height=54,
                             style=ft.ButtonStyle(color=PRIMARY_DARK, overlay_color=PRIMARY_SOFT, side=ft.BorderSide(1.4, LINE), shape=ft.RoundedRectangleBorder(radius=14)))


def icon_button(icon: str, callback, tooltip=None, color=INK):
    """Botão redondo com ícone Font Awesome (estilo do protótipo)."""
    return ft.Container(width=40, height=40, border_radius=20, bgcolor=SURFACE, border=ft.border.all(1, LINE), alignment=ft.alignment.center,
                        content=fa(icon, 15, color), on_click=callback, tooltip=tooltip, ink=True)


def busy_primary(text: str, label_busy: str = "Aguarde…", icon: str | None = None, width=None):
    """Botão primário com loading e proteção contra duplo clique. Retorna (botão, executar)."""
    label = ft.Text(text, color=ON_PRIMARY, size=14, weight=ft.FontWeight.W_600)
    btn = ft.FilledButton(content=ft.Row(([fa(icon, 16, ON_PRIMARY)] if icon else []) + [label], tight=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                          width=width, height=54, style=ft.ButtonStyle(bgcolor=PRIMARY, color=ON_PRIMARY, overlay_color=PRIMARY_DARK, elevation=0, shape=ft.RoundedRectangleBorder(radius=14)))

    def executar(callback):
        def handler(e):
            if btn.disabled:
                return
            btn.disabled = True
            label.value = label_busy
            try:
                page = getattr(e, "page", None)
                if page is not None:
                    page.update()
            except Exception:
                pass
            try:
                return callback(e)
            finally:
                try:
                    btn.disabled = False
                    label.value = text
                    if page is not None:
                        page.update()
                except Exception:
                    pass
        return handler

    return btn, executar


def topbar(title, subtitle=None, back=None, action=None):
    left = icon_button(ft.Icons.ARROW_BACK_IOS_NEW, back, "Voltar") if back else ft.Container(width=40)
    mid = ft.Column(
        [
            ft.Text(title, size=FS_HEADING, weight=ft.FontWeight.W_800, color=INK),
            ft.Text(subtitle, size=FS_CAPTION, color=MUTED) if subtitle else ft.Container(height=0),
        ],
        spacing=1,
        expand=True,
    )
    right = action if action else theme_button()
    return ft.Row([left, mid, right], vertical_alignment=ft.CrossAxisAlignment.CENTER)


def section_title(text: str):
    return ft.Text(text, size=FS_SUB, weight=ft.FontWeight.W_800, color=INK)


def empty_state(icon: str, title: str, message: str = ""):
    """Estado vazio padronizado para listas."""
    items = [
        ft.Icon(icon, size=32, color=MUTED),
        ft.Text(title, weight=ft.FontWeight.W_700, color=INK),
    ]
    if message:
        items.append(ft.Text(message, size=FS_CAPTION, color=MUTED, text_align=ft.TextAlign.CENTER))
    return card(ft.Column(items, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=SP1), padding=SP6)


try:
    import base64 as _b
    _MARK_B64 = _b.b64encode(open(Path(__file__).resolve().parent / "assets" / "brand" / "logo-marca.png", "rb").read()).decode()
except OSError:
    _MARK_B64 = None


def logo(small=False):
    """Marca K+carro com 'keeper' em texto (acompanha claro/escuro) e a tagline do produto."""
    w = 96 if small else 150
    return ft.Column(
        [
            ft.Container(theme_button(), alignment=ft.alignment.top_right, width=340),
            ft.Image(src_base64=_MARK_B64, width=w, fit=ft.ImageFit.CONTAIN),
            ft.Text("keeper", size=34 if small else 46, weight=ft.FontWeight.W_900, color=OLIVE_DARK, style=ft.TextStyle(letter_spacing=-1)),
            ft.Text("Intelligent Access System", size=11, color=MUTED, style=ft.TextStyle(letter_spacing=1.2)),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )


_FOTOS: dict = {}


def _foto_b64(path):
    if not path or not Path(path).exists():
        return None
    if path not in _FOTOS:
        import base64, io
        from PIL import Image
        im = Image.open(path).convert("RGB"); im.thumbnail((160, 160)); b = io.BytesIO(); im.save(b, "JPEG", quality=85)
        _FOTOS[path] = base64.b64encode(b.getvalue()).decode()
    return _FOTOS[path]


def avatar(nome: str, size=44, foto=None):
    """Foto do usuário em círculo (se houver); senão, iniciais."""
    b64 = _foto_b64(foto)
    if b64:
        return ft.Container(width=size, height=size, border_radius=size, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            border=ft.border.all(2, KHAKI), content=ft.Image(src_base64=b64, width=size, height=size, fit=ft.ImageFit.COVER))
    initials = "".join(x[0] for x in (nome or "?").split()[:2]).upper() or "U"
    return ft.CircleAvatar(radius=size / 2, bgcolor=PRIMARY_SOFT, content=ft.Text(initials, color=INK, weight=ft.FontWeight.W_800))


async def pulse_rings(page, rings, alive):
    """Animação do radar: os anéis crescem e esmaecem em loop enquanto alive() for verdadeiro."""
    big = False
    while alive():
        big = not big
        for k, r in enumerate(rings):
            r.scale = 1.0 + (0.28 + 0.22 * k if big else 0.0); r.opacity = 0.25 if big else 0.8
        try: page.update()
        except Exception: return
        await asyncio.sleep(1.1)


def radar(icon=ft.Icons.SENSOR_DOOR_OUTLINED, size=150):
    """Radar do 'Acesso detectado': 2 anéis animados + círculo central com ícone. Retorna (controle, anéis)."""
    anim = ft.Animation(1100, ft.AnimationCurve.EASE_IN_OUT)
    rings = [ft.Container(width=size, height=size, border_radius=size, border=ft.border.all(2, KHAKI), animate_scale=anim, animate_opacity=anim, scale=1.0, opacity=0.8) for _ in range(2)]
    core = ft.Container(width=size * 0.62, height=size * 0.62, border_radius=size, bgcolor=OLIVE_SOFT, alignment=ft.alignment.center,
                        content=ft.Icon(icon, size=size * 0.34, color=OLIVE_DARK))
    return ft.Container(width=size * 1.5, height=size * 1.5, alignment=ft.alignment.center, content=ft.Stack([ft.Container(r, alignment=ft.alignment.center) for r in rings] + [ft.Container(core, alignment=ft.alignment.center)], width=size * 1.5, height=size * 1.5)), rings


def shell(page: ft.Page, body, width=520, bottom=None):
    page.controls.clear()
    apply_theme(page)
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    try:
        viewport = page.window.width or page.width or 0
    except Exception:
        viewport = 0
    # Largura responsiva: nunca ultrapassa a janela (evita overflow/corte).
    content_w = max(300, min(width, (viewport - 40) if viewport else width, 820))
    content = ft.Container(
        width=content_w,
        expand=True,
        bgcolor=BG,
        content=ft.Column(
            [
                ft.Container(content=body, padding=SP4 + 2),
                bottom if bottom else ft.Container(height=SP2),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
    )
    page.add(ft.SafeArea(content=content, expand=True))
    page.update()


def bottom_nav(items, selected, callback):
    """Barra inferior flutuante: ícone + nome em todas as abas; a ativa fica em pílula verde-oliva (como no protótipo)."""
    controls = []
    for key, icon, label in items:
        active = key == selected
        cor = ON_PRIMARY if active else MUTED
        controls.append(ft.Container(
            expand=True, padding=ft.padding.symmetric(vertical=8), border_radius=18, bgcolor=PRIMARY if active else None,
            animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT), on_click=lambda e, k=key: callback(k), ink=True,
            content=ft.Column([fa(icon, 17, cor), ft.Text(label, size=9, weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500, color=cor, no_wrap=True)],
                              spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)))
    return ft.Container(margin=ft.margin.only(left=14, right=14, bottom=12, top=4), padding=ft.padding.symmetric(horizontal=6, vertical=6), bgcolor=SURFACE,
                        border=ft.border.all(1, LINE), border_radius=26, shadow=ft.BoxShadow(blur_radius=28, spread_radius=-6, color=SHADOW, offset=ft.Offset(0, 10)),
                        content=ft.Row(controls, spacing=2))


async def close_after(page: ft.Page, control, seconds: float):
    """Fecha um overlay após N segundos (uso com diálogos temporários)."""
    try:
        await asyncio.sleep(seconds)
        page.close(control)
    except Exception:
        pass


# ---------------- Imagens de carros (geradas, na cor e no tipo do veículo) ----------------
_CORES = {"preto": "#1d1f1c", "branco": "#f1efe8", "prata": "#b9bcbc", "cinza": "#7c807e", "vermelho": "#b3342c",
          "azul": "#2f5d8a", "verde": "#4f6b3a", "amarelo": "#d6b73a", "laranja": "#d2782c", "marrom": "#7b4618",
          "bege": "#c9b98a", "dourado": "#b8934a", "vinho": "#6d1f2c"}
_SUV = ("compass", "tiguan", "creta", "tracker", "hilux", "renegade", "t-cross", "tcross", "kicks", "duster", "suv", "sw4", "ranger", "pulse", "nivus")
_HATCH = ("gol", "onix", "polo", "hb20", "ka", "uno", "fox", "up", "mobi", "argo", "sandero", "fit", "kwid", "208", "celta", "palio")
_car_cache: dict = {}


def car_image(modelo: str | None, cor: str | None, width: int = 150) -> ft.Image:
    """Ilustração do carro: tipo (sedan/hatch/SUV) pelo modelo e cor pelo campo 'cor'."""
    import base64, io
    from PIL import Image, ImageDraw
    m, c = (modelo or "").lower(), (cor or "").lower()
    tipo = "suv" if any(k in m for k in _SUV) else "hatch" if any(k in m.split() or k == m for k in _HATCH) else "sedan"
    hexa = next((v for k, v in _CORES.items() if k in c), "#647332")
    key = (tipo, hexa)
    if key not in _car_cache:
        S = 4; W, H = 300 * S, 150 * S
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        P = lambda pts: [(x * S, y * S) for x, y in pts]
        sh = {"sedan": ([(20,100),(28,78),(90,70),(120,40),(200,40),(235,70),(280,78),(290,100)], [(100,70),(125,46),(165,46),(165,70)], [(172,70),(172,46),(198,46),(225,70)]),
              "hatch": ([(25,100),(30,75),(85,68),(110,38),(205,36),(255,60),(280,80),(285,100)], [(95,68),(115,44),(160,44),(160,68)], [(168,68),(168,44),(203,44),(240,68)]),
              "suv": ([(18,104),(24,70),(70,62),(100,30),(215,30),(255,58),(284,70),(290,104)], [(84,62),(105,36),(155,36),(155,62)], [(163,62),(163,36),(211,36),(245,62)])}[tipo]
        d.polygon(P(sh[0]), fill=hexa, outline="#2b2f28", width=S * 2)
        for w in sh[1:]: d.polygon(P(w), fill="#26332a")
        d.rectangle(P([(20, 96), (290, 106)]), fill="#1b1f1a")
        d.polygon(P([(262, 76), (282, 80), (284, 88), (262, 86)]), fill="#f3ecc6")
        for cx in (82, 232):
            d.ellipse(P([(cx-24, 84), (cx+24, 132)]), fill="#111"); d.ellipse(P([(cx-13, 95), (cx+13, 121)]), fill="#b9bcbc"); d.ellipse(P([(cx-4, 104), (cx+4, 112)]), fill="#444")
        im = im.resize((W // S, H // S), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "PNG"); _car_cache[key] = base64.b64encode(buf.getvalue()).decode()
    return ft.Image(src_base64=_car_cache[key], width=width, fit=ft.ImageFit.CONTAIN)



# ---------------- Componentes do protótipo: indicadores, passo a passo e moldura de câmera ----------------
def kpi_card(label: str, value, icon: str, accent=None):
    """Indicador do dashboard: número grande + legenda + ícone (grade 2×2 do protótipo). Ocupa metade da linha."""
    return ft.Container(
        expand=True, bgcolor=SURFACE, border=ft.border.all(1, LINE), border_radius=20, padding=16,
        shadow=ft.BoxShadow(blur_radius=24, spread_radius=-4, color=SHADOW, offset=ft.Offset(0, 8)),
        content=ft.Column([
            ft.Container(width=40, height=40, bgcolor=accent or OLIVE_SOFT, border_radius=14, alignment=ft.alignment.center, content=fa(icon, 17, OLIVE_DARK)),
            ft.Text(str(value), size=32, weight=ft.FontWeight.W_800, color=INK),
            ft.Text(label, size=11, color=MUTED),
        ], spacing=2))


def stepper(items):
    """Passo a passo horizontal (1 · 2 · 3) com linhas ligando as etapas.
    items = [(rótulo, detalhe, estado)] com estado em 'pending' | 'active' | 'done' | 'error'."""
    cols = []
    for i, (label, detail, state) in enumerate(items):
        done, active, err = state == "done", state == "active", state == "error"
        bg = GREEN if done else (RED if err else (PRIMARY if active else SURFACE_2))
        fg = WHITE if (done or err or active) else MUTED
        mark = fa(ft.Icons.CHECK, 15, fg) if done else (fa(ft.Icons.CLOSE, 15, fg) if err else ft.Text(str(i + 1), size=14, weight=ft.FontWeight.W_700, color=fg))
        circle = ft.Container(width=38, height=38, border_radius=19, bgcolor=bg, alignment=ft.alignment.center, content=mark,
                              border=ft.border.all(2, PRIMARY if active else bg))
        left = ft.Container(height=2, expand=True, bgcolor=(GREEN if done or (i > 0 and items[i - 1][2] == "done") else LINE) if i > 0 else None)
        right = ft.Container(height=2, expand=True, bgcolor=(GREEN if done else LINE) if i < len(items) - 1 else None)
        cols.append(ft.Column([
            ft.Row([left, circle, right], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700, color=INK, text_align=ft.TextAlign.CENTER),
            ft.Text(detail, size=9, color=MUTED, text_align=ft.TextAlign.CENTER, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ], spacing=4, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
    return card(ft.Row(cols, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START), padding=ft.padding.symmetric(horizontal=8, vertical=16))


def viewfinder(icon, size=132, color=None):
    """Moldura de câmera com 4 cantos (como a tela 'Aguardando veículo' do protótipo) e ícone no centro."""
    color = color or KHAKI; t, L, r = 3, 28, 12
    def corner(**pos):
        side = ft.BorderSide(t, color); b = {}
        b["top" if "top" in pos else "bottom"] = side; b["left" if "left" in pos else "right"] = side
        rad = {("top" if "top" in pos else "bottom") + "_" + ("left" if "left" in pos else "right"): r}
        return ft.Container(width=L, height=L, border=ft.border.only(**b), border_radius=ft.border_radius.only(**rad), **pos)
    return ft.Container(width=size, height=int(size * 0.82), content=ft.Stack([
        corner(top=0, left=0), corner(top=0, right=0), corner(bottom=0, left=0), corner(bottom=0, right=0),
        ft.Container(left=0, top=0, right=0, bottom=0, alignment=ft.alignment.center, content=fa(icon, 40, OLIVE_DARK)),
    ]))

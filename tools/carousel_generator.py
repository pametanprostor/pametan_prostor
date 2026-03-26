"""
Carousel generator: produces ready-to-upload Instagram PNG images (1080x1080px).
Output: tools/output/carousels/{slug}/slide-01.png, slide-02.png, ...
"""
import os
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

GOLD       = (201, 151, 58)
GOLD_DARK  = (140, 100, 30)
BG         = (9,   9,  11)
BG2        = (20,  20, 24)
WHITE      = (255, 255, 255)
GRAY       = (161, 161, 170)
GRAY_DIM   = (82,  82,  91)

SIZE   = 1080
PAD    = 80
FOOTER = 72


# ─────────────────────────────────────────────────────────────────
# FONT HELPERS
# ─────────────────────────────────────────────────────────────────

def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = {
        "serif":      ["PlayfairDisplay-Regular.ttf", "DejaVuSerif-Bold.ttf"],
        "sans":       ["Inter-Regular.ttf", "DejaVuSans-Regular.ttf"],
        "sans-bold":  ["DejaVuSans-Bold.ttf", "Inter-Regular.ttf"],
    }
    for fname in candidates.get(name, candidates["sans"]):
        path = os.path.join(FONTS_DIR, fname)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if font.getbbox(test)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def _draw_lines(draw, lines, font, color, x, y, spacing=1.25):
    lh = int(font.size * spacing)
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += lh
    return y


def _line_h(font, spacing=1.25) -> int:
    return int(font.size * spacing)


# ─────────────────────────────────────────────────────────────────
# BRAND ELEMENTS
# ─────────────────────────────────────────────────────────────────

def _draw_pp_logo(draw: ImageDraw.Draw, cx: int, cy: int, box_size: int = 44):
    """Draw the 4-square PP logo box centered at (cx, cy)."""
    x0 = cx - box_size // 2
    y0 = cy - box_size // 2
    r  = max(3, box_size // 10)

    # Gold background
    draw.rounded_rectangle([(x0, y0), (x0 + box_size, y0 + box_size)],
                            radius=r, fill=(*GOLD, 255))

    # 4 squares inside
    margin = max(2, box_size // 9)
    sq     = (box_size - margin * 3) // 2

    positions = [
        (x0 + margin,          y0 + margin,          255),   # TL full
        (x0 + margin*2 + sq,   y0 + margin,          140),   # TR dim
        (x0 + margin,          y0 + margin*2 + sq,   140),   # BL dim
        (x0 + margin*2 + sq,   y0 + margin*2 + sq,   255),   # BR full
    ]
    for px, py, a in positions:
        draw.rectangle([(px, py), (px + sq, py + sq)], fill=(*BG, a))


def _brand_header(draw: ImageDraw.Draw, site: dict, y_center: int = 58):
    """Draw centered logo + brand name at top of slide."""
    name_font = _font("serif", 22)
    name      = site["name"]  # "Pametan Prostor"

    logo_size = 44
    gap       = 14
    name_w    = name_font.getbbox(name)[2]
    name_h    = name_font.size

    total_w = logo_size + gap + name_w
    x0      = (SIZE - total_w) // 2

    _draw_pp_logo(draw, x0 + logo_size // 2, y_center)

    # "Pametan" in white, "Prostor" in gold
    parts = name.split(" ", 1)
    tx = x0 + logo_size + gap
    ty = y_center - name_h // 2 - 2
    draw.text((tx, ty), parts[0], font=name_font, fill=(*WHITE, 255))
    if len(parts) > 1:
        pw = name_font.getbbox(parts[0] + " ")[2]
        draw.text((tx + pw, ty), parts[1], font=name_font, fill=(*GOLD, 255))


def _brand_footer(draw: ImageDraw.Draw, site: dict):
    y0 = SIZE - FOOTER
    draw.rectangle([(0, y0), (SIZE, SIZE)], fill=(*BG, 255))
    draw.rectangle([(0, y0), (SIZE, y0 + 2)], fill=(*GOLD, 255))
    draw.text((PAD, y0 + 22), site["name"],
              font=_font("serif", 18), fill=(*GOLD, 255))
    url      = site["url"].replace("https://www.", "")
    url_font = _font("sans", 13)
    uw = url_font.getbbox(url)[2]
    draw.text((SIZE - PAD - uw, y0 + 26), url, font=url_font,
              fill=(*GRAY_DIM, 255))


def _slide_num(draw: ImageDraw.Draw, index: int, total: int):
    f = _font("sans", 13)
    t = f"{index}/{total}"
    w = f.getbbox(t)[2]
    draw.text((SIZE - PAD - w, 38), t, font=f, fill=(*GRAY_DIM, 200))


# ─────────────────────────────────────────────────────────────────
# IMAGE HELPERS
# ─────────────────────────────────────────────────────────────────

def _load_bg(image_path: str, root_dir: str) -> Image.Image | None:
    full = os.path.join(root_dir, image_path.lstrip("/"))
    if not os.path.exists(full):
        return None
    try:
        img  = Image.open(full).convert("RGBA")
        w, h = img.size
        side = min(w, h)
        img  = img.crop(((w - side)//2, (h - side)//2,
                          (w + side)//2, (h + side)//2))
        return img.resize((SIZE, SIZE), Image.LANCZOS)
    except Exception:
        return None


def _gradient(img: Image.Image, style="bottom-heavy") -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    g    = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(g)
    h    = img.height
    if style == "bottom-heavy":
        for y in range(h):
            t = y / h
            a = int(255 * (0.25 + 0.75 * t ** 1.3))
            draw.line([(0, y), (SIZE, y)], fill=(9, 9, 11, a))
    elif style == "full":
        for y in range(h):
            a = int(255 * (0.50 + 0.25 * (y / h)))
            draw.line([(0, y), (SIZE, y)], fill=(9, 9, 11, a))
    return Image.alpha_composite(img, g)


def _pick_slide_image(slide: dict, hero_image: str, root_dir: str) -> str:
    """Pick the best-matching image for a photo slide based on slide text."""
    text = (slide.get("headline", "") + " " + slide.get("body", "")
            + " " + slide.get("subtitle", "")).lower()

    images_dir = os.path.join(root_dir, "images")
    try:
        available = [f for f in os.listdir(images_dir)
                     if f.lower().endswith((".webp", ".png", ".jpg"))]
    except Exception:
        return hero_image

    # keyword → filename fragments
    rules = [
        (["bela", "belo", "krem", "svetl", "beli"], ["bela-ostrvo", "krem", "skandinavska"]),
        (["moderna", "modern"],                      ["moderna", "industrijska"]),
        (["klasicn", "klasik"],                      ["klasicna"]),
        (["skandinavsk"],                             ["skandinavska", "jasen"]),
        (["industrijska", "tamn", "antracit"],        ["industrijska"]),
        (["plakar", "ormar", "ugradni"],              ["plakar", "klizna", "walkin", "garderober"]),
        (["garderob", "walkin", "walk-in"],           ["walkin", "garderober"]),
        (["led", "osvetljenje", "svetlo"],            ["ugaoni-ormar-led", "walkin", "plakar"]),
        (["kuhinja", "kuhinje"],                      ["kuhinja", "kuhinje"]),
        (["radni sto", "homeoffice", "radna soba"],   ["homeoffice"]),
        (["tv", "komoda"],                            ["tv-jedinica"]),
        (["jasen", "hrast", "furnir", "drvo"],        ["jasen", "hrast"]),
    ]

    for keywords, img_fragments in rules:
        if any(kw in text for kw in keywords):
            for frag in img_fragments:
                for fname in available:
                    if frag in fname.lower():
                        return f"/images/{fname}"

    return hero_image


# ─────────────────────────────────────────────────────────────────
# SLIDE RENDERERS
# ─────────────────────────────────────────────────────────────────

HEADER_Y    = 58    # center-y of brand header
HEADER_ZONE = 110   # pixels reserved at top for header + breathing room
CONTENT_TOP = HEADER_ZONE + 10


def render_cover(slide: dict, hero_image: str, site: dict,
                 index: int, total: int, root_dir: str) -> Image.Image:
    bg = _load_bg(hero_image, root_dir)
    if bg:
        bg = _gradient(bg, "full")
    else:
        bg = Image.new("RGBA", (SIZE, SIZE), (*BG, 255))

    # Thin gold top bar
    top_bar = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(top_bar).rectangle([(0, 0), (SIZE, 4)], fill=(*GOLD, 255))
    bg = Image.alpha_composite(bg, top_bar)

    draw = ImageDraw.Draw(bg)
    _brand_header(draw, site, HEADER_Y)
    _slide_num(draw, index, total)

    headline  = slide.get("headline", "")
    subtitle  = slide.get("subtitle", "")
    h_font    = _font("serif", 88)
    sub_font  = _font("sans", 24)
    MAX_W     = SIZE - PAD * 2

    h_lines = _wrap(headline, h_font, MAX_W)
    s_lines = _wrap(subtitle, sub_font, MAX_W) if subtitle else []

    h_h = len(h_lines) * _line_h(h_font, 1.12)
    s_h = (len(s_lines) * _line_h(sub_font, 1.5) + 32) if s_lines else 0
    acc = 4 + 28  # accent line + gap

    total_h = acc + h_h + s_h
    y = SIZE - FOOTER - total_h - 72
    y = max(CONTENT_TOP, y)

    draw.rectangle([(PAD, y), (PAD + 52, y + 4)], fill=(*GOLD, 255))
    y += 4 + 28

    y = _draw_lines(draw, h_lines, h_font, (*WHITE, 255), PAD, y, 1.12)
    if s_lines:
        y += 32
        _draw_lines(draw, s_lines, sub_font, (*GRAY, 210), PAD, y, 1.5)

    _brand_footer(draw, site)
    return bg.convert("RGB")


def render_text(slide: dict, site: dict, index: int, total: int) -> Image.Image:
    img  = Image.new("RGBA", (SIZE, SIZE), (*BG, 255))
    draw = ImageDraw.Draw(img)

    # Gold top bar
    draw.rectangle([(0, 0), (SIZE, 4)], fill=(*GOLD, 255))

    _brand_header(draw, site, HEADER_Y)
    _slide_num(draw, index, total)

    # Thin separator under header
    draw.rectangle([(PAD, HEADER_ZONE - 4), (SIZE - PAD, HEADER_ZONE - 3)],
                   fill=(*GOLD_DARK, 80))

    tip_num  = slide.get("tip_number")
    headline = slide.get("headline", "")
    body     = slide.get("body", slide.get("subtitle", ""))

    lbl_font  = _font("sans-bold", 13)
    h_font    = _font("serif",     76)
    body_font = _font("sans",      28)

    MAX_W   = SIZE - PAD * 2
    h_lines = _wrap(headline, h_font, MAX_W)
    b_lines = _wrap(body, body_font, MAX_W) if body else []

    lbl_h   = 20 + 16 + 4 + 32       # label + gap + accent + gap
    h_h     = len(h_lines) * _line_h(h_font, 1.2)
    b_h     = (48 + len(b_lines) * _line_h(body_font, 1.65)) if b_lines else 0

    content_h = lbl_h + h_h + b_h

    usable_h  = (SIZE - FOOTER) - CONTENT_TOP
    y = CONTENT_TOP + max(0, (usable_h - content_h) // 2)

    # Tip label
    lbl = f"SAVET {tip_num}" if tip_num is not None else "PAMETAN PROSTOR"
    draw.text((PAD, y), lbl, font=lbl_font, fill=(*GOLD, 255))
    y += 20 + 16

    # Gold accent line
    draw.rectangle([(PAD, y), (PAD + 56, y + 4)], fill=(*GOLD, 255))
    y += 4 + 32

    y = _draw_lines(draw, h_lines, h_font, (*WHITE, 255), PAD, y, 1.2)

    if b_lines:
        y += 48
        _draw_lines(draw, b_lines, body_font, (*GRAY, 215), PAD, y, 1.65)

    _brand_footer(draw, site)
    return img.convert("RGB")


def render_photo(slide: dict, hero_image: str, site: dict,
                 index: int, total: int, root_dir: str) -> Image.Image:
    # Smart image selection based on slide content
    img_path = _pick_slide_image(slide, hero_image, root_dir)
    bg = _load_bg(img_path, root_dir)
    if bg:
        bg = _gradient(bg, "bottom-heavy")
    else:
        bg = Image.new("RGBA", (SIZE, SIZE), (*BG2, 255))

    draw = ImageDraw.Draw(bg)
    _brand_header(draw, site, HEADER_Y)
    _slide_num(draw, index, total)

    headline  = slide.get("headline", "")
    body      = slide.get("body", slide.get("subtitle", ""))
    h_font    = _font("serif", 62)
    body_font = _font("sans",  23)
    MAX_W     = SIZE - PAD * 2

    h_lines = _wrap(headline, h_font, MAX_W)
    b_lines = _wrap(body, body_font, MAX_W) if body else []

    h_h = len(h_lines) * _line_h(h_font, 1.18)
    b_h = (24 + len(b_lines) * _line_h(body_font, 1.55)) if b_lines else 0

    y = SIZE - FOOTER - h_h - b_h - 64
    y = max(CONTENT_TOP, y)

    y = _draw_lines(draw, h_lines, h_font, (*WHITE, 255), PAD, y, 1.18)
    if b_lines:
        y += 24
        _draw_lines(draw, b_lines, body_font, (*GRAY, 210), PAD, y, 1.55)

    _brand_footer(draw, site)
    return bg.convert("RGB")


def render_cta(slide: dict, site: dict, index: int, total: int) -> Image.Image:
    img  = Image.new("RGBA", (SIZE, SIZE), (*BG, 255))

    # Radial gold glow
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    cx, cy = SIZE // 2, SIZE // 2 + 60
    for r in range(500, 0, -2):
        a = int(22 * (1 - r / 500) ** 1.8)
        gd.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(*GOLD, a))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (SIZE, 4)], fill=(*GOLD, 255))
    _slide_num(draw, index, total)

    # Large centered PP logo
    logo_y = 130
    logo_size = 80
    _draw_pp_logo(draw, SIZE // 2, logo_y, logo_size)

    # Brand name below logo
    brand_font = _font("serif", 22)
    brand_text = site["name"]
    bw = brand_font.getbbox(brand_text)[2]
    bx = (SIZE - bw) // 2
    by = logo_y + logo_size // 2 + 20
    parts = brand_text.split(" ", 1)
    draw.text((bx, by), parts[0], font=brand_font, fill=(*WHITE, 255))
    if len(parts) > 1:
        pw = brand_font.getbbox(parts[0] + " ")[2]
        draw.text((bx + pw, by), parts[1], font=brand_font, fill=(*GOLD, 255))

    headline  = slide.get("headline", "")
    body      = slide.get("body", slide.get("subtitle",
                "Besplatna konsultacija. 3D projekat za 24 sata."))
    phone     = site.get("phone", "065 2262 308")

    h_font    = _font("serif",    68)
    body_font = _font("sans",     25)
    btn_font  = _font("sans-bold", 21)
    ph_font   = _font("sans-bold", 32)

    MAX_W   = SIZE - PAD * 2 + 40
    h_lines = _wrap(headline, h_font, MAX_W)
    b_lines = _wrap(body, body_font, MAX_W) if body else []

    h_h   = len(h_lines) * _line_h(h_font, 1.15)
    b_h   = (36 + len(b_lines) * _line_h(body_font, 1.6)) if b_lines else 0
    btn_h = 64
    ph_h  = 44

    content_h = h_h + b_h + 60 + btn_h + 32 + ph_h

    content_top = by + brand_font.size + 52
    usable      = SIZE - FOOTER - content_top
    y = content_top + max(0, (usable - content_h) // 2)

    # Headline
    for line in h_lines:
        lw = h_font.getbbox(line)[2]
        draw.text(((SIZE - lw) // 2, y), line, font=h_font, fill=(*WHITE, 255))
        y += _line_h(h_font, 1.15)

    # Body
    if b_lines:
        y += 36
        for line in b_lines:
            lw = body_font.getbbox(line)[2]
            draw.text(((SIZE - lw) // 2, y), line, font=body_font, fill=(*GRAY, 210))
            y += _line_h(body_font, 1.6)

    # Button
    y += 60
    btn_text = "Zatražite besplatnu konsultaciju"
    btn_tw   = btn_font.getbbox(btn_text)[2]
    btn_pw   = btn_tw + 80
    bx_btn   = (SIZE - btn_pw) // 2
    draw.rounded_rectangle([(bx_btn, y), (bx_btn + btn_pw, y + btn_h)],
                            radius=6, fill=(*GOLD, 255))
    draw.text((bx_btn + 40, y + (btn_h - btn_font.size) // 2 - 1),
              btn_text, font=btn_font, fill=(*BG, 255))
    y += btn_h + 32

    # Phone
    pw = ph_font.getbbox(phone)[2]
    draw.text(((SIZE - pw) // 2, y), phone, font=ph_font, fill=(*GOLD, 255))

    _brand_footer(draw, site)
    return img.convert("RGB")


# ─────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────

class CarouselGenerator:
    def __init__(self, config: dict):
        self.config   = config
        self.site     = config["site"]
        self.root_dir = os.path.join(os.path.dirname(__file__), "..")

    def generate(self, data: dict) -> str:
        slides     = data.get("carousel_slides", [])
        hero_image = data.get("hero_image", "/images/hero.webp")
        slug       = data["slug"]

        output_dir = os.path.join(
            os.path.dirname(__file__),
            self.config["paths"]["output"], "carousels", slug
        )
        os.makedirs(output_dir, exist_ok=True)

        # Filter out any non-dict items (Claude occasionally returns strings)
        slides = [s for s in slides if isinstance(s, dict)]
        total  = len(slides)

        for i, slide in enumerate(slides, 1):
            t = slide.get("type", "text")
            if t == "cover":
                img = render_cover(slide, hero_image, self.site, i, total, self.root_dir)
            elif t == "photo":
                img = render_photo(slide, hero_image, self.site, i, total, self.root_dir)
            elif t == "cta":
                img = render_cta(slide, self.site, i, total)
            else:
                img = render_text(slide, self.site, i, total)

            img.save(os.path.join(output_dir, f"slide-{i:02d}.png"), "PNG", optimize=True)

        caption_path = os.path.join(output_dir, "caption.txt")
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(data.get("instagram_caption", ""))

        print(f"  Carousel slike ({total} PNG): tools/output/carousels/{slug}/")
        for i in range(1, total + 1):
            print(f"    slide-{i:02d}.png")
        print(f"  Instagram caption: tools/output/carousels/{slug}/caption.txt")
        return output_dir

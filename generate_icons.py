"""
توليد أيقونات PNG من public/icons/icon.svg
═══════════════════════════════════════════════════════════════

كانت icon-192.png وicon-512.png ملفّ SVG واحداً بامتداد .png —
بصمتاهما تطابق icon.svg حرفياً. لا يقبلهما أي متجر ولا أداة تعبئة.

الاستعمال:
    python generate_icons.py

يكتب في public/icons/:
    icon-192.png              — "any"، مطابق للتصميم كما هو (زوايا مدوّرة)
    icon-512.png              — "any"، نفس الشيء
    icon-1024.png             — لأبل (App Store)، RGB بلا قناة شفافية
    icon-maskable-192.png     — أندرويد، منطقة أمان ٨٠٪ وخلفية ملء كامل
    icon-maskable-512.png     — نفس الشيء بحجم أكبر

ولماذا سكربت لا تنفيذ يدوي: الشعار قيد إعادة التصميم، وإعادة
التوليد بعد كل تعديل يجب أن تكون أمراً واحداً لا سلسلة خطوات.

يحتاج: pip install -r requirements-dev.txt && playwright install chromium
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

ICONS_DIR = Path(__file__).resolve().parent / "public" / "icons"
SRC_SVG = ICONS_DIR / "icon.svg"

STANDARD_SIZES = [192, 512]
APPLE_SIZE = 1024
MASKABLE_SIZES = [192, 512]

BG_COLOR = "#0d1117"       # نفس خلفية icon.svg — يُستعمل لملء منطقة الأمان
SAFE_ZONE_SCALE = 0.8      # المحتوى داخل ٨٠٪ الوسطى (معيار الأيقونة القابلة للقصّ)
VIEWBOX_SIZE = 192         # viewBox الأصلية في icon.svg


def _read_svg() -> str:
    if not SRC_SVG.exists():
        sys.exit(f"لا يوجد {SRC_SVG}")
    return SRC_SVG.read_text(encoding="utf-8")


def _svg_at_size(svg_markup: str, size: int) -> str:
    """نسخة من الـSVG الأصلي بأبعاد px = size (viewBox كما هو، لا تشويه)."""
    out = re.sub(r'width="\d+"', f'width="{size}"', svg_markup, count=1)
    out = re.sub(r'height="\d+"', f'height="{size}"', out, count=1)
    return out


def _maskable_svg(svg_markup: str, size: int) -> str:
    """
    نسخة قابلة للقصّ: خلفية مربّعة بلا زوايا مدوَّرة تملأ اللوحة
    كاملةً (نظام التشغيل يفرض قناعه هو)، والمحتوى الأصلي (بما فيه
    مستطيل الخلفية المدوَّرة القديم كزخرفة داخلية) مصغَّر إلى ٨٠٪
    ومُوسَّط، فلا يُقصّ عند القناع الدائري.
    """
    m = re.match(r"(<svg[^>]*>)(.*)</svg>\s*$", svg_markup, re.S)
    if not m:
        sys.exit("تعذّر تحليل بنية icon.svg — الشكل غير متوقَّع")
    open_tag, inner = m.group(1), m.group(2)
    open_tag = re.sub(r'width="\d+"', f'width="{size}"', open_tag, count=1)
    open_tag = re.sub(r'height="\d+"', f'height="{size}"', open_tag, count=1)

    c = VIEWBOX_SIZE / 2
    safe_group = (
        f'<g transform="translate({c},{c}) scale({SAFE_ZONE_SCALE}) translate({-c},{-c})">'
        f"{inner}</g>"
    )
    bg = f'<rect width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" fill="{BG_COLOR}"/>'
    return f"{open_tag}{bg}{safe_group}</svg>"


def _render_png(browser, svg_markup: str, size: int, out_path: Path) -> None:
    page = browser.new_page(viewport={"width": size, "height": size})
    page.set_content(
        f'<!doctype html><html><head><meta charset="utf-8">'
        f"<style>html,body{{margin:0;padding:0;background:transparent}}</style>"
        f"</head><body>{svg_markup}</body></html>"
    )
    page.locator("svg").screenshot(path=str(out_path))
    page.close()
    print(f"  + {out_path.relative_to(ICONS_DIR.parent.parent)}  ({size}×{size})")


def main() -> None:
    svg_markup = _read_svg()
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for size in STANDARD_SIZES:
            _render_png(browser, _svg_at_size(svg_markup, size), size,
                       ICONS_DIR / f"icon-{size}.png")

        for size in MASKABLE_SIZES:
            _render_png(browser, _maskable_svg(svg_markup, size), size,
                       ICONS_DIR / f"icon-maskable-{size}.png")

        # ١٠٢٤ لأبل — يُرسَم أولاً بشفافية ثم يُفرَّغ منها (RGBA→RGB)؛
        # App Store Connect يرفض أيقونة فيها قناة شفافية.
        tmp_apple = ICONS_DIR / "_icon-1024-rgba.png"
        _render_png(browser, _svg_at_size(svg_markup, APPLE_SIZE), APPLE_SIZE, tmp_apple)
        browser.close()

    with Image.open(tmp_apple) as im:
        rgb = Image.new("RGB", im.size, BG_COLOR)
        rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
        apple_out = ICONS_DIR / "icon-1024.png"
        rgb.save(apple_out, "PNG")
    tmp_apple.unlink()
    print(f"  + {apple_out.relative_to(ICONS_DIR.parent.parent)}  ({APPLE_SIZE}×{APPLE_SIZE}, RGB بلا شفافية)")

    print("\nتم. صفر ملف SVG بامتداد .png متبقٍّ — تحقّق:")
    for f in sorted(ICONS_DIR.glob("icon*.png")):
        head = f.read_bytes()[:8]
        ok = head.startswith(b"\x89PNG\r\n\x1a\n")
        print(f"  {'✓' if ok else '✗ ليس PNG!'} {f.name}  {len(f.read_bytes())} بايت")


if __name__ == "__main__":
    main()

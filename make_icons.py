# -*- coding: utf-8 -*-
"""
أيقونات بُنيان — مولَّدة من هندسة الشعار الرسمي مباشرةً (لا من صورة).

الإحداثيات أدناه مُستخرَجة من ملفّ الشعار الرسمي بالبكسل، ومُتحقَّق منها:
الرسم منها عند 1024 يطابق الملفّ الأصلي بكسلاً ببكسل (فرق أقصى = 0).
فهي الشعار نفسه، لا تقريباً له. لا تُعدَّل.

لا يحتاج أي مكتبة غير Pillow، ولا يحتاج ملفّ صورة مصدراً.
    python make_icons.py
"""
import math
import os
from PIL import Image, ImageDraw

# مساحة الشعار: 600 × 551 (ليس مربّعاً — هكذا هو الشعار الرسمي)
MARK_W, MARK_H = 600, 551
RECTS = [                       # x, y, w, h
    (0,   0,   363, 188),       # أعلى-يسار
    (387, 0,   213, 338),       # أعلى-يمين
    (0,   213, 213, 338),       # أسفل-يسار
    (238, 362, 362, 189),       # أسفل-يمين
]
FG, BG = (255, 255, 255), (0, 0, 0)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "public", "icons")


def render(size, scale, ss=8):
    """
    يرسم عند دقّة ss أضعاف ثم يُصغّر — وإلّا ابتُلعت الفواصل عند المقاسات
    الصغيرة (عند 32 بكسل الفاصل أقلّ من بكسل واحد).
    scale = نسبة عرض الشعار إلى ضلع المربّع. نِسَب الشعار محفوظة كما هي.
    """
    big = size * ss
    im = Image.new("RGB", (big, big), BG)
    d = ImageDraw.Draw(im)
    k = (big * scale) / MARK_W
    ox = math.ceil((big - MARK_W * k) / 2.0)
    oy = math.ceil((big - MARK_H * k) / 2.0)
    for x, y, w, h in RECTS:
        d.rectangle([round(ox + x * k), round(oy + y * k),
                     round(ox + (x + w) * k) - 1, round(oy + (y + h) * k) - 1], fill=FG)
    return im if ss == 1 else im.resize((size, size), Image.LANCZOS)


# (الاسم، المقاس، نسبة الشعار، السبب)
TARGETS = [
    ("icon-1024.png",        1024, 0.586, "الإطار الرسمي كما في ملفّ الشعار"),
    ("icon-512.png",          512, 0.586, "الإطار الرسمي"),
    ("icon-192.png",          192, 0.586, "الإطار الرسمي"),
    ("apple-touch-icon.png",  180, 0.586, "بلا قناة شفافية — شرط App Store"),
    ("icon-maskable-512.png", 512, 0.500, "هامش أوسع: أندرويد يقصّ الأيقونة دائرياً"),
    ("icon-maskable-192.png", 192, 0.500, "هامش أوسع"),
    ("favicon-32.png",         32, 0.860, "تكبير داخل المربّع ليصمد الفاصل في التبويب"),
    ("favicon-16.png",         16, 0.860, "تكبير داخل المربّع"),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, size, scale, why in TARGETS:
        img = render(size, scale)
        assert img.mode == "RGB", "بلا قناة شفافية"
        img.save(os.path.join(OUT, name), "PNG")
        print("%-24s %4dpx   %s" % (name, size, why))
    # favicon.ico وحده في جذر public/ لا public/icons/ — المتصفّحات تطلب
    # /favicon.ico من الجذر تلقائياً بلا أي <link> في HTML، فملفّ واحد هناك
    # يغطّي كل صفحات الموقع بلا تعديل صفحة واحدة منها.
    root_out = os.path.dirname(OUT)
    render(48, 0.86).save(os.path.join(root_out, "favicon.ico"), "ICO",
                          sizes=[(16, 16), (32, 32), (48, 48)])
    print("%-24s %s" % ("favicon.ico", "16/32/48"))

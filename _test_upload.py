"""اختبار /upload endpoint باستخدام requests"""
import requests, base64

# صورة PNG 1x1 pixel شفافة
png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
img_bytes = base64.b64decode(png_b64)

resp = requests.post(
    "http://127.0.0.1:8000/upload",
    files={"file": ("test_img.png", img_bytes, "image/png")},
    timeout=30,
)
print("Status:", resp.status_code)
print("Body:", resp.json())

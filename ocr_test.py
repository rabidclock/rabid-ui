import pytesseract
from PIL import Image

try:
    print(f"Tesseract Version: {pytesseract.get_tesseract_version()}")
    print("Environment check: SUCCESS")
except Exception as e:
    print(f"Environment check: FAILED - {e}")

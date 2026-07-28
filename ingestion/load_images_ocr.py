from pathlib import Path

import pytesseract
from PIL import Image


def extract_image_text(path: Path) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)

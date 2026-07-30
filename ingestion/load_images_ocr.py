import shutil
from pathlib import Path

import pytesseract
from PIL import Image

# On Windows, a fresh winget/installer PATH update isn't visible to processes
# started before the install (e.g. this one), so PATH lookup alone can miss
# a tesseract that is genuinely installed. Fall back to the default install
# location rather than requiring every caller to restart their shell.
_DEFAULT_WINDOWS_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
_DEFAULT_USER_LINUX_TESSERACT = Path.home() / ".local/share/mamba/envs/tesseract/bin/tesseract"
if not shutil.which("tesseract"):
    if _DEFAULT_WINDOWS_TESSERACT.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_DEFAULT_WINDOWS_TESSERACT)
    elif _DEFAULT_USER_LINUX_TESSERACT.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_DEFAULT_USER_LINUX_TESSERACT)


def extract_image_text(path: Path) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)

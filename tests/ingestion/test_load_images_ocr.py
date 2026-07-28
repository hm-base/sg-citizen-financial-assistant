from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from ingestion.load_images_ocr import extract_image_text


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    image = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 60), "SILVER SUPPORT SCHEME", fill="black", font=ImageFont.load_default())
    path = tmp_path / "sample.png"
    image.save(path)
    return path


def test_extract_image_text_finds_rendered_words(sample_image):
    text = extract_image_text(sample_image)
    assert "SILVER" in text.upper() or "SUPPORT" in text.upper()

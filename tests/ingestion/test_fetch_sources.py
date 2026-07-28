from pathlib import Path

import pytest

from ingestion.fetch_sources import fetch_sources, load_sources_yaml


@pytest.fixture
def sources_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(
        "- doc_id: baby-bonus-scheme\n"
        "  url: https://example.gov.sg/baby-bonus.pdf\n"
        "  modality: text\n"
        "  scheme_name: Baby Bonus Scheme\n"
        "  category: Family\n"
        "- doc_id: cdc-vouchers\n"
        "  url: https://example.gov.sg/cdc.png\n"
        "  modality: image\n"
        "  scheme_name: CDC Vouchers\n"
        "  category: Household\n",
        encoding="utf-8",
    )
    return path


class FakeDownloader:
    def __init__(self):
        self.requested = []

    def get(self, url: str) -> bytes:
        self.requested.append(url)
        return f"content-of-{url}".encode("utf-8")


def test_load_sources_yaml_parses_entries(sources_yaml):
    entries = load_sources_yaml(sources_yaml)
    assert len(entries) == 2
    assert entries[0]["doc_id"] == "baby-bonus-scheme"
    assert entries[1]["modality"] == "image"


def test_fetch_sources_downloads_into_modality_folders(sources_yaml, tmp_path):
    entries = load_sources_yaml(sources_yaml)
    downloader = FakeDownloader()
    raw_dir = tmp_path / "raw"

    saved_paths = fetch_sources(entries, raw_dir, downloader)

    assert len(saved_paths) == 2
    assert (raw_dir / "text" / "baby-bonus-scheme.pdf").exists()
    assert (raw_dir / "images" / "cdc-vouchers.png").exists()
    assert downloader.requested == [
        "https://example.gov.sg/baby-bonus.pdf",
        "https://example.gov.sg/cdc.png",
    ]

from pathlib import Path
from typing import Protocol

import yaml


class Downloader(Protocol):
    def get(self, url: str) -> bytes: ...


def load_sources_yaml(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or []


def fetch_sources(entries: list[dict], raw_dir: Path, downloader: Downloader) -> list[Path]:
    modality_subdir = {"text": "text", "image": "images", "video": "video"}
    saved_paths = []
    for entry in entries:
        subdir = modality_subdir[entry["modality"]]
        folder = raw_dir / subdir
        folder.mkdir(parents=True, exist_ok=True)
        suffix = Path(entry["url"]).suffix or ".bin"
        target = folder / f"{entry['doc_id']}{suffix}"
        target.write_bytes(downloader.get(entry["url"]))
        saved_paths.append(target)
    return saved_paths


import requests


class RequestsDownloader:
    def get(self, url: str) -> bytes:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content


if __name__ == "__main__":
    import config

    entries = load_sources_yaml(config.SOURCES_YAML_PATH)
    paths = fetch_sources(entries, config.DATA_DIR / "raw", RequestsDownloader())
    print(f"Downloaded {len(paths)} sources into {config.DATA_DIR / 'raw'}")

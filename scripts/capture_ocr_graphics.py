#!/usr/bin/env python3
"""Capture official payout/eligibility table graphics for OCR modality.

Outputs PNGs under:
  - sg-citizen-financial-assistant/data/raw/images/<topic>/
  - Windows Drive upload pack images/<topic>/
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF

REPO = Path("/home/jonyling/SNAIC/Week7/Week7_Capstone/sg-citizen-financial-assistant")
RAW_IMG = REPO / "data" / "raw" / "images"
DRIVE = Path("/mnt/c/Users/User/Downloads/sg-finance-project-jony-upload/images")
META = REPO / "data" / "meta"
MANIFEST = REPO / "data" / "sources_images.yaml"

# Folder names under data/raw/images must match CATEGORY_BY_FOLDER keys
# (wis/sctp/ccp → Lower-income/employment)
PAGES = [
    {
        "doc_id": "cpf_wis_employee_payout_table",
        "topic_folder": "wis",
        "topic": "Workfare_WIS",
        "scheme": "Workfare Income Supplement",
        "agency": "CPF",
        "title": "WIS maximum annual payout by age (employees) — CPF scheme page",
        "url": "https://www.cpf.gov.sg/member/growing-your-savings/government-support/workfare-income-supplement",
        "selectors": [
            "table",
            "[class*='table']",
            "main table",
        ],
        "prefer_text": ["Maximum WIS", "Work Year 2025", "30-34", "$2,450"],
    },
    {
        "doc_id": "cpf_wis_how_much_payout_table",
        "topic_folder": "wis",
        "topic": "Workfare_WIS",
        "scheme": "Workfare Income Supplement",
        "agency": "CPF",
        "title": "How much WIS will I get — payout + CPF allocation tables",
        "url": "https://www.cpf.gov.sg/service/article/how-much-workfare-income-supplement-will-i-get",
        "selectors": ["table", "main table"],
        "prefer_text": ["Maximum WIS", "Ordinary Account", "MediSave", "Work Year 2025"],
    },
    {
        "doc_id": "cpf_wis_payment_schedule_table",
        "topic_folder": "wis",
        "topic": "Workfare_WIS",
        "scheme": "Workfare Income Supplement",
        "agency": "CPF",
        "title": "WIS payment schedule (worked in → paid in)",
        "url": "https://www.cpf.gov.sg/service/article/when-will-i-get-my-workfare-income-supplement",
        "selectors": ["table", "main table"],
        "prefer_text": ["PayNow", "GovCash", "End March", "worked in"],
    },
    {
        "doc_id": "ssg_skillsfuture_credit_amounts",
        "topic_folder": "sctp",
        "topic": "SkillsFuture_SCTP",
        "scheme": "SkillsFuture Credit",
        "agency": "SSG",
        "title": "SkillsFuture Credit amounts / usage — official portal",
        "url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/SkillsFuture_Credit.html",
        "selectors": ["table", "main table", "[class*='table']", "article"],
        "prefer_text": ["$500", "Credit", "SkillsFuture", "mid-career"],
    },
    {
        "doc_id": "ssg_sctp_scheme_overview",
        "topic_folder": "sctp",
        "topic": "SkillsFuture_SCTP",
        "scheme": "SkillsFuture Career Transition Programme",
        "agency": "SSG",
        "title": "SCTP scheme overview — eligibility / support graphic region",
        "url": "https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/skillsfuture-career-transition-programme.html",
        "selectors": ["table", "main table", "article", "main"],
        "prefer_text": ["Career Transition", "SCTP", "eligible", "course"],
    },
    {
        "doc_id": "wsg_ccp_individuals_eligibility",
        "topic_folder": "ccp",
        "topic": "Career_Conversion_CCP",
        "scheme": "Career Conversion Programme",
        "agency": "WSG",
        "title": "CCP for individuals — eligibility / support summary",
        "url": "https://www.wsg.gov.sg/home/individuals/attachment-placement-programmes/career-conversion-programmes-for-individuals",
        "selectors": ["table", "main table", "main", "article"],
        "prefer_text": ["Career Conversion", "eligibility", "salary", "support"],
    },
]

PDF_PAGES = [
    {
        "doc_id": "swda_ccp_factsheet_eligibility_graphic",
        "topic_folder": "ccp",
        "topic": "Career_Conversion_CCP",
        "scheme": "Career Conversion Programme",
        "agency": "SWDA",
        "title": "CCP Factsheet Jul 2026 — page with eligibility / funding tables",
        "url": "https://www.swda.gov.sg/docs/programme/38b67413-cd3c-4968-8587-d370c4dc9256/ccp-factsheet-jul-2026.pdf",
        "pdf": REPO / "datasets/Career_Conversion_CCP/pdf/swda_ccp_factsheet_202607.pdf",
        "pages": [0, 1],  # 0-indexed; first pages usually have criteria/tables
    },
]


def score_locator(loc, prefer_text: list[str]) -> float:
    try:
        text = (loc.inner_text(timeout=2000) or "").lower()
    except Exception:
        return -1.0
    if len(text.strip()) < 40:
        return -1.0
    score = 0.0
    for needle in prefer_text:
        if needle.lower() in text:
            score += 2.0
    # Prefer denser numeric tables
    score += min(text.count("$"), 8) * 0.5
    score += min(len(re.findall(r"\d", text)), 40) * 0.05
    # Penalize huge chrome blobs
    if len(text) > 8000:
        score -= 5.0
    return score


def best_element(page, selectors: list[str], prefer_text: list[str]):
    candidates = []
    for sel in selectors:
        for i, loc in enumerate(page.locator(sel).all()):
            try:
                if not loc.is_visible():
                    continue
            except Exception:
                continue
            s = score_locator(loc, prefer_text)
            if s >= 0:
                candidates.append((s, loc, f"{sel}[{i}]"))
    if not candidates:
        # fallback: main content
        main = page.locator("main, article, #content, .content").first
        if main.count():
            return main, "main-fallback"
        return page.locator("body"), "body-fallback"
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][2]


def capture_page(item: dict, browser) -> dict | None:
    out_dir = RAW_IMG / item["topic_folder"]
    out_dir.mkdir(parents=True, exist_ok=True)
    drive_dir = DRIVE / item["topic"]
    drive_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{item['doc_id']}.png"

    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    try:
        page.goto(item["url"], wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2500)
        # dismiss cookie banners if present
        for label in ("Accept", "Agree", "I understand", "Close"):
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            try:
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=1500)
                    page.wait_for_timeout(500)
            except Exception:
                pass

        loc, chosen = best_element(page, item["selectors"], item["prefer_text"])
        # Scroll into view then screenshot element
        try:
            loc.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(400)
            loc.screenshot(path=str(out_path), type="png")
        except Exception:
            # Clip a vertical slice of the page around mid content
            page.screenshot(path=str(out_path), full_page=False, type="png")
            chosen = chosen + "+viewport-fallback"

        drive_path = drive_dir / out_path.name
        drive_path.write_bytes(out_path.read_bytes())

        meta = {
            "doc_id": item["doc_id"],
            "title": item["title"],
            "source_url": item["url"],
            "agency": item["agency"],
            "topic": item["topic"],
            "scheme": item["scheme"],
            "tier": "A",
            "retrieved_on": "2026-07-29",
            "doc_type": "pdf" if False else "scheme_page",
            "modality": "image",
            "owner": "Jony",
            "local_path": str(out_path.relative_to(REPO)),
            "capture_method": "playwright_element_screenshot",
            "capture_selector_note": chosen,
        }
        return meta
    except Exception as e:
        print(f"FAIL {item['doc_id']}: {e}")
        return None
    finally:
        context.close()


def capture_pdf(item: dict) -> list[dict]:
    pdf_path = Path(item["pdf"])
    if not pdf_path.exists():
        print(f"MISSING PDF {pdf_path}")
        return []
    out_dir = RAW_IMG / item["topic_folder"]
    out_dir.mkdir(parents=True, exist_ok=True)
    drive_dir = DRIVE / item["topic"]
    drive_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    metas = []
    for page_i in item["pages"]:
        if page_i >= len(doc):
            continue
        page = doc[page_i]
        # 2x zoom for OCR clarity
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        doc_id = f"{item['doc_id']}_p{page_i + 1}"
        out_path = out_dir / f"{doc_id}.png"
        pix.save(str(out_path))
        drive_path = drive_dir / out_path.name
        drive_path.write_bytes(out_path.read_bytes())
        metas.append(
            {
                "doc_id": doc_id,
                "title": f"{item['title']} (page {page_i + 1})",
                "source_url": item["url"],
                "agency": item["agency"],
                "topic": item["topic"],
                "scheme": item["scheme"],
                "tier": "D",
                "retrieved_on": "2026-07-29",
                "doc_type": "pdf",
                "modality": "image",
                "owner": "Jony",
                "local_path": str(out_path.relative_to(REPO)),
                "capture_method": "pymupdf_raster",
                "pdf_page": page_i + 1,
            }
        )
    doc.close()
    return metas


def write_yaml(metas: list[dict]) -> None:
    lines = [
        "# Official payout / eligibility graphics for OCR modality (Jony)",
        "# Place files under data/raw/images/{wis,sctp,ccp}/ before build_index",
        "",
    ]
    for m in metas:
        lines.append(f"- doc_id: {m['doc_id']}")
        lines.append(f"  url: {m['source_url']}")
        lines.append(f"  modality: image")
        lines.append(f"  topic: {m['topic']}")
        lines.append(f"  scheme: {m['scheme']}")
        lines.append(f"  agency: {m['agency']}")
        lines.append(f"  title: \"{m['title']}\"")
        lines.append(f"  local_path: {m['local_path']}")
        lines.append(f"  meta: data/meta/{m['doc_id']}.json")
        lines.append("")
    MANIFEST.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RAW_IMG.mkdir(parents=True, exist_ok=True)
    DRIVE.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)

    metas: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for item in PAGES:
            print(f"Capturing {item['doc_id']} …")
            m = capture_page(item, browser)
            if m:
                metas.append(m)
                print(f"  OK → {m['local_path']} ({m['capture_selector_note']})")
        browser.close()

    for item in PDF_PAGES:
        print(f"Rasterizing {item['doc_id']} …")
        for m in capture_pdf(item):
            metas.append(m)
            print(f"  OK → {m['local_path']}")

    for m in metas:
        (META / f"{m['doc_id']}.json").write_text(
            json.dumps(m, indent=2) + "\n", encoding="utf-8"
        )

    write_yaml(metas)
    # also copy yaml + meta into Drive pack
    drive_root = DRIVE.parent
    (drive_root / "sources_images.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    drive_meta = drive_root / "meta"
    drive_meta.mkdir(exist_ok=True)
    for m in metas:
        (drive_meta / f"{m['doc_id']}.json").write_text(
            json.dumps(m, indent=2) + "\n", encoding="utf-8"
        )

    print(f"\nDone: {len(metas)} images")
    for m in metas:
        print(f"  - {m['doc_id']}")


if __name__ == "__main__":
    main()

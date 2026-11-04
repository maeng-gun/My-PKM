"""Synthetic fixtures and generators for Valley AI Macro Lecture Pipeline E2E tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

# Exact 9 parts, 27 chapters specification
SYNTHETIC_CURRICULUM_DATA: List[Dict[str, Any]] = [
    {
        "round": 1,
        "round_title": "1회차: 글로벌 매크로 오리엔테이션 및 기초",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "글로벌 매크로 실전편 구성",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_1_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "거시경제 데이터 해석의 기초",
                "lecture_type": "video",
                "attachment_title": None,
                "attachment_url": None,
            },
            {
                "lecture_num": 3,
                "title": "자산군 간 상관관계 입문",
                "lecture_type": "video",
                "attachment_title": None,
                "attachment_url": None,
            },
        ],
    },
    {
        "round": 2,
        "round_title": "2회차: 1960~70년대 브레튼우즈와 스태그플레이션",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "60년대 통사: 인플레이션의 태동",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_2_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "브레튼우즈 체제의 붕괴",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_2_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "1차 오일쇼크와 스태그플레이션",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_2_3.pdf",
            },
        ],
    },
    {
        "round": 3,
        "round_title": "3회차: 1980년대 볼커 쇼크와 플라자 합의",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "볼커의 금리 인상과 달러 강세",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_3_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "플라자 합의와 엔고 현상",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_3_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "블랙먼데이와 유동성 공급",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_3_3.pdf",
            },
        ],
    },
    {
        "round": 4,
        "round_title": "4회차: 1990년대 아시아 외환위기와 닷컴 버블",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "90년대 신흥국 외환위기",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_4_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "닷컴 버블의 형성과 붕괴",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_4_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "연준의 금리 인하와 자산 효과",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_4_3.pdf",
            },
        ],
    },
    {
        "round": 5,
        "round_title": "5회차: 2000년대 중국 부상과 글로벌 금융위기",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "중국의 WTO 가입과 슈퍼사이클",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_5_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "서브프라임 모기지와 구조화 채권",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_5_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "글로벌 금융위기와 양적완화",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_5_3.pdf",
            },
        ],
    },
    {
        "round": 6,
        "round_title": "6회차: 2010년대 유럽 재정위기와 저물가 시대",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "유럽 재정위기와 유로존의 구조",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_6_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "테이퍼 탠트럼과 신흥국 충격",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_6_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "원자재 폭락과 디플레이션 압력",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_6_3.pdf",
            },
        ],
    },
    {
        "round": 7,
        "round_title": "7회차: 미중 무역분쟁과 코로나19 팬데믹",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "미중 무역전쟁과 글로벌 공급망",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_7_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "팬데믹 충격과 무제한 유동성",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_7_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "공급망 병목과 인플레이션 귀환",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_7_3.pdf",
            },
        ],
    },
    {
        "round": 8,
        "round_title": "8회차: 긴축 사이클과 실리콘밸리은행 사태",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "자이언트 스텝과 금리 정상화",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_8_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "실리콘밸리은행 사태와 신용경색",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_8_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "AI 혁명과 미국 주식 독주",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_8_3.pdf",
            },
        ],
    },
    {
        "round": 9,
        "round_title": "9회차: 뉴노멀과 글로벌 매크로 TAA 실전",
        "lectures": [
            {
                "lecture_num": 1,
                "title": "탈세계화와 지정학적 분절화",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_9_1.pdf",
            },
            {
                "lecture_num": 2,
                "title": "고금리 장기화(Higher for Longer)의 역학",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_9_2.pdf",
            },
            {
                "lecture_num": 3,
                "title": "글로벌 매크로 실전 포트폴리오 구축",
                "lecture_type": "material",
                "attachment_title": "강의자료",
                "attachment_url": "https://www.valley.town/attachment/lec_9_3.pdf",
            },
        ],
    },
]


def generate_curriculum_html() -> str:
    """Generate HTML replicating Valley AI course curriculum DOM for offline testing."""
    html_parts = ['<div class="course-curriculum">']
    for part in SYNTHETIC_CURRICULUM_DATA:
        r_num = part["round"]
        html_parts.append(f'<div class="part-section" data-round="{r_num}">')
        html_parts.append(f'  <h3 class="part-title">{part["round_title"]}</h3>')
        for lec in part["lectures"]:
            l_num = lec["lecture_num"]
            title = lec["title"]
            l_type = lec["lecture_type"]
            html_parts.append(f'  <div class="lecture-item" data-round="{r_num}" data-lecture="{l_num}">')
            html_parts.append(f'    <button class="lecture-btn">{l_num}강: {title}</button>')
            if lec["attachment_url"]:
                att_title = lec["attachment_title"] or "강의자료"
                att_url = lec["attachment_url"]
                html_parts.append(f'    <a href="{att_url}" class="attachment-link">{att_title}</a>')
            html_parts.append("  </div>")
        html_parts.append("</div>")
    html_parts.append("</div>")
    return "\n".join(html_parts)


def create_synthetic_pdf(
    target_path: Path,
    title: str = "글로벌 매크로 강의",
    body_text: str = "글로벌 매크로 경제 분석 및 자산 배분 강의 내용입니다.",
    corrupt_type: Optional[str] = None,
    min_size_bytes: int = 1500,
) -> Path:
    """Create a synthetic PDF file for testing (either valid or corrupted)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if corrupt_type == "zero_byte":
        target_path.write_bytes(b"")
        return target_path

    if corrupt_type == "too_small":
        # Under 1024 bytes
        target_path.write_bytes(b"%PDF-1.4\n%small\n%%EOF\n")
        return target_path

    if corrupt_type == "no_header":
        # HTML error page or text instead of PDF magic bytes (padded > 1024 bytes)
        html_content = (
            b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>\n"
            b"<h1>404 Not Found</h1>\n"
            + (b"<p>The requested URL was not found on this server. Please check the address.</p>\n" * 30)
            + b"</body></html>\n"
        )
        target_path.write_bytes(html_content)
        return target_path

    if corrupt_type == "no_eof":
        # Valid header but missing EOF trailer
        content = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            + b"Padding stream data " * 50
        )
        target_path.write_bytes(content)
        return target_path

    # Standard valid PDF binary
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 120 >>\nstream\n"
        b"BT\n/F1 12 Tf\n72 712 Td\n(Valley AI Global Macro Lecture) Tj\nET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000214 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n380\n"
        b"%%EOF\n"
    )

    # Pad if required to exceed min_size_bytes while keeping valid header & %%EOF
    if len(pdf_content) < min_size_bytes:
        pad_len = min_size_bytes - len(pdf_content) + 100
        padding = b"\n% " + (b"PAD" * (pad_len // 3)) + b"\n"
        # insert padding before trailer
        parts = pdf_content.split(b"trailer\n")
        pdf_content = parts[0] + padding + b"trailer\n" + parts[1]

    target_path.write_bytes(pdf_content)
    return target_path


def create_synthetic_drivefs_db(db_path: Path, cloud_id: str = "TEST_CLOUD_ID_12345") -> Path:
    """Create a synthetic DriveFS SQLite metadata database for URL resolution testing."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE items (
            stable_id INTEGER PRIMARY KEY,
            id TEXT,
            local_title TEXT,
            is_folder INTEGER,
            trashed INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE stable_parents (
            item_stable_id INTEGER,
            parent_stable_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE stable_ids (
            stable_id INTEGER PRIMARY KEY,
            cloud_id TEXT
        )
        """
    )

    # Insert root '내 드라이브'
    cur.execute(
        "INSERT INTO items VALUES (1, 'root_cloud_id', '내 드라이브', 1, 0)"
    )
    cur.execute(
        "INSERT INTO stable_parents VALUES (1, NULL)"
    )

    # Insert 'Archive_Sources' folder
    cur.execute(
        "INSERT INTO items VALUES (2, 'archive_cloud_id', 'Archive_Sources', 1, 0)"
    )
    cur.execute(
        "INSERT INTO stable_parents VALUES (2, 1)"
    )

    # Insert subfolder '320. Lectures'
    cur.execute(
        "INSERT INTO items VALUES (3, 'lectures_cloud_id', '320. Lectures', 1, 0)"
    )
    cur.execute(
        "INSERT INTO stable_parents VALUES (3, 2)"
    )

    # Insert a sample file inside 320. Lectures
    cur.execute(
        "INSERT INTO items VALUES (4, ?, 'sample_lecture.pdf', 0, 0)",
        (cloud_id,)
    )
    cur.execute(
        "INSERT INTO stable_parents VALUES (4, 3)"
    )
    cur.execute(
        "INSERT INTO stable_ids VALUES (4, ?)",
        (cloud_id,)
    )

    conn.commit()
    conn.close()
    return db_path

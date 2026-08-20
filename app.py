from __future__ import annotations

import ast
import html
import json
import os
from urllib.parse import urlparse

import pandas as pd
import streamlit as st


# ============================================================
# 기본 설정
# ============================================================

#CSV_FILE_PATH = (
#    r"D:\Local developing\HR-news dashboard\hr_news.csv"
#)

from pathlib import Path

BASE_DIR = Path(__file__).parent
CSV_FILE_PATH = BASE_DIR / "hr_news.csv"


st.set_page_config(
    page_title="HR 뉴스 대시보드",
    page_icon="📰",
    layout="wide"
)


# ============================================================
# 스타일
# ============================================================

st.markdown(
    """
<style>
    /* Streamlit 기본 상단 여백 축소 */
    .block-container {
        max-width: 1380px;
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    .main {
        background-color: #f8fafc;
    }

    body,
    div,
    span,
    a,
    button {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Arial,
            sans-serif;
    }

    /* Streamlit 상단 헤더 공간 완화 */
    header[data-testid="stHeader"] {
        height: 2.5rem;
        background-color: transparent;
    }

    /* ============================================
       오늘의 스마일게이트
       ============================================ */

    .sg-container {
        background-color: #1b2230;
        border: 1px solid #283244;
        border-radius: 9px;
        padding: 13px 16px;
        margin-top: 0;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.10);
    }

    .sg-title {
        font-size: 14px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 9px;
        letter-spacing: -0.2px;
    }

    .sg-card {
        background-color: #242d3f;
        border: 1px solid #303b50;
        border-radius: 6px;
        margin-bottom: 6px;
        overflow: hidden;
        transition:
            border-color 0.18s ease,
            background-color 0.18s ease;
    }

    .sg-card:last-child {
        margin-bottom: 0;
    }

    .sg-card:hover {
        border-color: #64748b;
        background-color: #293449;
    }

    .sg-card-header {
        padding: 8px 11px;
        font-size: 12px;
        font-weight: 600;
        color: #f8fafc;
        display: flex;
        align-items: center;
        min-width: 0;
    }

    .sg-date-tag {
        color: #60a5fa;
        font-weight: 700;
        margin-right: 8px;
        flex-shrink: 0;
    }

    .sg-title-text {
        display: block;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .sg-card-body {
        max-height: 0;
        overflow: hidden;
        padding: 0 11px;
        background-color: #202838;
        transition:
            max-height 0.25s ease-out,
            padding 0.25s ease-out;
    }

    .sg-card:hover .sg-card-body {
        max-height: 1800px !important;
        padding: 10px 11px;
        border-top: 1px solid #344056;
    }

        /* ============================================
       HR 영향도 / 관련 토픽
       ============================================ */

    .hr-impact-line {
        padding: 0 10px 7px 10px;
        font-size: 10px;
        line-height: 1.3;
        color: #64748b;
        font-weight: 500;
    }

    .hr-impact-topic {
        color: #475569;
        font-weight: 600;
    }

    .hr-impact-high {
        color: #dc2626;
        font-weight: 700;
    }

    .hr-impact-medium {
        color: #d97706;
        font-weight: 700;
    }

    .hr-impact-low {
        color: #94a3b8;
        font-weight: 600;
    }


    /* ============================================
       일반 뉴스 카드
       ============================================ */

    .news-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 7px;
        margin-bottom: 10px;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
        transition:
            border-color 0.18s ease,
            box-shadow 0.18s ease;
    }

    .news-card:hover {
        border-color: #94a3b8;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
    }

    .card-header {
        min-height: 36px;
        padding: 7px 10px;
        font-size: 13px;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        align-items: center;
        min-width: 0;
    }

    .date-tag {
        color: #2563eb;
        font-weight: 700;
        margin-right: 7px;
        flex-shrink: 0;
    }

    .card-title-text {
        display: block;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .card-body {
        max-height: 0;
        overflow: hidden;
        padding: 0 10px;
        background-color: #ffffff;
        transition:
            max-height 0.25s ease-out,
            padding 0.25s ease-out;
    }

    .news-card:hover .card-body {
        max-height: 1800px !important;
        padding: 10px;
        border-top: 1px solid #e2e8f0;
    }

    

    /* ============================================
       카드 상세 내용
       ============================================ */

    .summary-title-sg {
        color: #fca5a5;
        font-weight: 700;
        font-size: 11px;
        margin-bottom: 4px;
    }

    .summary-box-sg {
        font-size: 11px;
        color: #d6deea;
        line-height: 1.55;
        white-space: normal;
        margin-bottom: 8px;
        word-break: keep-all;
    }

    .summary-title-normal {
        color: #b91c1c;
        font-weight: 700;
        font-size: 11px;
        margin-bottom: 4px;
    }

    .summary-box {
        font-size: 11px;
        color: #334155;
        line-height: 1.55;
        white-space: normal;
        margin-bottom: 8px;
        word-break: keep-all;
    }

    .checkpoint-title {
        color: #15803d;
        font-weight: 700;
        font-size: 11px;
        margin-bottom: 4px;
    }

    .checkpoint-box {
        background-color: #f7fbf8;
        border: 1px solid #dcefe1;
        border-radius: 4px;
        padding: 7px 9px;
        font-size: 11px;
        color: #166534;
        margin-bottom: 7px;
        word-break: keep-all;
    }

    .checkpoint-item {
        margin-bottom: 3px;
        line-height: 1.45;
    }

    .checkpoint-item:last-child {
        margin-bottom: 0;
    }

    .btn-link {
        display: inline-block;
        background-color: #334155;
        color: #ffffff !important;
        font-size: 10px;
        font-weight: 700;
        padding: 4px 9px;
        border-radius: 4px;
        text-decoration: none !important;
        margin-top: 2px;
    }

    .btn-link:hover {
        background-color: #1e293b;
    }
        /* ============================================
       필터 영역
       ============================================ */

    .filter-container {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px 10px 16px;
        margin-top: 18px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    }

    .filter-title {
        font-size: 13px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
    }

    .result-count {
        font-size: 13px;
        color: #475569;
        margin: 8px 0 14px 0;
        font-weight: 500;
    }
        .dashboard-summary {
        font-size: 12px;
        color: #64748b;
        margin: 2px 0 16px 0;
        line-height: 1.5;
        font-weight: 500;
    }

    .summary-divider {
        color: #cbd5e1;
        margin: 0 7px;
    }

    .result-count strong {
        color: #1e293b;
        font-weight: 700;
    }
    
    /* ============================================
       섹션
       ============================================ */

    .sec-header {
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        margin-top: 18px;
        margin-bottom: 10px;
        padding-bottom: 7px;
        border-bottom: 1px solid #e2e8f0;
        letter-spacing: -0.2px;
        display: flex;
        align-items: center;
        gap: 7px;
    }

    .sec-marker {
        width: 4px;
        height: 18px;
        border-radius: 3px;
        background-color: #475569;
        display: inline-block;
        flex-shrink: 0;
    }

    .sec-count {
        color: #94a3b8;
        font-size: 11px;
        font-weight: 500;
        margin-left: auto;
    }

    .empty-section-box {
        background-color: #ffffff;
        border: 1px dashed #cbd5e1;
        border-radius: 6px;
        padding: 18px 10px;
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        margin-bottom: 8px;
    }

    /* ============================================
       더보기
       ============================================ */

    div[data-testid="stExpander"] {
        border: 1px solid #dce3ec !important;
        border-radius: 6px !important;
        background-color: #f8fafc !important;
        margin-top: 2px !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
    }

    div[data-testid="stExpander"] summary p {
        min-height: 0 !important;
        padding: 2px 8px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #64748b !important;
        background-color: #f8fafc !important;
        border-radius: 6px !important;
    }

    div[data-testid="stExpander"] summary:hover {
        color: #334155 !important;
        background-color: #f1f5f9 !important;
    }

    div[data-testid="stExpanderDetails"] {
        padding-top: 2px !important;
        padding-bottom: 0px !important;
    }

    /* 컬럼 사이 간격 */
    div[data-testid="stHorizontalBlock"] {
        gap: 1.1rem;
    }


    /* 좁은 화면 대응 */
    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

/* ============================================================
   사이드바
   ============================================================ */

/* ============================================================
   사이드바 전체 배경 - 강제 적용
   ============================================================ */

/* 사이드바 최외곽 */
section[data-testid="stSidebar"] {
    background: #1b2230 !important;
    background-color: #1b2230 !important;
}

/* Streamlit 사이드바 내부 모든 주요 wrapper */
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    background: #1b2230 !important;
    background-color: #1b2230 !important;
}

/* 사이드바 내부 기본 block 영역 */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: transparent !important;
}

/* 사이드바 안쪽 여백 */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* 실제 사용자 콘텐츠 영역 */
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    background-color: #1b2230 !important;
}

/* 사이드바 내부 일반 텍스트 */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
    color: #f8fafc;
}
/* ============================================================
   사이드바 접기 버튼 - 강제 강조
   ============================================================ */

/* 접기 버튼 자체 */
button[data-testid="stSidebarCollapseButton"] {
    background-color: #475569 !important;
    border: 2px solid #94a3b8 !important;
    border-radius: 6px !important;

    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;

    padding: 0 !important;
    margin: 6px !important;

    opacity: 1 !important;

    box-shadow:
        0 2px 6px rgba(0, 0, 0, 0.35) !important;
}

/* 아이콘 */
button[data-testid="stSidebarCollapseButton"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;

    width: 18px !important;
    height: 18px !important;
}

/* 마우스 올렸을 때 */
button[data-testid="stSidebarCollapseButton"]:hover {
    background-color: #64748b !important;
    border-color: #cbd5e1 !important;
}

/* 아이콘을 감싸는 요소까지 강제 */
button[data-testid="stSidebarCollapseButton"] > div {
    background-color: transparent !important;
}

/* 버튼이 있는 상단 영역 */
section[data-testid="stSidebar"] > div:first-child {
    position: relative !important;
}
/* ------------------------------------------------------------
   사이드바 제목
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] .sidebar-title {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    line-height: 1.3 !important;
    margin: 0 0 3px 0 !important;
    padding: 0 !important;
}

section[data-testid="stSidebar"] .sidebar-subtitle {
    font-size: 12px !important;
    font-weight: 400 !important;
    color: #aeb8c8 !important;
    line-height: 1.5 !important;
    margin: 0 0 14px 0 !important;
    padding: 0 !important;
}

/* ------------------------------------------------------------
   사이드바 섹션 제목
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] h3 {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    line-height: 1.25 !important;
    margin-top: 9px !important;
    margin-bottom: 5px !important;
    padding: 0 !important;
}

section[data-testid="stSidebar"] h4 {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    line-height: 1.35 !important;
    margin-top: 10px !important;
    margin-bottom: 7px !important;
    padding: 0 !important;
}

/* ------------------------------------------------------------
   사이드바 설명 문구
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    font-size: 11px !important;
    color: #aeb8c8 !important;
    line-height: 1.55 !important;
    margin-top: 0 !important;
    margin-bottom: 8px !important;
}

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    font-size: 11px !important;
    color: #aeb8c8 !important;
    line-height: 1.55 !important;
    margin: 0 !important;
}

/* ------------------------------------------------------------
   검색창
   ------------------------------------------------------------ */

/* 검색창 전체 박스 */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* 검색창 바깥 테두리/컨테이너 */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] > div {
    min-height: 30px !important;
    height: 30px !important;
}

/* 실제 입력 박스 */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] div[data-baseweb="base-input"] {
    min-height: 30px !important;
    height: 30px !important;
    border-radius: 5px !important;
}

/* input */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
    height: 30px !important;
    min-height: 30px !important;
    padding: 4px 9px !important;
    font-size: 11px !important;
    line-height: 1.2 !important;
    color: #1e293b !important;
    box-sizing: border-box !important;
}

/* placeholder */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
    color: #9ca3af !important;
    opacity: 1 !important;
    font-size: 11px !important;
}

/* ------------------------------------------------------------
   Selectbox / Multiselect
   ------------------------------------------------------------ */

/* 위젯 전체 */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"],
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* 셀렉박스 전체 외곽 */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"],
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] {
    min-height: 28px !important;
    height: 28px !important;
    font-size: 11px !important;
}

/* 실제 흰색 박스 */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
    min-height: 28px !important;
    height: 28px !important;
    background-color: #ffffff !important;
    border-radius: 5px !important;
    border: none !important;
    box-sizing: border-box !important;
}

/* 값이 표시되는 영역 */
section[data-testid="stSidebar"] div[data-baseweb="select"] div[class*="ValueContainer"] {
    min-height: 28px !important;
    height: 28px !important;
    padding: 0 8px !important;
    display: flex !important;
    align-items: center !important;
    box-sizing: border-box !important;
}

/* ------------------------------------------------------------
   Selectbox 선택된 값 글씨
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] div[data-testid="stSelectbox"]
div[data-baseweb="select"]
div[class*="singleValue"],
section[data-testid="stSidebar"] div[data-testid="stSelectbox"]
div[data-baseweb="select"]
div[class*="singleValue"] span {
    font-size: 10px !important;
    line-height: 1.2 !important;
    color: #1e293b !important;
    font-weight: 400 !important;
}

/* Multiselect 선택값 */
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"]
div[data-baseweb="select"] span {
    font-size: 10px !important;
    line-height: 1.2 !important;
}

/* 드롭다운 목록 */
section[data-testid="stSidebar"] div[data-baseweb="popover"]
div[role="option"],
section[data-testid="stSidebar"] div[data-baseweb="popover"]
div[role="option"] span {
    font-size: 10px !important;
    line-height: 1.2 !important;
}

/* Multiselect의 선택값 */
section[data-testid="stSidebar"] div[data-baseweb="select"] [data-baseweb="tag"],
section[data-testid="stSidebar"] div[data-baseweb="select"] [data-baseweb="tag"] span {
    font-size: 11px !important;
    line-height: 1.2 !important;
    color: #1e293b !important;
    font-weight: 400 !important;
}

/* "토픽 선택" placeholder */
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] input {
    font-size: 11px !important;
    color: #1e293b !important;
}

section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] input::placeholder {
    font-size: 11px !important;
    color: #9ca3af !important;
    opacity: 1 !important;
}

/* selectbox 내부 input */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] input {
    font-size: 11px !important;
    color: #1e293b !important;
}

/* 오른쪽 화살표 영역 */
section[data-testid="stSidebar"] div[data-baseweb="select"] div[class*="IndicatorsContainer"] {
    height: 28px !important;
    min-height: 28px !important;
}


/* ------------------------------------------------------------
   구분선
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] hr {
    margin-top: 10px !important;
    margin-bottom: 10px !important;
    border: none !important;
    border-top: 1px solid #465166 !important;
}


/* ------------------------------------------------------------
   검색 결과
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] .filter-result {
    margin-top: 5px !important;
    margin-bottom: 4px !important;
    font-size: 11px !important;
    line-height: 1.4 !important;
    color: #94a3b8 !important;
}

section[data-testid="stSidebar"] .filter-result strong {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* ------------------------------------------------------------
   통계
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] .sidebar-summary {
    display: flex !important;
    gap: 6px !important;
    margin-top: 8px !important;
    margin-bottom: 0 !important;
}

section[data-testid="stSidebar"] .sidebar-stat {
    flex: 1 !important;
    background-color: #242d3f !important;
    border: 1px solid #303b50 !important;
    border-radius: 6px !important;
    padding: 9px 6px 8px 6px !important;
    text-align: center !important;
}

section[data-testid="stSidebar"] .sidebar-stat-number {
    font-size: 17px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    line-height: 1.2 !important;
    margin-bottom: 3px !important;
}

section[data-testid="stSidebar"] .sidebar-stat-label {
    font-size: 9px !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    letter-spacing: 0.4px !important;
    line-height: 1.2 !important;
}

/* ------------------------------------------------------------
   HR 이슈 토픽 칩
   ------------------------------------------------------------ */

section[data-testid="stSidebar"] .topic-chip-label {
    font-size: 11px !important;
    color: #aeb8c8 !important;
    margin-bottom: 6px !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] {
    margin-bottom: 3px !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    min-height: 28px !important;
    height: 28px !important;
    padding: 2px 8px !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    border-radius: 14px !important;
    border: 1px solid #465166 !important;
    background-color: #242d3f !important;
    color: #d6deea !important;
    white-space: nowrap !important;
}

/* HR 이슈 토픽 버튼 내부 글씨 */
section[data-testid="stSidebar"]
div[data-testid="stButton"] > button,
section[data-testid="stSidebar"]
div[data-testid="stButton"] > button p,
section[data-testid="stSidebar"]
div[data-testid="stButton"] > button span {
    font-size: 10px !important;
    line-height: 1.1 !important;
    font-weight: 500 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    border-color: #60a5fa !important;
    color: #ffffff !important;
    background-color: #303b50 !important;
}
</style>
""",
    unsafe_allow_html=True
)
# ============================================================
# 데이터 로딩
# ============================================================

def get_csv_modified_time() -> float:
    if not os.path.exists(CSV_FILE_PATH):
        return 0.0

    try:
        return os.path.getmtime(
            CSV_FILE_PATH
        )
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def load_data(
    file_path: str,
    modified_time: float
) -> pd.DataFrame:
    """
    CSV 수정 시각을 캐시 키로 사용하여
    수집 완료 후 새 데이터를 자동으로 다시 읽습니다.
    """

    del modified_time

    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        data_frame = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False
        )

    except UnicodeDecodeError:
        data_frame = pd.read_csv(
            file_path,
            encoding="utf-8",
            dtype=str,
            keep_default_na=False
        )

    except Exception as error:
        st.error(
            f"CSV 파일을 읽는 중 오류가 발생했습니다: {error}"
        )
        return pd.DataFrame()

    required_columns = [
        "category",
        "date_str",
        "title",
        "summary",
        "checkpoints",
        "link",
        "pubDate",
        "hr_relevance",
        "practical_value",
    ]

    for column in required_columns:
        if column not in data_frame.columns:
            data_frame[column] = ""

    data_frame = data_frame.fillna("")

    if "pubDate" in data_frame.columns:
        data_frame["_sort_date"] = pd.to_datetime(
            data_frame["pubDate"],
            errors="coerce",
            utc=True
        )

        data_frame = data_frame.sort_values(
            by="_sort_date",
            ascending=False,
            na_position="last"
        )

        data_frame = data_frame.drop(
            columns=["_sort_date"],
            errors="ignore"
        )

    return data_frame.reset_index(
        drop=True
    )

# ============================================================
# HR 토픽 분류
# ============================================================

HR_TOPIC_KEYWORDS = {


    # --------------------------------------------------------
    # 휴가·휴직
    # --------------------------------------------------------
    "휴가·휴직": [
        "육아휴직",
        "출산휴가",
        "연차",
        "휴가",
        "휴직",
        "가족돌봄휴가",
        "가족돌봄",
        "육아지원",
    ],

    # --------------------------------------------------------
    # 보상·임금
    # --------------------------------------------------------
    "보상·임금": [
        "임금",
        "급여",
        "연봉",
        "성과급",
        "성과보상",
        "상여금",
        "임금인상",
        "보수",
        "보상체계",
        "성과보상제",
        "임금체계",
        "임금제도",
        "복리후생",
        "처우개선",

        "퇴직금",
        "퇴직급여",
        "퇴직급여비용",
        "퇴직비용",
        "평균임금",
        "임금성",
        "임금에 해당",
        "성과급의 임금성",
        "근로의 대가",
        "TAI",
        "목표 인센티브",
    ],

    # --------------------------------------------------------
    # 노사관계
    # --------------------------------------------------------
    "노사관계": [
        "노조",
        "노동조합",
        "노조원",
        "단체교섭",
        "노사협의",
        "노사관계",
        "임단협",
        "임금협상",
        "파업",
        "쟁의",
        "노사갈등",
    ],

    # --------------------------------------------------------
    # 채용
    # --------------------------------------------------------
    "채용": [
        "채용",
        "채용공고",
        "신입사원",
        "신입채용",
        "경력채용",
        "경력직",
        "인재채용",
        "채용시장",
        "채용전형",
        "채용평가",
        "채용방식",
    ],

    # --------------------------------------------------------
    # 인력변화
    # --------------------------------------------------------
        "인력변화": [
        "희망퇴직",
        "명예퇴직",
        "정년",
        "정년퇴직",
        "계속고용",
        "고용연장",
        "구조조정",
        "인력감축",
        "인력재편",
        "인력 재편",
        "인력재배치",
        "인력 이동",
        "인력조정",
        "직무전환",
        "대규모 해고",
        "정리해고",
        "감원",
        "리스킬링",
        "업스킬링",
    ],

    # --------------------------------------------------------
    # 평가·인사제도
    # --------------------------------------------------------
    "평가·인사제도": [
        "인사평가",
        "성과평가",
        "평가제도",
        "성과관리",
        "성과관리제도",
        "승진",
        "승진제도",
        "직급",
        "직급제도",
        "인사제도",
        "인사관리",
        "인사운영",
        "인사정책",
        "평가기준",
        "평가 기준",
        "성과 평가 기준",
        "전보",
        "부당전보",
        "배치전환",
        "인사이동",
        "취업규칙",
        "근로계약",
        "징계제도",
        "징계기준",
        "징계절차",
    ],

    # --------------------------------------------------------
    # 조직·근무제도
    # --------------------------------------------------------
    "조직·근무제도": [
        "조직문화",
        "기업문화",
        "조직개편",
        "조직운영",
        "조직설계",

        "근무제도",
        "근무방식",
        "일하는 방식",
        "재택근무",
        "출근정책",
        "유연근무",
        "시차출퇴근",

        "근로시간",
        "근무시간",
        "근로시간제",
        "주4일제",
        "주 4일제",
        "주4일 근무",
        "근로시간 단축",
        "근무시간 단축",

        "ai 도입",
        "ai 활용",
        "ai 정책",
        "인공지능 도입",
        "인공지능 활용",
        "인공지능 정책",
    ],
}


# ============================================================
# HR 세부 토픽 분류
#
# category = collector.py에서 결정한 대분류
# topic    = app.py에서 title + summary를 기준으로 세부분류
# ============================================================

HR_TOPIC_KEYWORDS = {

    "보상·임금": [
        "임금",
        "급여",
        "연봉",
        "성과급",
        "성과보상",
        "상여금",
        "임금인상",
        "보수",
        "보상체계",
        "성과보상제",
        "임금체계",
        "임금제도",
        "복리후생",
        "처우개선",
        "퇴직금",
        "퇴직급여",
        "퇴직급여비용",
        "퇴직비용",
        "평균임금",
        "임금성",
        "임금에 해당",
        "성과급의 임금성",
        "근로의 대가",
        "TAI",
        "목표 인센티브",
    ],

    "노사관계": [
        "노조",
        "노동조합",
        "노조원",
        "단체교섭",
        "노사협의",
        "노사관계",
        "임단협",
        "임금협상",
        "파업",
        "쟁의",
        "쟁의행위",
        "노사갈등",
        "노사협상",
    ],

    "채용": [
        "채용",
        "채용공고",
        "신입사원",
        "신입채용",
        "경력채용",
        "경력직",
        "인재채용",
        "채용시장",
        "채용전형",
        "채용평가",
        "채용방식",
        "온보딩",
    ],

    "인력변화": [
        "희망퇴직",
        "명예퇴직",
        "정년",
        "정년퇴직",
        "계속고용",
        "고용연장",
        "구조조정",
        "인력감축",
        "인력재편",
        "인력 재편",
        "인력재배치",
        "인력 이동",
        "인력조정",
        "직무전환",
        "대규모 해고",
        "정리해고",
        "감원",
        "해고",
        "리스킬링",
        "업스킬링",
    ],

    "평가·인사제도": [
        "인사평가",
        "성과평가",
        "평가제도",
        "성과관리",
        "성과관리제도",
        "승진",
        "승진제도",
        "직급",
        "직급제도",
        "인사제도",
        "인사관리",
        "인사운영",
        "인사정책",
        "평가기준",
        "평가 기준",
        "성과 평가 기준",
        "전보",
        "부당전보",
        "배치전환",
        "인사이동",
        "취업규칙",
        "근로계약",
        "징계제도",
        "징계기준",
        "징계절차",
    ],

    "조직·근무제도": [
        "조직문화",
        "기업문화",
        "조직개편",
        "조직운영",
        "조직설계",
        "근무제도",
        "근무방식",
        "일하는 방식",
        "재택근무",
        "출근정책",
        "유연근무",
        "시차출퇴근",
        "근로시간",
        "근무시간",
        "근로시간제",
        "주4일제",
        "주 4일제",
        "주4일 근무",
        "근로시간 단축",
        "근무시간 단축",
        "AI 도입",
        "AI 활용",
        "AI 정책",
        "인공지능 도입",
        "인공지능 활용",
        "인공지능 정책",
    ],

    "휴가·휴직": [
        "육아휴직",
        "출산휴가",
        "연차",
        "휴가",
        "휴직",
        "가족돌봄휴가",
        "가족돌봄",
        "육아지원",
    ],

    "노동정책": [
        "근로기준법 개정",
        "근로기준법 개정안",
        "노동조합법 개정",
        "노동조합법 개정안",
        "노조법 개정",
        "노조법 개정안",
        "노동법 개정",
        "노동법 개정안",
        "법률 개정안",
        "법률 개정",
        "법안 발의",
        "법안 통과",
        "법안 가결",
        "국회 본회의 통과",
        "국회 통과",
        "입법예고",
        "입법 예고",
        "시행령 개정",
        "시행령 개정안",
        "시행규칙 개정",
        "시행규칙 개정안",
        "제도 개편",
        "제도 변경",
        "제도 시행",
        "제도 도입",
        "대법원 판결",
        "대법원 선고",
        "대법원 판단",
        "법원 판결",
        "법원 선고",
        "법원 판단",
        "노동위원회 판정",
        "노동위원회 결정",
        "중노위 판정",
        "중노위 결정",
        "지노위 판정",
        "지노위 결정",
    ],
}


def get_related_topics(
    row: pd.Series,
    max_topics: int = 3
) -> list[str]:

    title = str(
        row.get("title", "")
    ).strip().lower()

    summary = str(
        row.get("summary", "")
    ).strip().lower()

    # 제목과 요약을 합쳐서 세부 토픽 판정
    full_text = f"{title} {summary}"

    topic_scores = {}

    for topic, keywords in HR_TOPIC_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            keyword_lower = keyword.lower()

            # 제목에 있으면 가장 강하게
            if keyword_lower in title:
                score += 3

            # 요약에 있으면 그다음
            elif keyword_lower in summary:
                score += 1

        if score > 0:
            topic_scores[topic] = score

    # --------------------------------------------------------
    # 아무 토픽도 잡히지 않는 경우
    # --------------------------------------------------------

    if not topic_scores:
        return ["트렌드 · 타사 사례"]

    # --------------------------------------------------------
    # 토픽 우선순위
    # --------------------------------------------------------

    topic_order = {
        "보상·임금": 1,
        "노사관계": 2,
        "채용": 3,
        "인력변화": 4,
        "평가·인사제도": 5,
        "조직·근무제도": 6,
        "휴가·휴직": 7,
        "노동정책": 8,
    }

    sorted_topics = sorted(
        topic_scores.items(),
        key=lambda item: (
            item[1],
            -topic_order.get(item[0], 99)
        ),
        reverse=True
    )

    top_score = sorted_topics[0][1]

    selected_topics = []

    for topic, score in sorted_topics:

        # 최고 토픽의 45% 이상만 표시
        if score >= max(
            2,
            top_score * 0.45
        ):
            selected_topics.append(topic)

    return selected_topics[:max_topics]

# ============================================================
# 데이터 안전 처리
# ============================================================

def safe_text(
    value: object,
    default: str = ""
) -> str:
    if value is None:
        return html.escape(
            default,
            quote=True
        )

    text = str(value).strip()

    if not text:
        text = default

    return html.escape(
        text,
        quote=True
    )


def safe_multiline_text(
    value: object,
    default: str
) -> str:
    text = safe_text(
        value,
        default
    )

    return text.replace(
        "\n",
        "<br>"
    )


def safe_url(
    value: object
) -> str:
    url = str(
        value or ""
    ).strip()

    if not url:
        return ""

    try:
        parsed = urlparse(
            url
        )

        if parsed.scheme not in {
            "http",
            "https"
        }:
            return ""

        return html.escape(
            url,
            quote=True
        )

    except ValueError:
        return ""


def parse_checkpoints(
    value: object
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        list
    ):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    text = str(
        value
    ).strip()

    if not text:
        return []

    try:
        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            list
        ):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]

    except (
        json.JSONDecodeError,
        TypeError
    ):
        pass

    try:
        parsed = ast.literal_eval(
            text
        )

        if isinstance(
            parsed,
            list
        ):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]

    except (
        ValueError,
        SyntaxError
    ):
        pass

    values = [
        text
    ]

    for separator in [
        "\n",
        "•",
        "|"
    ]:
        split_values = []

        for current_value in values:
            split_values.extend(
                current_value.split(
                    separator
                )
            )

        values = split_values

    return [
        item.strip(
            " -•\t"
        )
        for item in values
        if item.strip(
            " -•\t"
        )
    ]


# ============================================================
# 카드 생성
# ============================================================

def build_link_html(
    link: object
) -> str:
    safe_link = safe_url(
        link
    )

    if not safe_link:
        return (
            '<span style="font-size:10px;color:#94a3b8;">'
            "원문 링크 없음"
            "</span>"
        )

    return (
        f'<a href="{safe_link}" '
        'target="_blank" '
        'rel="noopener noreferrer" '
        'class="btn-link">'
        "원문 보기"
        "</a>"
    )


def build_card_html(
    row: pd.Series,
    is_sg: bool = False
) -> str:

    checkpoints = parse_checkpoints(
        row.get(
            "checkpoints",
            ""
        )
    )

    # --------------------------------------------------------
    # HR 영향도 / 관련 토픽 표시
    # --------------------------------------------------------

    related_topics = get_related_topics(
        row,
        max_topics=3
    )

    topic_text = " · ".join(
        related_topics
    )


    # --------------------------------------------------------
    # 체크포인트
    # --------------------------------------------------------

    checkpoint_items = "".join(
        (
            '<div class="checkpoint-item">'
            f"• {safe_text(checkpoint)}"
            "</div>"
        )
        for checkpoint in checkpoints
    )

    if not checkpoint_items:
        checkpoint_items = (
            '<div class="checkpoint-item">'
            "• 별도 체크포인트가 없습니다."
            "</div>"
        )

    # --------------------------------------------------------
    # 요약
    # --------------------------------------------------------

    summary = safe_multiline_text(
        row.get(
            "summary",
            ""
        ),
        "요약 정보가 없습니다."
    )

    # --------------------------------------------------------
    # 제목
    # --------------------------------------------------------

    raw_title = str(
        row.get(
            "title",
            ""
        )
    )

    raw_title = (
        raw_title
        .replace(
            "[국내]",
            ""
        )
        .replace(
            "[해외]",
            ""
        )
        .strip()
    )

    clean_title = safe_text(
        raw_title,
        "제목 없음"
    )

    # --------------------------------------------------------
    # 날짜
    # --------------------------------------------------------

    date_str = safe_text(
        row.get(
            "date_str",
            ""
        )
    )

    # --------------------------------------------------------
    # 링크
    # --------------------------------------------------------

    link_html = build_link_html(
        row.get(
            "link",
            ""
        )
    )

    # ========================================================
    # 오늘의 스마일게이트
    # ========================================================

    if is_sg:

        return (
            '<div class="sg-card">'

            '<div class="sg-card-header">'
            f'<span class="sg-date-tag">{date_str}</span>'
            f'<span class="sg-title-text" '
            f'title="{clean_title}">'
            f'{clean_title}'
            '</span>'
            '</div>'

            '<div class="sg-card-body">'

            '<div class="summary-title-sg">'
            '주요 요약'
            '</div>'

            f'<div class="summary-box-sg">'
            f'{summary}'
            '</div>'

            f'{link_html}'

            '</div>'
            '</div>'
        )

    # ========================================================
    # 일반 뉴스 카드
    # ========================================================

    return (
        '<div class="news-card">'

        '<div class="card-header">'
        f'<span class="date-tag">{date_str}</span>'
        f'<span class="card-title-text" '
        f'title="{clean_title}">'
        f'{clean_title}'
        '</span>'
        '</div>'

        '<div class="hr-impact-line">'
        f'<span class="hr-impact-topic">'
        f'{safe_text(topic_text)}'
        f'</span>'
        '</div>'

        '<div class="card-body">'

        '<div class="summary-title-normal">'
        '핵심 요약'
        '</div>'

        f'<div class="summary-box">'
        f'{summary}'
        '</div>'

        '<div class="checkpoint-title">'
        '실무 체크포인트'
        '</div>'

        '<div class="checkpoint-box">'
        f'{checkpoint_items}'
        '</div>'

        f'{link_html}'

        '</div>'
        '</div>'
    )


# ============================================================
# 카테고리 렌더링
# ============================================================

def render_category_with_more(
    data_frame: pd.DataFrame,
    display_title: str,
    category_key: str
) -> None:
    category_data = data_frame[
        data_frame["category"]
        == category_key
    ]

    count = len(
        category_data
    )

    st.markdown(
        (
            '<div class="sec-header">'
            '<span class="sec-marker"></span>'
            f"<span>{html.escape(display_title)}</span>"
            f'<span class="sec-count">{count}건</span>'
            "</div>"
        ),
        unsafe_allow_html=True
    )

    if category_data.empty:
        st.markdown(
            (
                '<div class="empty-section-box">'
                "최근 수집된 기사가 없습니다."
                "</div>"
            ),
            unsafe_allow_html=True
        )

        return

    # 기사 5개 이상일 때만 더보기 생성
    if count >= 5:
        top_items = category_data.iloc[
            :4
        ]

        more_items = category_data.iloc[
            4:
        ]

        top_html = "".join(
            build_card_html(
                row
            )
            for _, row
            in top_items.iterrows()
        )

        st.markdown(
            top_html,
            unsafe_allow_html=True
        )

        with st.expander(
            f"+{len(more_items)}개 더보기"
        ):
            more_html = "".join(
                build_card_html(
                    row
                )
                for _, row
                in more_items.iterrows()
            )

            st.markdown(
                more_html,
                unsafe_allow_html=True
            )

    else:
        all_html = "".join(
            build_card_html(
                row
            )
            for _, row
            in category_data.iterrows()
        )

        st.markdown(
            all_html,
            unsafe_allow_html=True
        )


# ============================================================
# 데이터 읽기
# ============================================================

modified_time = get_csv_modified_time()

df = load_data(
    CSV_FILE_PATH,
    modified_time
)


if df.empty:
    st.warning(
        "수집된 뉴스가 없습니다. "
        "`python collector.py`를 먼저 실행하세요."
    )

    st.stop()

# ============================================================
# 사이드바 필터
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">📰 HR 뉴스 레이더</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-subtitle">'
        "HR에 영향을 주는 주요 이슈를 한눈에 살펴보세요."
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("### 🔎 검색")

    search_keyword = st.text_input(
        "기사 검색",
        placeholder="제목, 요약, 주제 검색",
        label_visibility="collapsed"
    )

    st.markdown("### 📌 HR 이슈")

    st.markdown(
        '<div class="topic-chip-label">'
        "관심 있는 이슈를 눌러보세요."
        "</div>",
        unsafe_allow_html=True
    )

    if "selected_hr_topics" not in st.session_state:
        st.session_state.selected_hr_topics = []

    topic_names = list(HR_TOPIC_KEYWORDS.keys()) + [
        "트렌드 · 타사 사례"
    ]
    topic_rows = [
        topic_names[i:i+3]
        for i in range(0, len(topic_names), 3)
    ]

    for topic_row in topic_rows:

        cols = st.columns(len(topic_row))

        for col, topic in zip(cols, topic_row):

            with col:

                is_selected = (
                    topic
                    in st.session_state.selected_hr_topics
                )

                button_label = (
                    f"✓ {topic}"
                    if is_selected
                    else topic
                )

                if st.button(
                    button_label,
                    key=f"topic_{topic}",
                    use_container_width=True
                ):

                    if topic in st.session_state.selected_hr_topics:
                        st.session_state.selected_hr_topics.remove(topic)
                    else:
                        st.session_state.selected_hr_topics.append(topic)

                    st.rerun()

    selected_hr_topics = (
        st.session_state.selected_hr_topics
    )

    st.markdown("### 📅 수집 기간")

    period_options = [
            "전체",
            "7일",
            "30일"
    ]

    selected_period = st.selectbox(
        "수집 기간",
        period_options,
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("### ↕ 정렬")

    sort_option = st.selectbox(
        "정렬 기준",
        [
            "최신순",
            "HR 실무 중요도순"
        ],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")


    total_count = len(df)

    today_str = pd.Timestamp.now(
        tz="Asia/Seoul"
    ).strftime("%Y-%m-%d")

    today_count = (
        pd.to_datetime(
            df["pubDate"],
            errors="coerce"
        )
        .dt.strftime("%Y-%m-%d")
        .eq(today_str)
        .sum()
    )



    st.markdown(
        (
            '<div class="sidebar-summary">'

            '<div class="sidebar-stat">'
            f'<div class="sidebar-stat-number">{total_count}</div>'
            '<div class="sidebar-stat-label">TOTAL</div>'
            '</div>'

            '<div class="sidebar-stat">'
            f'<div class="sidebar-stat-number">{today_count}</div>'
            '<div class="sidebar-stat-label">TODAY</div>'
            '</div>'

            '</div>'
        ),
        unsafe_allow_html=True
    )

# ============================================================
# 오늘의 스마일게이트
# ============================================================

smilegate_data = df[
    df["category"]
    == "오늘의 스마일게이트"
]

if not smilegate_data.empty:
    smilegate_cards = "".join(
        build_card_html(
            row,
            is_sg=True
        )
        for _, row
        in smilegate_data.head(
            5
        ).iterrows()
    )

    smilegate_html = (
        '<div class="sg-container">'
        '<div class="sg-title">'
        "🚀오늘의 스마일게이트"
        "</div>"
        f"{smilegate_cards}"
        "</div>"
    )

else:
    smilegate_html = (
        '<div class="sg-container">'
        '<div class="sg-title">'
        "오늘의 스마일게이트"
        "</div>"
        '<div style="color:#94a3b8;font-size:11px;">'
        "최근 스마일게이트 기사가 없습니다."
        "</div>"
        "</div>"
    )

st.markdown(
    smilegate_html,
    unsafe_allow_html=True
)


# ============================================================
# 필터 적용
# ============================================================

filtered_df = df[
    df["category"]
    != "오늘의 스마일게이트"
].copy()


# ------------------------------------------------------------
# 검색
# ------------------------------------------------------------

if search_keyword.strip():

    keyword = (
        search_keyword
        .strip()
        .lower()
    )

    search_columns = [
        "title",
        "summary",
    ]

    search_mask = pd.Series(
        False,
        index=filtered_df.index
    )

    for column in search_columns:

        if column in filtered_df.columns:

            search_mask = (
                search_mask
                |
                filtered_df[column]
                .astype(str)
                .str.lower()
                .str.contains(
                    keyword,
                    regex=False,
                    na=False
                )
            )

    filtered_df = filtered_df[
        search_mask
    ]

# ------------------------------------------------------------
# HR 이슈 토픽 검색
# ------------------------------------------------------------

if selected_hr_topics:

    topic_mask = filtered_df.apply(
        lambda row: any(
            selected_topic in get_related_topics(
                row,
                max_topics=3
            )
            for selected_topic
            in selected_hr_topics
        ),
        axis=1
    )

    filtered_df = filtered_df[
        topic_mask
    ]

# ------------------------------------------------------------
# 기간
# ------------------------------------------------------------

pub_dates = pd.to_datetime(
    filtered_df["pubDate"],
    errors="coerce",
    utc=True
)

now_kst = pd.Timestamp.now(
    tz="Asia/Seoul"
)

if selected_period == "7일":

    cutoff = (
        now_kst.normalize()
        - pd.Timedelta(days=6)
    )

    filtered_df = filtered_df[
        pub_dates >= cutoff.tz_convert("UTC")
    ]

elif selected_period == "30일":

    cutoff = (
        now_kst.normalize()
        - pd.Timedelta(days=29)
    )

    filtered_df = filtered_df[
        pub_dates >= cutoff.tz_convert("UTC")
    ]

# ------------------------------------------------------------
# 정렬
# ------------------------------------------------------------

if sort_option == "HR 실무 중요도순":

    filtered_df["_sort_score"] = pd.to_numeric(
        filtered_df["hr_relevance"],
        errors="coerce"
    ).fillna(0)

    filtered_df["_sort_date"] = pd.to_datetime(
        filtered_df["pubDate"],
        errors="coerce",
        utc=True
    )

    filtered_df = (
        filtered_df
        .sort_values(
            by=[
                "_sort_score",
                "_sort_date"
            ],
            ascending=[
                False,
                False
            ],
            na_position="last"
        )
        .drop(
            columns=[
                "_sort_score",
                "_sort_date"
            ],
            errors="ignore"
        )
    )

else:

    filtered_df["_sort_date"] = pd.to_datetime(
        filtered_df["pubDate"],
        errors="coerce",
        utc=True
    )

    filtered_df = (
        filtered_df
        .sort_values(
            by="_sort_date",
            ascending=False,
            na_position="last"
        )
        .drop(
            columns=[
                "_sort_date"
            ],
            errors="ignore"
        )
    )

# ============================================================
# 검색 결과 표시
# ============================================================

search_related_topics = set()

if search_keyword.strip():

    for _, row in filtered_df.iterrows():

        related_topics = get_related_topics(row)

        search_related_topics.update(
            related_topics
        )

with st.sidebar:

    result_text = (
        f"{search_keyword.strip()} 검색 결과"
        if search_keyword.strip()
        else "현재 검색 결과"
    )

    st.markdown(
        (
            '<div class="filter-result">'
            f"{result_text} "
            f"<strong>{len(filtered_df)}건</strong>"
            "</div>"
        ),
        unsafe_allow_html=True
    )

st.markdown(
    (
        '<div class="result-count">'
        f"검색 결과 <strong>{len(filtered_df)}건</strong>"
        "</div>"
    ),
    unsafe_allow_html=True
)

if search_keyword.strip() and search_related_topics:

    related_topic_text = " · ".join(
        sorted(search_related_topics)
    )

    st.markdown(
        (
            '<div class="dashboard-summary">'
            f"<strong>{html.escape(search_keyword.strip())}</strong>"
            " 관련 검색 결과 "
            f"<strong>{len(filtered_df)}건</strong>"
            '<span class="summary-divider">|</span>'
            "관련 토픽: "
            f"<strong>{html.escape(related_topic_text)}</strong>"
            "</div>"
        ),
        unsafe_allow_html=True
    )

# ============================================================
# 카테고리 배치
# ============================================================

row1_col1, row1_col2 = st.columns(
    2
)

with row1_col1:
    render_category_with_more(
        filtered_df,
        "HR 제도·조직운영",
        "HR 제도·조직운영"
    )

with row1_col2:
    render_category_with_more(
        filtered_df,
        "노동법·정책·판례",
        "노동법·정책·판례"
    )


st.markdown(
    "<div style='height:22px;'></div>",
    unsafe_allow_html=True
)


row2_col1, row2_col2 = st.columns(
    2
)

with row2_col1:
    render_category_with_more(
        filtered_df,
        "보상·노사관계",
        "보상·노사관계"
    )

with row2_col2:
    render_category_with_more(
        filtered_df,
        "채용·인력운영",
        "채용·인력운영"
    )
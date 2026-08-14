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
        max-width: 1480px;
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
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
       일반 뉴스 카드
       ============================================ */

    .news-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 7px;
        margin-bottom: 8px;
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
        min-height: 32px;
        padding: 6px 10px;
        font-size: 12px;
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
       섹션
       ============================================ */

    .sec-header {
        font-size: 14px;
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
        height: 16px;
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
        "pubDate"
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

    summary = safe_multiline_text(
        row.get(
            "summary",
            ""
        ),
        "요약 정보가 없습니다."
    )

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

    date_str = safe_text(
        row.get(
            "date_str",
            ""
        )
    )

    link_html = build_link_html(
        row.get(
            "link",
            ""
        )
    )

    if is_sg:
        return (
            '<div class="sg-card">'
            '<div class="sg-card-header">'
            f'<span class="sg-date-tag">{date_str}</span>'
            f'<span class="sg-title-text" '
            f'title="{clean_title}">'
            f"{clean_title}"
            "</span>"
            "</div>"
            '<div class="sg-card-body">'
            '<div class="summary-title-sg">'
            "주요 요약"
            "</div>"
            f'<div class="summary-box-sg">{summary}</div>'
            f"{link_html}"
            "</div>"
            "</div>"
        )

    return (
        '<div class="news-card">'
        '<div class="card-header">'
        f'<span class="date-tag">{date_str}</span>'
        f'<span class="card-title-text" '
        f'title="{clean_title}">'
        f"{clean_title}"
        "</span>"
        "</div>"
        '<div class="card-body">'
        '<div class="summary-title-normal">'
        "핵심 요약"
        "</div>"
        f'<div class="summary-box">{summary}</div>'
        '<div class="checkpoint-title">'
        "실무 체크포인트"
        "</div>"
        '<div class="checkpoint-box">'
        f"{checkpoint_items}"
        "</div>"
        f"{link_html}"
        "</div>"
        "</div>"
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
# 카테고리 배치
# ============================================================

row1_col1, row1_col2 = st.columns(
    2
)

with row1_col1:
    render_category_with_more(
        df,
        "HR 제도·조직운영",
        "HR 제도·조직운영"
    )

with row1_col2:
    render_category_with_more(
        df,
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
        df,
        "보상·노사관계",
        "보상·노사관계"
    )

with row2_col2:
    render_category_with_more(
        df,
        "채용·인력운영",
        "채용·인력운영"
    )
from __future__ import annotations

import datetime
import html
import json
import os
import re
import time
import urllib.parse
from collections import defaultdict
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# 경로 / 환경설정
# ============================================================

# 로컬에서 실행시 코드
# BASE_DIR = Path(
#    r"D:\Local developing\HR-news dashboard"
#)

#깃허브에서 실행시 코드
BASE_DIR = Path(__file__).parent

ENV_FILE_PATH = BASE_DIR / ".env"
CSV_FILE_PATH = BASE_DIR / "hr_news.csv"
STATUS_FILE_PATH = BASE_DIR / "collector_status.json"

if ENV_FILE_PATH.exists():
    load_dotenv(dotenv_path=ENV_FILE_PATH)
else:
    load_dotenv() # 특정 경로를 강제하지 않아 시스템 환경변수가 정상 반영됩니다.
NAVER_CLIENT_ID = (
    os.getenv("NAVER_CLIENT_ID")
    or os.getenv("CLIENT_ID")
    or ""
).strip()

NAVER_CLIENT_SECRET = (
    os.getenv("NAVER_CLIENT_SECRET")
    or os.getenv("CLIENT_SECRET")
    or ""
).strip()

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or ""
).strip()

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or ""
).strip()

# [추가] 글자 수와 존재 여부를 출력하여 비밀 키가 정상 주입되었는지 검증합니다.
print(f"[DEBUG] GEMINI_API_KEY 정상 로드 여부: {bool(GEMINI_API_KEY)} (글자수: {len(GEMINI_API_KEY)})")


GEMINI_MODEL_NAME = "gemini-3.1-flash-lite"


# ============================================================
# 기본 설정
# ============================================================

NAVER_DISPLAY_COUNT = 20

# ------------------------------------------------------------
# 매일 오전 9시 KST 기준
#
# 전날 09:00 이상
# 당일 09:00 미만
#
# 기사만 신규 수집합니다.
# ------------------------------------------------------------

COLLECTION_BOUNDARY_HOUR = 9

# 수집 시간대가 지난 뒤 수동 실행하는 경우에도
# 해당 09:00~09:00 구간까지 도달할 수 있도록
# 검색 페이지를 조금 넉넉하게 봅니다.
MAX_SEARCH_PAGES = 5

CLASSIFICATION_BATCH_SIZE = 40

MAX_RAW_CANDIDATES = 300
MAX_CANDIDATES_PER_SEARCH_GROUP = 60

# ------------------------------------------------------------
# 하루 신규 기사 최대 수
#
# 이것은 화면 표시 제한이 아닙니다.
# 과거 데이터는 CSV에 계속 누적됩니다.
# ------------------------------------------------------------

SMILEGATE_DAILY_LIMIT = 10
NORMAL_CATEGORY_DAILY_LIMIT = 10

# ------------------------------------------------------------
# CSV 전체 누적 최대 기사 수
# ------------------------------------------------------------

MAX_STORED_ARTICLES = 200

# 최종 10건을 뽑기 전 중복 검사용 후보 여유분
DEDUP_POOL_MULTIPLIER = 2


KST = datetime.timezone(
    datetime.timedelta(hours=9)
)


CSV_COLUMNS = [
    "category",
    "date_str",
    "title",
    "summary",
    "checkpoints",
    "link",
    "pubDate",
    "collected_at"
]


# ============================================================
# 최종 카테고리
# ============================================================

CATEGORY_SMILEGATE = "오늘의 스마일게이트"
CATEGORY_HR_SYSTEM = "HR 제도·조직운영"
CATEGORY_WORKFORCE = "채용·인력운영"
CATEGORY_LABOR_RELATIONS = "보상·노사관계"
CATEGORY_LAW = "노동법·정책·판례"


CATEGORY_ORDER = [
    CATEGORY_SMILEGATE,
    CATEGORY_LAW,
    CATEGORY_LABOR_RELATIONS,
    CATEGORY_WORKFORCE,
    CATEGORY_HR_SYSTEM
]


# ============================================================
# 검색 그룹
#
# 검색 그룹 != 최종 카테고리
#
# 검색어는 후보 수집용입니다.
# 최종 카테고리는 Gemini가 다시 판단합니다.
# ============================================================

SEARCH_SMILEGATE = "smilegate"
SEARCH_HR_SYSTEM = "hr_system"
SEARCH_WORKFORCE = "workforce"
SEARCH_LABOR_RELATIONS = "labor_relations"
SEARCH_LAW = "labor_law"


SEARCH_GROUPS = {

    SEARCH_SMILEGATE: [
        "스마일게이트",
        "스마일게이트 신작",
        "스마일게이트 사업",
        "스마일게이트 글로벌",
        "스마일게이트 투자",
        "스마일게이트 경영",
        "스마일게이트 AI",
        "스마일게이트 희망스튜디오",
        "스마일게이트 채용",
        "스마일게이트 조직"
    ],

    SEARCH_HR_SYSTEM: [
        "기업 인사제도 개편",
        "기업 평가제도 개편",
        "기업 성과관리 개편",
        "기업 승진제도 개편",
        "기업 직급체계 개편",
        "기업 조직개편 인사",
        "기업 조직문화 개편",
        "기업 근무제도 개편",
        "기업 재택근무 변경",
        "기업 출근제 변경",
        "기업 주4일제",
        "기업 유연근무",
        "기업 HR AI 도입",
        "기업 피플애널리틱스",
        "기업 인재육성 제도",
        "기업 근태관리",
        "기업 근로시간 위반",
        "기업 노동법 위반",
        "기업 육아휴직",
        "기업 임산부 보호"
    ],

    # --------------------------------------------------------
    # 단순 공개채용 / 인력채용은 IT·게임·테크 중심
    #
    # 희망퇴직·구조조정·직무전환 등 구조적인
    # workforce 이슈는 업종 제한 없이 검색
    # --------------------------------------------------------

    SEARCH_WORKFORCE: [
        "IT기업 신입 채용",
        "IT기업 경력 채용",
        "IT기업 채용 전략",
        "IT기업 수시채용",
        "IT기업 채용 방식 변경",
        "IT기업 채용 평가",

        "게임사 신입 채용",
        "게임사 경력 채용",
        "게임사 인재 채용",

        "플랫폼 기업 채용",
        "소프트웨어 기업 채용",
        "AI 기업 채용",
        "테크기업 채용",
        "클라우드 기업 채용",

        "기업 온보딩 제도",
        "기업 이직률",
        "기업 퇴사율",
        "기업 리텐션",

        "기업 인력 감축",
        "기업 희망퇴직",
        "기업 구조조정 인력",
        "기업 직무전환",
        "기업 인력 재배치",
        "기업 재교육 리스킬링"
    ],

    SEARCH_LABOR_RELATIONS: [
        "기업 노사관계",
        "기업 노동조합",
        "기업 임금협상",
        "기업 임단협",
        "기업 파업",
        "기업 성과급 갈등",
        "기업 성과급 제도",
        "기업 임금체계 노조",
        "기업 보상 갈등",
        "기업 복리후생 변경",
        "기업 노조 교섭"
    ],

    SEARCH_LAW: [
        "고용노동부 기업 인사",
        "근로기준법 기업",
        "노동법 개정 기업",
        "노동 판례 기업",
        "통상임금 판결",
        "근로자성 판결",
        "부당해고 판결",
        "직장 내 괴롭힘 판례",
        "근로시간 법 개정",
        "육아휴직 법 개정",
        "연차 판례",
        "노조법 기업",
        "산업안전보건법 기업",
        "고용 차별 판결"
    ]
}


# ============================================================
# 명백한 비대상 기사
#
# 스마일게이트 검색에는 적용하지 않습니다.
# ============================================================

HARD_EXCLUDE_KEYWORDS = [

    # --------------------------------------------------------
    # 개인 / 연예 / 무관
    # --------------------------------------------------------

    "재산분할",
    "이혼소송",
    "연예인",
    "드라마 출연",
    "프로야구 선수",
    "프로축구 선수",
    "경마",
    "로또",
    "개인택시",

    # --------------------------------------------------------
    # 공무원 단순 인사 / 공공조직 사례
    # --------------------------------------------------------

    "공무원 인사발령",
    "공무원 인사 발령",
    "공무원 전보 인사",
    "공무원 승진 인사",
    "인사 명단",

    "공직사회",
    "적극행정",
    "행정혁신",
    "공무원 조직문화",
    "공무원 성과관리",

    # --------------------------------------------------------
    # 인물 / 오너 / 경영승계
    # --------------------------------------------------------

    "Who Is",
    "경영2세",
    "경영 2세",
    "경영3세",
    "경영 3세",
    "오너2세",
    "오너 2세",
    "오너3세",
    "오너 3세",
    "가업승계",

    # --------------------------------------------------------
    # 출판 / 책 홍보
    # --------------------------------------------------------

    "신간 소개",
    "책 출간",
    "도서 출간",
    "북콘서트",

    # 기타
    "부고",
]
HARD_EXCLUDE_KEYWORDS += [
    # 안보 / 범죄 / 보안
    "북한 IT 인력",
    "북한 it 인력",
    "위장취업",
    "취업 사기",
    "취업사기",
    "간첩",
    "스파이",
    "FBI",
    "해킹",

    # 취업시장 일반론
    "청년 취업난",
    "취업 절벽",
    "취업전쟁",
]

# ============================================================
# 일반 기업 HR과 무관한 특정 영업채널 모집
# ============================================================

NON_CORPORATE_RECRUITMENT_NOISE = [

    "보험설계사",
    "보험 설계사",

    "설계사 영입",
    "설계사 채용 경쟁",
    "설계사 리크루팅",
    "설계사 정착지원금",
    "설계사 스카우트",

    "GA 설계사",

    "보험대리점 설계사",
    "보험대리점 리크루팅",

    "FC 모집",
    "FC 영입",

    "재무설계사 모집",
    "재무설계사 영입",

    "영업조직 리크루팅 수당",
]


# ============================================================
# HTTP 세션
# ============================================================

def create_http_session() -> requests.Session:

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ],
        allowed_methods=["GET"],
        raise_on_status=False
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter
    )

    session.mount(
        "http://",
        adapter
    )

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/150.0 Safari/537.36"
        )
    })

    return session


HTTP_SESSION = create_http_session()


# ============================================================
# 상태 파일
# ============================================================

def write_status(
    success: bool,
    message: str,
    article_count: int = 0
) -> None:

    status = {
        "success": success,
        "message": message,
        "article_count": article_count,
        "updated_at": (
            datetime.datetime
            .now(KST)
            .isoformat()
        )
    }

    try:
        STATUS_FILE_PATH.write_text(
            json.dumps(
                status,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    except OSError:
        pass


# ============================================================
# 문자열 처리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:
        return ""

    text = html.unescape(
        str(value)
    )

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = re.sub(
        (
            r"\[(단독|포토|기획|속보|인사|부음|국내|해외|"
            r"종합|영상|인터뷰|현장)\]"
        ),
        "",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def normalize_title(
    title: str
) -> str:

    text = clean_text(
        title
    ).lower()

    text = re.sub(
        r"\[[^\]]+\]",
        " ",
        text
    )

    for word in [
        "단독",
        "속보",
        "종합",
        "포토",
        "영상",
        "기획",
        "인터뷰",
        "현장"
    ]:
        text = text.replace(
            word,
            " "
        )

    return re.sub(
        r"[^0-9a-zA-Z가-힣]",
        "",
        text
    )


def normalize_url(
    url: str
) -> str:

    if not url:
        return ""

    try:
        parts = urlsplit(
            url.strip()
        )

        query = [
            (key, value)
            for key, value in parse_qsl(
                parts.query,
                keep_blank_values=True
            )
            if not (
                key.lower().startswith("utm_")
                or key.lower() in {
                    "ref",
                    "source",
                    "campaign",
                    "fbclid",
                    "gclid",
                    "sc"
                }
            )
        ]

        path = re.sub(
            r"/+$",
            "",
            parts.path
        )

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(query),
            ""
        ))

    except ValueError:
        return url.strip()


def contains_hard_exclude(
    title: str,
    description: str
) -> bool:

    target = (
        f"{title} {description}"
    ).lower()

    return any(
        keyword.lower() in target
        for keyword in HARD_EXCLUDE_KEYWORDS
    )


def contains_non_corporate_recruitment_noise(
    title: str,
    description: str
) -> bool:

    target = (
        f"{title} {description}"
    ).lower()

    return any(
        keyword.lower() in target
        for keyword in NON_CORPORATE_RECRUITMENT_NOISE
    )


# ============================================================
# 날짜 처리
# ============================================================

def parse_pub_date(
    value: str
) -> Optional[datetime.datetime]:

    try:
        parsed = parsedate_to_datetime(
            value
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=KST
            )

        return parsed.astimezone(
            KST
        )

    except (
        TypeError,
        ValueError,
        OverflowError
    ):
        return None


def get_collection_window(
    now: datetime.datetime
) -> Tuple[
    datetime.datetime,
    datetime.datetime
]:
    """
    KST 기준 수집 시간 구간.

    예:
    8월 13일 09:00 이후 실행
    → 8월 12일 09:00 이상
      8월 13일 09:00 미만

    오전 9시 전에 수동 실행하면
    아직 당일 구간이 종료되지 않았으므로
    그 이전에 완결된 24시간 구간을 사용합니다.
    """

    now = now.astimezone(
        KST
    )

    today_boundary = now.replace(
        hour=COLLECTION_BOUNDARY_HOUR,
        minute=0,
        second=0,
        microsecond=0
    )

    if now >= today_boundary:
        window_end = today_boundary

    else:
        window_end = (
            today_boundary
            - datetime.timedelta(
                days=1
            )
        )

    window_start = (
        window_end
        - datetime.timedelta(
            days=1
        )
    )

    return (
        window_start,
        window_end
    )


# ============================================================
# 네이버 뉴스 검색
# ============================================================

def search_naver_news(
    keyword: str,
    headers: Dict[str, str],
    start: int
) -> Tuple[
    bool,
    List[Dict[str, Any]]
]:

    query = urllib.parse.quote(
        keyword
    )

    url = (
        "https://openapi.naver.com/"
        "v1/search/news.json"
        f"?query={query}"
        f"&display={NAVER_DISPLAY_COUNT}"
        f"&start={start}"
        "&sort=date"
    )

    try:
        response = HTTP_SESSION.get(
            url,
            headers=headers,
            timeout=(5, 15),
            verify=False
        )

    except requests.RequestException as error:
        print(
            f"  ❌ 네이버 API 연결 실패: {error}"
        )
        return False, []

    if response.status_code != 200:

        try:
            error_body = response.json()

        except ValueError:
            error_body = response.text[
                :300
            ]

        print(
            "  ❌ 네이버 API 오류 "
            f"HTTP {response.status_code}: "
            f"{error_body}"
        )

        return False, []

    try:
        payload = response.json()

    except ValueError as error:
        print(
            f"  ❌ 네이버 API JSON 분석 실패: {error}"
        )

        return False, []

    items = payload.get(
        "items",
        []
    )

    if not isinstance(
        items,
        list
    ):
        return True, []

    return True, items


# ============================================================
# 기사 원문
# ============================================================

@lru_cache(maxsize=256)
def fetch_article_page(
    url: str
) -> Tuple[
    str,
    str
]:

    if not url:
        return "", ""

    try:
        response = HTTP_SESSION.get(
            url,
            timeout=(5, 12),
            verify=False,
            allow_redirects=True
        )

        if response.status_code != 200:
            return "", ""

        content_type = response.headers.get("Content-Type", "").lower()

        if "charset=euc-kr" in content_type or "charset=ks_c_5601-1987" in content_type:
            response.encoding = "euc-kr"
        elif "charset=utf-8" in content_type:
            response.encoding = "utf-8"
        else:
            # 대부분의 최신 국내 뉴스 사이트는 UTF-8
            response.encoding = "utf-8"

        page_html = response.text

        soup = BeautifulSoup(
            page_html,
            "html.parser"
        )

        original_title = ""

        for selector in [
            'meta[property="og:title"]',
            'meta[name="twitter:title"]'
        ]:
            tag = soup.select_one(
                selector
            )

            if not tag:
                continue

            original_title = clean_text(
                tag.get(
                    "content",
                    ""
                )
            )

            if original_title:
                break

        if (
            not original_title
            and soup.title
            and soup.title.string
        ):
            original_title = clean_text(
                soup.title.string
            )

        body = ""

        if trafilatura is not None:

            try:
                body = (
                    trafilatura.extract(
                        page_html,
                        include_comments=False,
                        include_tables=False
                    )
                    or ""
                ).strip()

            except Exception:
                body = ""

        if len(body) < 100:

            selectors = [
                "article",
                ".article_body",
                "#articleBody",
                "#articeBody",
                "#newsCollapse",
                ".news_body",
                ".article-view-content-div",
                ".article_view",
                ".newsct_article"
            ]

            for selector in selectors:

                target = soup.select_one(
                    selector
                )

                if target is None:
                    continue

                candidate = clean_text(
                    target.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(candidate) >= 100:
                    body = candidate
                    break

        return (
            original_title,
            body
        )

    except Exception as error:

        print(
            f"   └ 원문 접속 실패: {error}"
        )

        return "", ""


# ============================================================
# 후보 수집
# ============================================================

def collect_raw_candidates(
    headers: Dict[str, str],
    window_start: datetime.datetime,
    window_end: datetime.datetime
) -> Tuple[
    List[Dict[str, Any]],
    int
]:

    candidates: List[
        Dict[str, Any]
    ] = []

    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()

    successful_api_calls = 0
    next_id = 1

    for search_group, keywords in (
        SEARCH_GROUPS.items()
    ):

        group_candidate_count = 0

        print(
            f"\n📂 후보 검색 그룹: [{search_group}]"
        )

        for keyword in keywords:

            print(
                f"  🔍 검색어: {keyword}"
            )

            accepted_count = 0

            for page_index in range(
                MAX_SEARCH_PAGES
            ):

                start = (
                    page_index
                    * NAVER_DISPLAY_COUNT
                    + 1
                )

                success, items = search_naver_news(
                    keyword,
                    headers,
                    start
                )

                if success:
                    successful_api_calls += 1

                if not items:
                    break

                # 이 페이지에서 이미 window_start보다
                # 오래된 기사까지 도달했는지 확인
                page_reached_before_window = False

                for item in items:

                    pub_date_raw = str(
                        item.get(
                            "pubDate",
                            ""
                        )
                    )

                    pub_dt = parse_pub_date(
                        pub_date_raw
                    )

                    if pub_dt is None:
                        continue

                    if pub_dt < window_start:
                        page_reached_before_window = True
                        continue

                    # 실행시점이 오전 9시보다 늦을 경우,
                    # 오늘 09:00 이후 기사는 다음 수집분이므로 제외
                    if pub_dt >= window_end:
                        continue

                    title = clean_text(
                        item.get(
                            "title",
                            ""
                        )
                    )

                    description = clean_text(
                        item.get(
                            "description",
                            ""
                        )
                    )

                    link = (
                        item.get(
                            "originallink"
                        )
                        or item.get(
                            "link"
                        )
                        or ""
                    ).strip()

                    if not title:
                        continue

                    # 스마일게이트는 HR 여부와 무관한
                    # 회사 소식이므로 HR용 필터를 적용하지 않습니다.
                    if (
                        search_group
                        != SEARCH_SMILEGATE
                    ):

                        if contains_hard_exclude(
                            title,
                            description
                        ):
                            continue

                        if (
                            contains_non_corporate_recruitment_noise(
                                title,
                                description
                            )
                        ):
                            continue

                    normalized_url = normalize_url(
                        link
                    )

                    normalized_title = normalize_title(
                        title
                    )

                    if (
                        normalized_url
                        and normalized_url
                        in seen_urls
                    ):
                        continue

                    if (
                        normalized_title
                        and normalized_title
                        in seen_titles
                    ):
                        continue

                    candidate = {
                        "id": next_id,
                        "search_group": search_group,
                        "search_keyword": keyword,
                        "title": title,
                        "description": description,
                        "link": link,
                        "normalized_url": (
                            normalized_url
                        ),
                        "normalized_title": (
                            normalized_title
                        ),
                        "pubDate": pub_date_raw,
                        "pub_dt": pub_dt
                    }

                    candidates.append(
                        candidate
                    )

                    group_candidate_count += 1
                    accepted_count += 1

                    if normalized_url:
                        seen_urls.add(
                            normalized_url
                        )

                    if normalized_title:
                        seen_titles.add(
                            normalized_title
                        )

                    next_id += 1

                    if (
                        len(candidates)
                        >= MAX_RAW_CANDIDATES
                    ):
                        break

                if (
                    len(candidates)
                    >= MAX_RAW_CANDIDATES
                ):
                    break

                # 원하는 시간구간보다 더 과거까지 내려왔으면
                # 다음 페이지는 볼 필요가 없음
                if page_reached_before_window:
                    break

                # 한 검색어에서 이미 어느 정도 확보했다면
                # 다른 검색어 다양성을 위해 다음 검색어로 이동
                if accepted_count >= 6:
                    break

            print(
                f"    └ 신규 후보 "
                f"{accepted_count}건"
            )

            if (
                group_candidate_count
                >= MAX_CANDIDATES_PER_SEARCH_GROUP
            ):
                break

        if (
            len(candidates)
            >= MAX_RAW_CANDIDATES
        ):
            break

    candidates.sort(
        key=lambda article: (
            article["pub_dt"]
        ),
        reverse=True
    )

    return (
        candidates,
        successful_api_calls
    )


# ============================================================
# Gemini 공통
# ============================================================

def extract_gemini_text(
    response: Any
) -> str:

    text_parts: List[str] = []

    candidates = (
        getattr(
            response,
            "candidates",
            None
        )
        or []
    )

    for candidate in candidates:

        content = getattr(
            candidate,
            "content",
            None
        )

        if content is None:
            continue

        parts = (
            getattr(
                content,
                "parts",
                None
            )
            or []
        )

        for part in parts:

            part_text = getattr(
                part,
                "text",
                None
            )

            if part_text:
                text_parts.append(
                    str(part_text)
                )

    if text_parts:
        return "\n".join(
            text_parts
        )

    try:
        return (
            getattr(
                response,
                "text",
                ""
            )
            or ""
        )

    except Exception:
        return ""


def parse_gemini_json(
    response_text: str
) -> Dict[str, Any]:

    text = response_text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    start = text.find(
        "{"
    )

    if start == -1:
        raise ValueError(
            "Gemini 응답에서 JSON 시작을 찾지 못했습니다."
        )

    decoder = json.JSONDecoder()

    try:
        data, _ = decoder.raw_decode(
            text[start:]
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Gemini JSON 분석 실패: {error}"
        ) from error

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            "Gemini 응답이 JSON 객체가 아닙니다."
        )

    return data


def call_gemini_json(
    prompt: str,
    temperature: float = 0.1
) -> Optional[Dict[str, Any]]:

    if (
        not GEMINI_API_KEY
        or genai is None
        or types is None
    ):
        return None

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception as error:

        print(
            f"   └ Gemini 클라이언트 생성 실패: {error}"
        )

        return None

    max_attempts = 4

    for attempt in range(
        max_attempts
    ):

        attempt_number = (
            attempt + 1
        )

        try:

            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type=(
                        "application/json"
                    ),
                    temperature=temperature
                )
            )

            response_text = extract_gemini_text(
                response
            )

            if not response_text.strip():
                raise ValueError(
                    "Gemini 응답 내용이 비어 있습니다."
                )

            return parse_gemini_json(
                response_text
            )

        except Exception as error:

            error_message = str(
                error
            )

            print(
                "   └ Gemini 호출 실패 "
                f"({attempt_number}/{max_attempts}): "
                f"{error_message}"
            )

            if (
                attempt_number
                >= max_attempts
            ):
                break

            if (
                "503" in error_message
                or "UNAVAILABLE"
                in error_message
                or "high demand"
                in error_message.lower()
            ):

                wait_seconds = (
                    5
                    * (2 ** attempt)
                )

            elif (
                "429" in error_message
                or "RESOURCE_EXHAUSTED"
                in error_message
                or "quota"
                in error_message.lower()
            ):

                wait_seconds = (
                    10
                    * (2 ** attempt)
                )

            elif (
                "404" in error_message
                or "NOT_FOUND"
                in error_message
            ):
                break

            else:
                wait_seconds = 3

            print(
                f"   ⏳ {wait_seconds}초 후 재시도"
            )

            time.sleep(
                wait_seconds
            )

    return None


# ============================================================
# 분류 프롬프트
# ============================================================

def build_classification_prompt(
    batch: List[Dict[str, Any]]
) -> str:

    article_payload = []

    for article in batch:
        article_payload.append({
            "id": article["id"],
            "title": article["title"],
            "description": article["description"],
            "search_keyword": article["search_keyword"],
            "search_group": article["search_group"],
            "date": article["pub_dt"].strftime(
                "%Y-%m-%d %H:%M"
            )
        })

    return f"""
당신은 대한민국 민간기업 HR팀에서
매일 아침 팀원들에게 공유할 뉴스를 고르는
매우 엄격한 인간 편집자입니다.

목표는 HR 관련 기사를 많이 모으는 것이 아닙니다.

목표는 다음 질문에 명확하게 YES인 기사만 남기는 것입니다.

"이 기사를 우리 회사 HR팀 단톡방에 공유했을 때
동료가 '이건 업무 때문에 알아야 했다'고 생각할까?"

조금이라도 애매하면 include=false입니다.

좋은 기사가 없으면 0건이어도 됩니다.
카테고리별 기사 수를 절대 채우려고 하지 마세요.

search_keyword와 search_group은
검색 과정에서 사용한 힌트일 뿐이며
최종 판단 근거가 아닙니다.

[허용 카테고리]

{json.dumps(CATEGORY_ORDER, ensure_ascii=False)}


============================================================
STEP 1. 오늘의 스마일게이트
============================================================

가장 먼저 다음 질문을 판단합니다.

"이 기사의 핵심 주어와 핵심 사건의 당사자가
스마일게이트 또는 스마일게이트의
게임·서비스·재단·조직인가?"

명확하게 YES인 경우에만
category="오늘의 스마일게이트"를 검토합니다.

HR 관련 여부는 상관없습니다.

포함 가능:

- 스마일게이트 게임 및 신작
- 라이브 서비스의 주요 변화
- 주요 사업전략
- 글로벌 사업
- 주요 투자 및 유통
- AI·기술
- 채용·조직
- 경영
- ESG·사회공헌
- 주요 파트너십
- 핵심 IP의 주요 성과

반드시 제외:

- 투자받은 회사가 기사 주인공이고
  스마일게이트인베스트먼트는 투자자 중 하나

- 여러 게임사의 신작·실적·사업을 묶은 기사

- 제목의 핵심 주어가
  게임업계, 게임사들, 국내 게임사,
  MMORPG 시장, e스포츠 업계,
  게임시장 등 산업 전체인 기사

- 여러 회사 이름이 병렬로 등장하며
  스마일게이트가 여러 사례 중 하나인 기사

- 게임시장 전망
- 업계 실적 비교
- 게임전시회 일반 기사
- e스포츠 산업 일반 기사
- 이용자 트렌드 기사
- 장르 트렌드 기사
- 카드뉴스형 산업 콘텐츠
- 묶음기사 속 작은 한 꼭지

예:

"스마일게이트 북미 시장 공략 가속"
→ 포함

"스마일게이트 크로스파이어, EWC 정식 종목"
→ 포함

"스마일게이트 퓨처랩, 신규 프로그램 시작"
→ 포함


"자동사냥 넘어 무접속 성장으로…MMORPG 문법 바뀐다"
→ 제외. MMORPG 시장 변화가 주제다.

"하루 종일·밤샘 게임은 이제 옛말…게임업계 라이트 유저로"
→ 제외. 게임업계 트렌드 기사다.

"크래프톤·스마일게이트·펄어비스, 이용자와 개발자 접점 키운다"
→ 제외. 여러 회사 사례를 묶은 기사다.

"게임업계 2Q 성적표"
→ 제외. 업계 실적 분석이다.

스마일게이트 기사로 통과하면
이후 일반 HR 심사는 하지 않습니다.


============================================================
STEP 2. HR 기사 자격심사
============================================================

스마일게이트 기사가 아닌 경우
카테고리를 고르기 전에 반드시 자격심사를 합니다.

다음 질문에 명확하게 YES여야 합니다.

"민간기업 HR·인사·노무 담당자가
자신의 담당 업무 때문에 읽어야 하는가?"

기사의 핵심 사건 자체가 다음 중 하나여야 합니다.

- 실제 인사제도 변경
- 실제 평가제도 변경
- 실제 성과관리 변경
- 실제 승진·직급제도 변경
- 실제 근무제도 변경
- 실제 채용방식·선발기준 변경
- 실제 인력계획 변경
- 실제 희망퇴직
- 실제 구조조정
- 실제 인력감축
- 실제 인력재배치
- 실제 직무전환
- 실제 리스킬링
- 실제 보상제도 변경
- 실제 노조·임단협·노사분쟁
- 민간기업에 적용되는 노동법
- 민간기업에 적용되는 정부 고용정책
- 법원·노동위원회의 HR 관련 판단
- 실제 기업 내부 HR AI 적용
- 실제 기업 내부 피플애널리틱스 적용

다음도 HR 실무 기사입니다.

- 실제 기업의 노동법 위반 의혹
- 실제 기업의 노무관리 실패 사례
- 실제 기업의 근태관리 문제
- 실제 기업의 근로시간 위반
- 실제 기업의 임산부·육아휴직 보호 위반
- 실제 기업의 직장 내 괴롭힘 사건
- 실제 기업의 인사감사·노무 리스크 사례

이러한 기사는
법 개정이나 판결이 아니더라도

HR 담당자가
우리 회사도 점검해야 하는 사례라면
include=true를 검토합니다.

다음 정도의 간접 연결은 부족합니다.

- HR도 참고할 수 있다
- 직원이 등장한다
- 채용이라는 단어가 있다
- AI가 일자리에 영향을 미친다
- 청년고용과 관련 있다
- 인력이 부족하다는 기사다
- 기업 경영에 참고할 수 있다

기사 자체가 HR 실무 사건이어야 합니다.


============================================================
STEP 3. 강제 제외
============================================================

아래 유형은 HR 키워드가 있더라도
원칙적으로 include=false입니다.


[제품·서비스 홍보]

- HR 앱
- AI 앱
- HR 솔루션
- AI 솔루션
- SaaS
- ERP
- 그룹웨어
- 채용 플랫폼 기능
- 제품 기능 소개
- 솔루션 업데이트

예:
"오라클, HR용 AI 앱 8종 공개"
→ 제외


[행사·협약·후원]

- 경진대회
- 행사 개최
- 후원
- 대학 행사
- 세미나
- 웨비나
- 포럼 개최 알림
- MOU
- 업무협약

예:
"포티투마루, AI·SW중심대학 경진대회 후원"
→ 제외


[홍보·인증]

- GPTW
- 일하기 좋은 기업
- 조직문화 인증
- 기업문화 인증
- 수상
- 브랜드 홍보

예:
"GPTW 일하기 좋은 기업 인증"
→ 제외


[컨설팅·교육]

- 정부지원 컨설팅
- HR 컨설팅 서비스
- 교육과정 모집
- 교육 프로그램 홍보

예:
"정부지원 인사 컨설팅 실시"
→ 제외


[경영진·오너]

- 대표이사 선임
- 회장 선임
- 임원 선임
- 임원 퇴사
- 임원 이탈
- CEO 교체
- 경영진 이동
- 경영 2세
- 경영 3세
- 오너 일가
- 후계구도
- 경영권 승계
- CEO 개인 프로필

일반 직원 대상
희망퇴직·구조조정·대규모 인력변동과
임원 개인 이동을 혼동하지 마세요.


[책·콘텐츠]

- 신간
- 책 광고
- HR 책 소개
- 저자 인터뷰
- 북콘서트
- 자기계발
- 카드뉴스
- 일반 칼럼

단,

노동법·판례를 구체적으로 설명하고
실무 대응방법이 명확한 전문 노무·법률 기고는
포함할 수 있습니다.


[사설·오피니언]

제목이나 형식이
사설·오피니언이고
새로운 법령·판결·공식 결정 자체보다
주장과 평가가 핵심이면 제외합니다.


[산업·경영 일반]

- 기업 실적
- 주가
- 시장점유율
- 산업 경쟁
- 기술 경쟁
- 제품 경쟁
- 투자
- IPO
- M&A 자체
- 시장 전망
- 산업 전망

예:
"TSMC 독주 속 삼성-인텔 파운드리 2위 다툼"
→ 제외


[취준생·일자리 일반론]

- 취준생 대상 기사
- 합격하려면 무엇을 해야 한다
- 취업 성공법
- 자기소개서
- 지원자 대응법
- 채용시장에서 살아남는 법
- 일반 취업난
- 청년 일자리 담론
- 일반 고용통계

예:
"AI 잘 쓰는 사람이 합격한다"
→ 실제 특정 기업의 채용제도 변경이 아니라면 제외


[보안·범죄]

- 북한 IT 인력
- 위장취업
- 취업사기
- FBI 수사
- 해킹
- 사이버보안
- 스파이
- 간첩

채용 때 참고할 수 있다는 이유로
HR 뉴스가 되지 않습니다.


[공공조직 운영]

- 공직사회 조직문화
- 지자체 조직운영
- 지자체 회의문화
- 행정혁신
- 적극행정
- 공무원 성과관리

예:
"양주시, 보고보다 해결 중심으로 일하는 방식 개편"
→ 제외


[업계·협회의 주장]

업계단체·협회·경제단체가

- 지원이 필요하다
- 정부가 제도를 바꿔야 한다
- 부담을 줄여야 한다

등의 요구만 하는 기사는 제외합니다.

실제 정부 결정,
실제 법 개정,
실제 기업 제도 시행이 있어야 합니다.

다만

기업 내부에서 실제 발생한
노무관리 실패 사례

노동법 위반 의혹

근태조작

근무기록 조작

임산부 보호 위반

육아휴직 불이익

등은

실제 기업 HR 운영 사례이므로
제외하지 않습니다.


============================================================
STEP 4. 채용 특별 기준
============================================================

단순 공개채용·신입채용·경력채용 자체가 핵심이면
IT·게임·테크 기업만 포함할 수 있습니다.

IT·게임·테크 범위:

- 게임사
- 플랫폼
- 인터넷
- 소프트웨어
- AI
- 클라우드
- IT서비스
- 주요 테크기업

예:

"게임사 신입 공개채용"
→ 포함 검토 가능

"플랫폼 기업, 개발자 채용평가 변경"
→ 포함 가능


다음은 제외:

- 보험사 영업직 모집
- 판매직 모집
- 생산직 단순 채용
- 영업사원 모집
- 일반 비IT기업의 단순 공개채용

단,

다음은 업종 제한 없이 판단합니다.

- 희망퇴직
- 구조조정
- 대규모 감원
- 인력재배치
- 직무전환
- 리스킬링
- AI 도입에 따른 실제 조직·인력구조 변화


============================================================
STEP 5. 실무가치
============================================================

일반 HR 기사만 평가합니다.

hr_relevance:

90~100
HR·인사·노무 업무가 기사 핵심

80~89
HR 실무와 매우 직접적

70~79
관련은 있지만 간접적

0~69
HR 브리핑 부적합


practical_value:

90~100
즉시 사내 규정·프로세스 점검 필요

80~89
제도 설계·운영에 매우 유용

75~79
실무 참고 가치 충분

0~74
팀 공유 수준의 가치 부족


일반 HR 기사는 반드시

hr_relevance >= 80
AND
practical_value >= 75

를 만족해야 합니다.


============================================================
STEP 6. 카테고리
============================================================

자격심사를 통과한 기사만 분류합니다.


============================================================
카테고리 경계 판단의 핵심 원칙
============================================================

카테고리는 기사에 등장하는 키워드가 아니라
"가장 중요한 변화의 대상"을 기준으로 결정합니다.

다음 두 질문을 먼저 비교합니다.

Q1.

"사람 자체의 규모·이동·채용·퇴직·직무가 바뀌는가?"

YES
→ 채용·인력운영

Q2.

"사람을 관리하는 규칙·제도·일하는 방식이 바뀌는가?"

YES
→ HR 제도·조직운영


[핵심 구분]

사람의 이동과 구성 변화
→ 채용·인력운영

사람을 관리하는 제도와 운영방식 변화
→ HR 제도·조직운영


키워드가 겹치더라도
기사의 핵심 사건을 기준으로 하나만 선택합니다.

"채용"이라는 단어가 있다고
무조건 채용·인력운영이 아닙니다.

"조직"이라는 단어가 있다고
무조건 HR 제도·조직운영이 아닙니다.

"AI"라는 단어가 있다고
무조건 HR 제도·조직운영이 아닙니다.

"리스킬링"이라는 단어가 있다고
무조건 채용·인력운영이 아닙니다.


[노동법·정책·판례]

핵심이 외부 법·제도·공식 정책·법적 판단

- 노동법 개정
- 시행령·시행규칙
- 정부 고용정책
- 노동부 공식 지침
- 법원 판결
- 노동위원회 판단
- 근로자성
- 통상임금
- 부당해고
- 근로시간
- 육아휴직
- 연차
- 직장 내 괴롭힘
- 노조법
- 산업안전
- 고용 차별


[보상·노사관계]

실제 기업의 보상 또는 노사관계

- 임금
- 성과급
- 임금협상
- 임단협
- 노동조합
- 단체교섭
- 파업
- 쟁의
- 노사갈등
- 복리후생

다음 키워드가 핵심이면
무조건 보상·노사관계를 우선합니다.

- 노조
- 임단협
- 단체교섭
- 고용보장
- 쟁의
- 파업
- 노동조합 요구

AI
채용
인력
보다 우선합니다.


[채용·인력운영]

핵심 질문:

"회사가 사람을 뽑거나, 내보내거나,
인력의 규모·배치·직무를 실제로 바꾸는가?"

즉,
"사람의 이동과 구성 변화"가 핵심인 기사입니다.

포함:

- IT·게임·테크 기업의 채용
- 채용 규모 확대·축소
- 채용전형 변경
- 채용평가 방식 변경
- 신입·경력 채용
- 온보딩
- 희망퇴직
- 명예퇴직
- 구조조정
- 인력감축
- 대규모 해고
- 인력재배치
- 직무전환
- 조직 간 인력 이동
- AI 도입에 따른 실제 인력구조 변화
- 리스킬링
- 실제 인력운영 방식 변경

판단 기준:

"이 기사의 핵심이 사람의 수, 이동, 배치,
채용 또는 직무 변화인가?"

YES
→ 채용·인력운영


[채용평가 구분]

채용 전 평가·선발 기준의 변화
→ 채용·인력운영

입사 후 직원의 평가·성과평가 제도의 변화
→ HR 제도·조직운영


[리스킬링 구분]

리스킬링이라는 단어만으로
카테고리를 결정하지 않습니다.

실제 직무전환·인력재배치가 핵심이면
→ 채용·인력운영

교육·역량개발·인재육성 제도 자체가 핵심이면
→ HR 제도·조직운영

예:

"A사, AI 전환 위해 직원 500명 직무전환"
→ 채용·인력운영

"A사, 전 직원 대상 AI 리스킬링 교육 도입"
→ HR 제도·조직운영


산업 인력수요 전망이나
미래 직업 전망은 제외합니다.


[HR 제도·조직운영]

핵심 질문:

"회사가 사람을 관리하고 일하게 하는
규칙·제도·방식을 실제로 바꾸는가?"

즉,
"사람을 어떻게 관리하고 운영하는가"가
핵심인 기사입니다.

포함:

- 평가제도
- 성과관리
- 승진
- 직급
- 인사제도
- 조직설계
- 조직문화
- 근무제도
- 재택근무
- 출근정책
- 주4일제
- 유연근무
- 근로시간 운영방식
- 인재육성
- 교육·역량개발 제도
- 실제 사내 HR AI 적용
- 실제 피플애널리틱스 적용

판단 기준:

"이 기사의 핵심이
사람을 어떻게 평가·관리·육성하고,
어떻게 일하게 할 것인지에 대한
회사 내부 제도나 운영방식의 변화인가?"

YES
→ HR 제도·조직운영


[조직개편 구분]

조직개편이라는 단어만으로
카테고리를 결정하지 않습니다.

조직개편으로 인력 규모·배치·직무 이동이
발생하는 것이 핵심이면
→ 채용·인력운영

조직 운영체계·평가체계·관리방식의 변화가
핵심이면
→ HR 제도·조직운영

예:

"A사, 조직개편으로 300명 인력 재배치"
→ 채용·인력운영

"A사, 조직개편과 함께 평가체계 전면 개편"
→ HR 제도·조직운영


[AI 관련 분류 기준]

AI라는 단어 자체는
카테고리 판단 근거가 아닙니다.

AI 도입으로 실제 채용·감원·인력재배치·직무전환이
발생하는 것이 핵심이면
→ 채용·인력운영

AI를 평가·인사관리·피플애널리틱스 등에
실제 적용하는 것이 핵심이면
→ HR 제도·조직운영

AI가 일자리를 대체할 것이다,
AI가 미래 직업을 바꿀 것이다,
AI 시대 인재상 등의 일반적인 전망은
HR 기사로 인정하지 않습니다.


[인재육성 구분]

채용 후 직원의 교육·역량개발·육성 제도가
핵심이면
→ HR 제도·조직운영

단,
교육의 결과로 실제 직무전환·인력재배치가 발생하고
그 인력 변화가 기사의 핵심 사건이면
→ 채용·인력운영

============================================================
STEP 7. 카테고리 우선순위
============================================================

1. 스마일게이트 자체 주요 기사
→ 오늘의 스마일게이트

2. 외부 법·정책·공식 결정·법적 판단이 핵심
→ 노동법·정책·판례

3. 임금·성과급·노조·임단협·교섭·파업 등
돈 또는 노사관계가 핵심
→ 보상·노사관계

4. 사람의 채용·퇴직·감축·배치·직무 이동이 핵심
→ 채용·인력운영

5. 평가·성과관리·승진·근무제도·조직문화·
인재육성·HR AI 등
사람을 관리하고 운영하는 제도가 핵심
→ HR 제도·조직운영


[중요]

채용·인력운영과 HR 제도·조직운영이
동시에 등장하는 경우가 많습니다.

이때는 키워드 개수가 아니라
"기사의 핵심 변화가 무엇인가?"를 판단합니다.

사람의 이동·규모·직무 변화
→ 채용·인력운영

사람을 관리하는 규칙·제도·운영방식 변화
→ HR 제도·조직운영


예:

"A사, AI 도입으로 500명 직무전환"
→ 채용·인력운영

"A사, AI 기반 인사평가 시스템 도입"
→ HR 제도·조직운영

"A사, 신규 개발자 300명 채용"
→ 채용·인력운영

"A사, 개발자 채용 평가방식 개편"
→ 채용·인력운영

"A사, 전 직원 성과평가 제도 개편"
→ HR 제도·조직운영

"A사, 조직개편으로 300명 희망퇴직"
→ 채용·인력운영

"A사, 조직개편에 맞춰 평가·승진체계 개편"
→ HR 제도·조직운영


============================================================
STEP 8. 최종 인간 편집자 테스트
============================================================

include=true 직전에 다시 물으세요.

"내가 실제 회사 HR팀 편집자라면
이 기사를 팀에 공유하겠는가?"

다음 반응이 예상되면 제외합니다.

- 그래서 HR이 뭘 해야 하지?
- 그냥 업계기사 아닌가?
- 광고 아닌가?
- 취준생 기사 아닌가?
- 왜 이걸 HR팀에 공유하지?
- 실제 제도가 바뀐 것도 아닌데?

애매하면 false입니다.


============================================================
STEP 9. topic
============================================================

topic은 기사 제목이 아니라
중복·다양성 관리용 사건 유형입니다.

[노동법·정책·판례]

- 육아휴직
- 근로시간
- 통상임금
- 부당해고
- 연차
- 직장내괴롭힘
- 노조법
- 노동정책


[보상·노사관계]

- 성과급
- 임금
- 임단협
- 단체교섭
- 파업
- 노동조합
- 복리후생


[채용·인력운영]

- 신입채용
- 경력채용
- 채용평가
- 채용전형
- 온보딩
- 희망퇴직
- 구조조정
- 인력감축
- 인력재배치
- 직무전환
- 리스킬링


[HR 제도·조직운영]

- 평가제도
- 성과관리
- 승진제도
- 직급제도
- 조직개편
- 조직문화
- 유연근무
- 재택근무
- 근무제도
- 인재육성
- HR AI
- 피플애널리틱스


============================================================
출력
============================================================

반드시 출력:

- id
- include
- category
- topic
- hr_relevance
- practical_value
- rejection_type
- why_read
- reason

include=false이면 category=null

include=true이면 rejection_type=null


rejection_type:

- non_hr
- promotion
- product
- event
- owner_management
- book_content
- industry_news
- jobseeker_content
- security_crime
- public_org
- simple_non_it_recruitment
- low_practical_value
- smilegate_not_central


JSON만 출력하세요.


[기사 목록]

{json.dumps(article_payload, ensure_ascii=False)}


[JSON 형식]

{{
  "articles": [
    {{
      "id": 1,
      "include": true,
      "category": "노동법·정책·판례",
      "topic": "육아휴직",
      "hr_relevance": 96,
      "practical_value": 94,
      "rejection_type": null,
      "why_read": "새 육아휴직 제도를 사내 제도와 신청 프로세스에 반영할 필요가 있다.",
      "reason": "민간기업에 직접 적용되는 육아휴직 제도 변화가 핵심이다."
    }}
  ]
}}
""".strip()

# ============================================================
# Gemini 실패
#
# 실패 시 검색그룹으로 강제 포함하지 않습니다.
# ============================================================

def fallback_classification(
    batch: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    results = []

    for article in batch:
        results.append({
            "id": article["id"],
            "include": False,
            "category": None,
            "topic": "",
            "hr_relevance": 0,
            "practical_value": 0,
            "rejection_type": "classification_failure",
            "why_read": "",
            "reason": (
                "Gemini 분류 실패로 품질 보장을 위해 제외"
            )
        })

    return results


def parse_bool(
    value: Any
) -> bool:

    if isinstance(
        value,
        bool
    ):
        return value

    if isinstance(
        value,
        str
    ):
        return (
            value.strip().lower()
            == "true"
        )

    return bool(
        value
    )


# ============================================================
# 분류
# ============================================================

def classify_candidates_with_gemini(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    classified = []

    for batch_start in range(
        0,
        len(candidates),
        CLASSIFICATION_BATCH_SIZE
    ):
        batch = candidates[
            batch_start:
            batch_start + CLASSIFICATION_BATCH_SIZE
        ]

        print(
            "\n🤖 Gemini 기사 분류 "
            f"{batch_start + 1}~"
            f"{batch_start + len(batch)}"
        )

        prompt = build_classification_prompt(
            batch
        )

        data = call_gemini_json(
            prompt,
            temperature=0.0
        )

        if data is None:
            result_items = fallback_classification(
                batch
            )

        else:
            result_items = data.get(
                "articles",
                []
            )

            if not isinstance(
                result_items,
                list
            ):
                result_items = fallback_classification(
                    batch
                )

        result_by_id = {}

        for result in result_items:

            if not isinstance(
                result,
                dict
            ):
                continue

            try:
                article_id = int(
                    result.get(
                        "id"
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                continue

            result_by_id[
                article_id
            ] = result

        for article in batch:

            result = result_by_id.get(
                article["id"]
            )

            if result is None:
                continue

            include = parse_bool(
                result.get(
                    "include",
                    False
                )
            )

            if not include:
                continue

            category = result.get(
                "category"
            )

            if category not in CATEGORY_ORDER:
                continue

            try:
                hr_relevance = int(
                    result.get(
                        "hr_relevance",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                hr_relevance = 0

            try:
                practical_value = int(
                    result.get(
                        "practical_value",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                practical_value = 0

            # ------------------------------------------------
            # 스마일게이트는 HR 점수 기준 미적용
            # ------------------------------------------------

            if category != CATEGORY_SMILEGATE:

                # Gemini가 include=true를 잘못 줘도
                # 코드에서 최종 하한선을 다시 검사
                if hr_relevance < 80:
                    continue

                if practical_value < 75:
                    continue

            why_read = str(
                result.get(
                    "why_read",
                    ""
                )
            ).strip()

            if not why_read:
                continue

            enriched = dict(
                article
            )

            enriched[
                "category"
            ] = category

            enriched[
                "topic"
            ] = str(
                result.get(
                    "topic",
                    ""
                )
            ).strip()

            enriched[
                "hr_relevance"
            ] = hr_relevance

            enriched[
                "practical_value"
            ] = practical_value

            enriched[
                "why_read"
            ] = why_read

            enriched[
                "classification_reason"
            ] = str(
                result.get(
                    "reason",
                    ""
                )
            ).strip()

            enriched[
                "rejection_type"
            ] = result.get(
                "rejection_type"
            )

            enriched[
                "duplicate_group"
            ] = (
                f"article_{article['id']}"
            )

            classified.append(
                enriched
            )

        time.sleep(
            1
        )

    return classified


# ============================================================
# 중복검사 후보 압축
# ============================================================

def build_dedup_pool(
    articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    pool = []

    for category in CATEGORY_ORDER:

        category_articles = [
            article
            for article in articles
            if article.get(
                "category"
            ) == category
        ]

        if category == CATEGORY_SMILEGATE:

            category_articles.sort(
                key=lambda article: (
                    article["pub_dt"]
                ),
                reverse=True
            )

            base_limit = (
                SMILEGATE_DAILY_LIMIT
            )

        else:

            category_articles.sort(
                key=lambda article: (
                    article.get(
                        "practical_value",
                        0
                    ),
                    article.get(
                        "hr_relevance",
                        0
                    ),
                    article["pub_dt"]
                ),
                reverse=True
            )

            base_limit = (
                NORMAL_CATEGORY_DAILY_LIMIT
            )

        pool_limit = (
            base_limit
            * DEDUP_POOL_MULTIPLIER
        )

        pool.extend(
            category_articles[
                :pool_limit
            ]
        )

    return pool


# ============================================================
# 전 카테고리 횡단 중복검사
# ============================================================
def review_duplicates_with_gemini(
    articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not articles:
        return []

    if len(articles) == 1:
        result = dict(
            articles[0]
        )

        result["duplicate_group"] = (
            f"article_{result['id']}"
        )

        result["keep_id"] = result["id"]

        return [result]

    article_payload = []

    for article in articles:
        article_payload.append({
            "id": article["id"],
            "category": article.get(
                "category",
                ""
            ),
            "topic": article.get(
                "topic",
                ""
            ),
            "title": article["title"],
            "description": article.get(
                "description",
                ""
            ),
            "date": article["pub_dt"].strftime(
                "%Y-%m-%d %H:%M"
            ),
            "practical_value": article.get(
                "practical_value",
                0
            ),
            "hr_relevance": article.get(
                "hr_relevance",
                0
            )
        })

    prompt = f"""
당신은 HR 뉴스 브리핑의
최종 중복 편집자입니다.

기사의 제목이 아니라
'실제로 같은 사건인가'를 판단하세요.

목표:

같은 사건을 여러 언론사가
서로 다른 제목과 관점으로 보도했더라도
한 건만 남기는 것입니다.


============================================================
동일 사건 판단
============================================================

다음 네 가지가 실질적으로 같으면
같은 duplicate_group입니다.

1. 핵심 회사·기관
2. 핵심 사건
3. 발생 시기
4. 핵심 결정·수치·발표


예:

"현대차, 파업 손실 4만2천510대…노조 추가 파업"
"4.2만대 생산차질 현대차…책자 돌리며 파업 중단 요청"

→ 같은 현대차 파업 국면과
같은 생산차질 사실을 다루므로
같은 duplicate_group입니다.

기사 관점이
노조의 추가 파업과
회사의 중단 요청으로 다르더라도
핵심 사건이 같으면 중복입니다.


다음도 중복입니다.

- 동일 정부 발표를 여러 언론사가 보도
- 동일 법 개정을 다른 제목으로 보도
- 동일 판결을 다른 관점에서 보도
- 동일 임단협 결과를 여러 언론사가 보도
- 동일 성과급 갈등을 여러 언론사가 보도
- 동일 희망퇴직 발표를 여러 언론사가 보도
- 동일 파업과 동일 생산차질 수치를 재작성


============================================================
별도 기사
============================================================

다음은 중복이 아닙니다.

- 기존 파업 이후 실제 합의가 새로 체결됨
- 기존 발표 이후 새로운 판결이 발생
- 기존 구조조정 발표 이후 실제 규모가 새롭게 확정
- 같은 회사의 서로 다른 사건
- 같은 법률의 서로 다른 판결
- 같은 주제지만 서로 다른 회사 사건


============================================================
대표기사 keep_id
============================================================

각 duplicate_group에서
한 기사만 대표기사로 선택하세요.

대표기사 선정 순서:

1. 핵심 사건을 가장 직접적으로 설명
2. 새로운 사실과 구체적인 수치가 많음
3. HR 실무자가 사건을 이해하기 쉬움
4. 불필요하게 선정적·정치적 표현이 적음
5. 그래도 같으면 최신 기사

같은 duplicate_group의 모든 기사에는
반드시 동일한 keep_id를 출력하세요.

중복이 없는 기사:

duplicate_group은 고유값
keep_id는 자기 자신의 id


JSON만 출력하세요.

[기사 목록]

{json.dumps(article_payload, ensure_ascii=False)}

[JSON 형식]

{{
  "articles": [
    {{
      "id": 1,
      "duplicate_group": "dup_001",
      "keep_id": 1
    }},
    {{
      "id": 2,
      "duplicate_group": "dup_001",
      "keep_id": 1
    }},
    {{
      "id": 3,
      "duplicate_group": "dup_002",
      "keep_id": 3
    }}
  ]
}}
""".strip()

    data = call_gemini_json(
        prompt,
        temperature=0.0
    )

    # Gemini 실패
    if data is None:

        fallback = []

        for article in articles:
            item = dict(
                article
            )

            item["duplicate_group"] = (
                f"article_{article['id']}"
            )

            item["keep_id"] = article["id"]

            fallback.append(
                item
            )

        return fallback

    result_items = data.get(
        "articles",
        []
    )

    if not isinstance(
        result_items,
        list
    ):
        result_items = []

    review_by_id = {}

    for result in result_items:

        if not isinstance(
            result,
            dict
        ):
            continue

        try:
            article_id = int(
                result.get(
                    "id"
                )
            )

        except (
            TypeError,
            ValueError
        ):
            continue

        duplicate_group = str(
            result.get(
                "duplicate_group",
                f"article_{article_id}"
            )
        ).strip()

        try:
            keep_id = int(
                result.get(
                    "keep_id",
                    article_id
                )
            )

        except (
            TypeError,
            ValueError
        ):
            keep_id = article_id

        review_by_id[
            article_id
        ] = {
            "duplicate_group": (
                duplicate_group
                or f"article_{article_id}"
            ),
            "keep_id": keep_id
        }

    reviewed_articles = []

    for article in articles:

        reviewed = dict(
            article
        )

        review = review_by_id.get(
            article["id"],
            {}
        )

        reviewed[
            "duplicate_group"
        ] = review.get(
            "duplicate_group",
            f"article_{article['id']}"
        )

        reviewed[
            "keep_id"
        ] = review.get(
            "keep_id",
            article["id"]
        )

        reviewed_articles.append(
            reviewed
        )

    return reviewed_articles


# ============================================================
# 기사 정렬 점수
# ============================================================

def article_rank_score(
    article: Dict[str, Any]
) -> Tuple[
    int,
    int,
    datetime.datetime
]:

    if (
        article.get(
            "category"
        )
        == CATEGORY_SMILEGATE
    ):

        # 스마일게이트는 HR 점수가 아니라
        # 최신성을 중심으로 선정
        primary = 100
        secondary = 0

    else:

        primary = article.get(
            "practical_value",
            0
        )

        secondary = article.get(
            "hr_relevance",
            0
        )

    return (
        primary,
        secondary,
        article["pub_dt"]
    )


# ============================================================
# 중복 제거
# ============================================================

def deduplicate_classified_articles(
    articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    groups: Dict[
        str,
        List[Dict[str, Any]]
    ] = defaultdict(
        list
    )

    for article in articles:

        duplicate_group = article.get(
            "duplicate_group",
            f"article_{article['id']}"
        )

        groups[
            duplicate_group
        ].append(
            article
        )

    deduplicated = []

    for group_articles in groups.values():

        # ----------------------------------------------------
        # Gemini가 선택한 대표기사 우선
        # ----------------------------------------------------

        keep_article = None

        for article in group_articles:

            try:
                keep_id = int(
                    article.get(
                        "keep_id",
                        article["id"]
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                keep_id = article["id"]

            if article["id"] == keep_id:
                keep_article = article
                break

        # ----------------------------------------------------
        # Gemini keep_id가 이상하면 기존 점수 방식 fallback
        # ----------------------------------------------------

        if keep_article is None:

            group_articles.sort(
                key=article_rank_score,
                reverse=True
            )

            keep_article = (
                group_articles[0]
            )

        deduplicated.append(
            keep_article
        )

    # --------------------------------------------------------
    # LLM이 놓친 완전 동일 URL / 제목 최종 제거
    # --------------------------------------------------------

    final_articles = []

    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()

    for article in sorted(
        deduplicated,
        key=article_rank_score,
        reverse=True
    ):

        normalized_url = article.get(
            "normalized_url",
            ""
        )

        normalized_title = article.get(
            "normalized_title",
            ""
        )

        if (
            normalized_url
            and normalized_url
            in seen_urls
        ):
            continue

        if (
            normalized_title
            and normalized_title
            in seen_titles
        ):
            continue

        final_articles.append(
            article
        )

        if normalized_url:
            seen_urls.add(
                normalized_url
            )

        if normalized_title:
            seen_titles.add(
                normalized_title
            )

    return final_articles


# ============================================================
# 카테고리별 다양성 선정
# ============================================================

def select_category_candidates(
    articles: List[Dict[str, Any]],
    category: str,
    limit: int,
    existing_topics: Set[str] | None = None
) -> List[Dict[str, Any]]:

    category_articles = [
        article
        for article in articles
        if article.get(
            "category"
        ) == category
    ]

    category_articles.sort(
        key=article_rank_score,
        reverse=True
    )

    selected = []

    used_topics: Set[str] = set(
        existing_topics or set()
    )

    for article in category_articles:

        if len(selected) >= limit:
            break

        topic = str(
            article.get(
                "topic",
                ""
            )
        ).strip().lower()

        if not topic:
            topic = (
                f"article_{article['id']}"
            )

        # 기존 기사 또는 오늘 이미 선택된 기사와
        # 같은 topic이면 제외
        if topic in used_topics:
            continue

        selected.append(
            article
        )

        used_topics.add(
            topic
        )

    selected.sort(
        key=lambda article: (
            article["pub_dt"]
        ),
        reverse=True
    )

    return selected

    category_articles = [
        article
        for article in articles
        if article.get(
            "category"
        ) == category
    ]

    category_articles.sort(
        key=article_rank_score,
        reverse=True
    )

    selected = []
    used_topics: Set[str] = set()

    for article in category_articles:

        if len(selected) >= limit:
            break

        topic = str(
            article.get(
                "topic",
                ""
            )
        ).strip().lower()

        if not topic:
            topic = (
                f"article_{article['id']}"
            )

        # 같은 topic은 하루 한 건만
        if topic in used_topics:
            continue

        selected.append(
            article
        )

        used_topics.add(
            topic
        )

    selected.sort(
        key=lambda article: (
            article["pub_dt"]
        ),
        reverse=True
    )

    return selected



# ============================================================
# 기본 요약
# ============================================================

def make_fallback_summary(
    title: str,
    content: str
) -> Tuple[
    str,
    List[str]
]:

    normalized = re.sub(
        r"\s+",
        " ",
        content
    ).strip()

    if not normalized:
        normalized = title

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?。])\s+",
            normalized
        )
        if sentence.strip()
    ]

    first = (
        sentences[0][:180]
        if sentences
        else title[:180]
    )

    second = (
        sentences[1][:180]
        if len(sentences) >= 2
        else (
            "기사 원문에서 세부 내용과 "
            "업무 영향을 확인해야 합니다."
        )
    )

    return (
        f"• {first}\n• {second}",
        [
            "기사의 핵심 변화 및 사실관계 확인",
            "자사 업무·제도에 미치는 영향 검토"
        ]
    )


# ============================================================
# 최종 요약
# ============================================================

def generate_article_summary(
    category: str,
    title: str,
    full_content: str
) -> Tuple[
    str,
    List[str]
]:

    fallback_summary, fallback_checkpoints = (
        make_fallback_summary(
            title,
            full_content
        )
    )

    if category == CATEGORY_SMILEGATE:

        prompt = f"""
당신은 스마일게이트 사내에서
외부 회사 소식을 공유하는 뉴스 브리핑 작성자입니다.

[기사 제목]
{title}

[기사 내용]
{full_content[:5000]}

[목적]

구성원이 빠르게 읽고

- 스마일게이트에 어떤 소식이 있는지
- 회사 관점에서 왜 알아둘 만한지

이해하도록 작성합니다.

[작성 기준]

1. 기사에 실제로 존재하는 사실만 사용합니다.
2. 스마일게이트 관련 내용을 우선합니다.
3. 업계 일반론보다 스마일게이트 관련 사실을 중심으로 씁니다.
4. 핵심 내용을 두 개의 불릿으로 요약합니다.
5. checkpoints는 사업·게임·제품·시장·조직 관점에서
   추가로 지켜볼 사항 두 가지를 작성합니다.
6. 기사에 없는 전략을 지어내지 않습니다.
7. 지나치게 거창한 컨설팅 표현을 사용하지 않습니다.
8. JSON만 출력합니다.

[JSON 형식]

{{
  "summary": "• 핵심 내용 1\\n• 핵심 내용 2",
  "checkpoints": [
    "확인사항 1",
    "확인사항 2"
  ]
}}
""".strip()

    else:

        prompt = f"""
당신은 대한민국 민간기업의
HR·인사·노무 실무자를 위한 뉴스 브리핑 작성자입니다.

[카테고리]
{category}

[기사 제목]
{title}

[기사 내용]
{full_content[:5000]}

[목적]

HR 실무자가 짧게 읽은 뒤

- 무엇이 바뀌었는지
- 우리 회사에서 무엇을 확인해야 하는지

바로 이해하도록 작성합니다.

[작성 기준]

1. 기사에 실제로 있는 사실만 사용합니다.
2. 핵심 사실을 두 개의 불릿으로 요약합니다.
3. HR 실무에 중요한 사실을 우선합니다.
4. checkpoints는 구체적인 실무 확인사항 두 가지입니다.
5. 추정이나 과장은 하지 않습니다.
6. 기사에 없는 법적 의무를 만들어내지 않습니다.
7. 기사와 무관한 범용 표현만 사용하지 않습니다.

예:

- 취업규칙 개정 필요 여부 확인
- 성과급 산정 기준과 노사합의 내용 점검
- 채용 평가 문항 및 검증 프로세스 점검
- 근로시간 관리기준 변경 필요 여부 확인
- 휴가 신청 시스템 반영 여부 확인

8. JSON만 출력합니다.

[JSON 형식]

{{
  "summary": "• 핵심 내용 1\\n• 핵심 내용 2",
  "checkpoints": [
    "실무 확인사항 1",
    "실무 확인사항 2"
  ]
}}
""".strip()

    data = call_gemini_json(
        prompt,
        temperature=0.15
    )

    if data is None:

        return (
            fallback_summary,
            fallback_checkpoints
        )

    summary = str(
        data.get(
            "summary",
            ""
        )
    ).strip()

    checkpoints = data.get(
        "checkpoints",
        []
    )

    if not isinstance(
        checkpoints,
        list
    ):
        checkpoints = []

    checkpoints = [
        str(item).strip()
        for item in checkpoints
        if str(item).strip()
    ][:2]

    if not summary:
        summary = fallback_summary

    if not checkpoints:
        checkpoints = (
            fallback_checkpoints
        )

    return (
        summary,
        checkpoints
    )


# ============================================================
# CSV
# ============================================================

def load_previous_data() -> pd.DataFrame:

    if not CSV_FILE_PATH.exists():

        return pd.DataFrame(
            columns=CSV_COLUMNS
        )

    try:

        data_frame = pd.read_csv(
            CSV_FILE_PATH,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False
        )

        for column in CSV_COLUMNS:

            if column not in data_frame.columns:
                data_frame[
                    column
                ] = ""

        return data_frame[
            CSV_COLUMNS
        ]

    except Exception:

        return pd.DataFrame(
            columns=CSV_COLUMNS
        )

def load_previous_smilegate_articles() -> List[Dict[str, Any]]:
    """
    기존 CSV에서 오늘의 스마일게이트 기사만 가져옵니다.

    오늘 수집분과 과거 기사 사이의
    동일 사건 중복검사에 사용합니다.
    """

    previous_df = load_previous_data()

    if previous_df.empty:
        return []

    previous_articles = []

    for _, row in previous_df.iterrows():

        if str(
            row.get("category", "")
        ).strip() != CATEGORY_SMILEGATE:
            continue

        title = clean_text(
            row.get("title", "")
        )

        if not title:
            continue

        pub_date = parse_pub_date(
            str(row.get("pubDate", ""))
        )

        if pub_date is None:
            continue

        previous_articles.append({
            "title": title,
            "description": clean_text(
                row.get("summary", "")
            ),
            "pubDate": str(
                row.get("pubDate", "")
            ),
            "pub_dt": pub_date,
            "link": str(
                row.get("link", "")
            ).strip(),
        })

    return previous_articles

def save_dataframe(
    data_frame: pd.DataFrame
) -> None:

    data_frame = data_frame.copy()

    for column in CSV_COLUMNS:

        if column not in data_frame.columns:
            data_frame[
                column
            ] = ""

    data_frame = data_frame[
        CSV_COLUMNS
    ]

    temp_path = (
        CSV_FILE_PATH
        .with_suffix(
            ".tmp.csv"
        )
    )

    data_frame.to_csv(
        temp_path,
        index=False,
        encoding="utf-8-sig"
    )

    temp_path.replace(
        CSV_FILE_PATH
    )


def merge_and_save_articles(
    new_articles: List[Dict[str, Any]]
) -> int:
    """
    신규 기사 + 기존 CSV 누적.

    - 기존 데이터 보존
    - URL 중복 제거
    - 제목 완전중복 제거
    - 최신순 정렬
    - 전체 최대 200건
    """

    previous_df = (
        load_previous_data()
    )

    new_df = pd.DataFrame(
        new_articles
    )

    if new_df.empty:

        return len(
            previous_df
        )

    for column in CSV_COLUMNS:

        if column not in new_df.columns:
            new_df[
                column
            ] = ""

    new_df = new_df[
        CSV_COLUMNS
    ]

    combined = pd.concat(
        [
            new_df,
            previous_df
        ],
        ignore_index=True
    )

    combined = combined.fillna(
        ""
    )

    # --------------------------------------------------------
    # URL 정규화 / 중복 제거
    # --------------------------------------------------------

    combined[
        "_normalized_url"
    ] = (
        combined["link"]
        .astype(str)
        .apply(
            normalize_url
        )
    )

    has_url = (
        combined[
            "_normalized_url"
        ]
        .astype(str)
        .str.len()
        > 0
    )

    with_url = (
        combined[
            has_url
        ]
        .drop_duplicates(
            subset=[
                "_normalized_url"
            ],
            keep="first"
        )
    )

    without_url = combined[
        ~has_url
    ]

    combined = pd.concat(
        [
            with_url,
            without_url
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # 제목 완전중복 제거
    # --------------------------------------------------------

    combined[
        "_normalized_title"
    ] = (
        combined["title"]
        .astype(str)
        .apply(
            normalize_title
        )
    )

    has_title = (
        combined[
            "_normalized_title"
        ]
        .astype(str)
        .str.len()
        > 0
    )

    with_title = (
        combined[
            has_title
        ]
        .drop_duplicates(
            subset=[
                "_normalized_title"
            ],
            keep="first"
        )
    )

    without_title = combined[
        ~has_title
    ]

    combined = pd.concat(
        [
            with_title,
            without_title
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # 최신순
    # --------------------------------------------------------

    combined[
        "_sort_date"
    ] = pd.to_datetime(
        combined[
            "pubDate"
        ],
        errors="coerce",
        utc=True
    )

    combined = (
        combined
        .sort_values(
            by="_sort_date",
            ascending=False,
            na_position="last"
        )
        .head(
            MAX_STORED_ARTICLES
        )
    )

    combined = combined.drop(
        columns=[
            "_normalized_url",
            "_normalized_title",
            "_sort_date"
        ],
        errors="ignore"
    )

    save_dataframe(
        combined
    )

    return len(
        combined
    )


# ============================================================
# 전체 실행
# ============================================================

def run_collection() -> bool:

    if (
        not NAVER_CLIENT_ID
        or not NAVER_CLIENT_SECRET
    ):

        message = (
            "네이버 API 인증정보가 없습니다. "
            ".env 파일의 NAVER_CLIENT_ID와 "
            "NAVER_CLIENT_SECRET을 확인하세요."
        )

        print(
            f"❌ {message}"
        )

        write_status(
            False,
            message
        )

        return False

    if (
        not GEMINI_API_KEY
        or genai is None
        or types is None
    ):

        message = (
            "Gemini를 사용할 수 없습니다. "
            "품질 보장을 위해 수집을 중단합니다."
        )

        print(
            f"❌ {message}"
        )

        write_status(
            False,
            message
        )

        return False

    now = datetime.datetime.now(
        KST
    )

    window_start, window_end = (
        get_collection_window(
            now
        )
    )

    headers = {
        "X-Naver-Client-Id": (
            NAVER_CLIENT_ID
        ),
        "X-Naver-Client-Secret": (
            NAVER_CLIENT_SECRET
        )
    }

    print(
        "=" * 72
    )

    print(
        "🌐 HR 뉴스 수집 시작"
    )

    print(
        f"📁 저장 위치: "
        f"{CSV_FILE_PATH}"
    )

    print(
        f"🤖 Gemini 모델: "
        f"{GEMINI_MODEL_NAME}"
    )

    print(
        f"🕒 실행 시각: "
        f"{now:%Y-%m-%d %H:%M:%S} KST"
    )

    print(
        "📅 신규 수집 구간: "
        f"{window_start:%Y-%m-%d %H:%M} "
        "~ "
        f"{window_end:%Y-%m-%d %H:%M} KST"
    )

    print(
        "=" * 72
    )

    # --------------------------------------------------------
    # 1. 후보 수집
    # --------------------------------------------------------

    raw_candidates, api_success_count = (
        collect_raw_candidates(
            headers,
            window_start,
            window_end
        )
    )

    print(
        f"\n📋 전체 원시 후보: "
        f"{len(raw_candidates)}건"
    )

    # --------------------------------------------------------
    # 2. Gemini 1차 분류
    # --------------------------------------------------------

    classified = (
        classify_candidates_with_gemini(
            raw_candidates
        )
    )

    print(
        f"🤖 1차 포함 판정: "
        f"{len(classified)}건"
    )

    # --------------------------------------------------------
    # 3. 중복검사 후보 압축
    # --------------------------------------------------------

    dedup_pool = (
        build_dedup_pool(
            classified
        )
    )

    print(
        f"🔎 중복 검토 후보: "
        f"{len(dedup_pool)}건"
    )

    # --------------------------------------------------------
    # 4. 전 카테고리 횡단 중복검사
    # --------------------------------------------------------

    duplicate_reviewed = (
        review_duplicates_with_gemini(
            dedup_pool
        )
    )

    # --------------------------------------------------------
    # 4-1. 과거 CSV의 스마일게이트 기사와 중복검사
    #
    # 오늘 기사와 날짜가 달라도
    # 동일 사건이면 오늘 기사를 제외합니다.
    # --------------------------------------------------------

def exclude_smilegate_duplicates_with_history(
    articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    smilegate_articles = [
        article
        for article in articles
        if article.get("category")
        == CATEGORY_SMILEGATE
    ]

    other_articles = [
        article
        for article in articles
        if article.get("category")
        != CATEGORY_SMILEGATE
    ]

    if not smilegate_articles:
        return articles

    previous_smilegate = (
        load_previous_smilegate_articles()
    )

    if not previous_smilegate:
        return articles

    # --------------------------------------------------------
    # 너무 오래된 기사는 비교하지 않도록 제한
    # --------------------------------------------------------

    latest_date = max(
        article["pub_dt"]
        for article in smilegate_articles
    )

    history_limit = (
        latest_date
        - datetime.timedelta(days=14)
    )

    previous_smilegate = [
        article
        for article in previous_smilegate
        if article["pub_dt"] >= history_limit
    ]

    if not previous_smilegate:
        return articles

    article_payload = []

    for article in smilegate_articles:
        article_payload.append({
            "id": article["id"],
            "title": article["title"],
            "description": article.get(
                "description",
                ""
            ),
            "date": article["pub_dt"].strftime(
                "%Y-%m-%d %H:%M"
            )
        })

    history_payload = []

    for article in previous_smilegate:
        history_payload.append({
            "title": article["title"],
            "description": article.get(
                "description",
                ""
            ),
            "date": article["pub_dt"].strftime(
                "%Y-%m-%d %H:%M"
            )
        })

    prompt = f"""
당신은 스마일게이트 뉴스 브리핑의
'과거 기사 중복 검사' 편집자입니다.

오늘 새로 수집된 스마일게이트 기사와
과거에 이미 저장된 스마일게이트 기사를 비교합니다.

목표는

"이미 이전 날짜에 다룬 동일 사건을
오늘 다시 보도한 기사라면 제외"

하는 것입니다.


============================================================
중요한 원칙
============================================================

날짜가 다르다는 이유만으로 중복으로 판단하지 마세요.

핵심은
'같은 사건을 다시 보도한 것인지'
입니다.


[중복으로 판단]

다음 요소가 실질적으로 같으면 중복입니다.

1. 같은 스마일게이트 게임·서비스·사업·조직
2. 같은 핵심 사건
3. 같은 발표·결정·성과
4. 새로운 핵심 사실이 거의 없음

예:

과거:
"스마일게이트, 신작 A 글로벌 출시"

오늘:
"스마일게이트 신작 A 글로벌 시장 공략"

→ 같은 글로벌 출시 사건이면 중복


과거:
"스마일게이트, 신작 A 출시"

오늘:
"스마일게이트 신작 A 첫 대규모 업데이트"

→ 새로운 업데이트 사건이므로 중복 아님


과거:
"스마일게이트, 직원 300명 채용"

오늘:
"스마일게이트, AI 조직 신설"

→ 서로 다른 사건이므로 중복 아님


============================================================
특히 주의
============================================================

단순히 같은 게임이나 같은 사업을 다룬다고
중복 처리하지 마세요.

다음은 별도 사건입니다.

- 신작 발표 → 출시
- 출시 → 업데이트
- 업데이트 → 흥행 성과
- 투자 발표 → 투자 집행
- 채용 발표 → 실제 채용 결과
- 행사 참가 → 행사 성과
- 사업 발표 → 실제 사업 확장
- 계약 체결 → 계약 이후 새로운 성과


============================================================
판단 기준
============================================================

오늘 기사에

'새로운 발표'
'새로운 결정'
'새로운 수치'
'새로운 성과'
'새로운 제품/서비스 변화'
'새로운 사업 진행 상황'

등이 명확하게 존재하면
기존 사건과 관련되어 있어도 살립니다.


반대로

제목만 바꾸었거나
표현만 바꾸었거나
기존 발표 내용을 다른 언론사가
다시 작성한 수준이면

중복으로 판단합니다.


============================================================
출력
============================================================

오늘 기사마다 다음을 출력하세요.

- id
- duplicate
- matched_date
- reason

duplicate=true
→ 기존 기사와 같은 사건이므로 제외

duplicate=false
→ 새로운 사건이므로 유지

JSON만 출력하세요.


[오늘 신규 스마일게이트 기사]

{json.dumps(article_payload, ensure_ascii=False)}


[과거 저장된 스마일게이트 기사]

{json.dumps(history_payload, ensure_ascii=False)}


[JSON 형식]

{{
  "articles": [
    {{
      "id": 1,
      "duplicate": true,
      "matched_date": "2026-08-18 14:30",
      "reason": "전날 보도된 동일한 글로벌 출시 발표를 다시 다룬 기사"
    }},
    {{
      "id": 2,
      "duplicate": false,
      "matched_date": null,
      "reason": "기존 출시 기사와 달리 새로운 업데이트 내용을 다룸"
    }}
  ]
}}
""".strip()

    data = call_gemini_json(
        prompt,
        temperature=0.0
    )

    # Gemini 실패 시 기존 기사를 함부로 제외하지 않음
    if data is None:
        return articles

    result_items = data.get(
        "articles",
        []
    )

    if not isinstance(
        result_items,
        list
    ):
        return articles

    result_by_id = {}

    for result in result_items:

        if not isinstance(
            result,
            dict
        ):
            continue

        try:
            article_id = int(
                result.get("id")
            )
        except (
            TypeError,
            ValueError
        ):
            continue

        result_by_id[
            article_id
        ] = result

    filtered_smilegate = []

    for article in smilegate_articles:

        result = result_by_id.get(
            article["id"]
        )

        if result is None:
            # 판단 결과가 없으면 안전하게 유지
            filtered_smilegate.append(
                article
            )
            continue

        duplicate = parse_bool(
            result.get(
                "duplicate",
                False
            )
        )

        if duplicate:

            matched_date = result.get(
                "matched_date"
            )

            reason = str(
                result.get(
                    "reason",
                    ""
                )
            ).strip()

            print(
                "   🚫 스마일게이트 과거기사 중복 제외: "
                f"{article['title'][:60]}"
            )

            print(
                f"      └ 기존 기사: "
                f"{matched_date}"
            )

            print(
                f"      └ 사유: {reason}"
            )

            continue

        filtered_smilegate.append(
            article
        )

    return (
        other_articles
        + filtered_smilegate
    )

    # --------------------------------------------------------
    # 5. 동일 사건 제거
    # --------------------------------------------------------

    deduplicated = (
        deduplicate_classified_articles(
            duplicate_reviewed
        )
    )

    print(
        f"🔄 동일 사건 제거 후: "
        f"{len(deduplicated)}건"
    )

    # --------------------------------------------------------
    # 6. 오늘 신규 기사 선정
    # --------------------------------------------------------

    selected_by_category: Dict[
        str,
        List[Dict[str, Any]]
    ] = {}

    for category in CATEGORY_ORDER:

        limit = (
            SMILEGATE_DAILY_LIMIT
            if category
            == CATEGORY_SMILEGATE
            else NORMAL_CATEGORY_DAILY_LIMIT
        )

        selected = select_category_candidates(
            articles,
            category,
            limit,
            existing_topics
        )

        selected_by_category[
            category
        ] = selected

        for article in selected:

            topic = str(
                article.get(
                    "topic",
                    ""
                )
            ).strip().lower()

            if topic:
                existing_topics.add(
                    topic
                )

        print(
            f"🎯 [{category}] "
            f"{len(selected)}건 선정"
        )

    # --------------------------------------------------------
    # 7. 원문 / 최종 요약
    # --------------------------------------------------------

    final_articles = []

    for category in CATEGORY_ORDER:

        selected = (
            selected_by_category
            .get(
                category,
                []
            )
        )

        print(
            f"\n🧾 [{category}] 최종 처리"
        )

        for index, candidate in enumerate(
            selected,
            start=1
        ):

            title = candidate[
                "title"
            ]

            link = candidate[
                "link"
            ]

            description = candidate[
                "description"
            ]

            print(
                f"  📖 "
                f"[{index}/{len(selected)}] "
                f"{title[:70]}"
            )

            original_title, full_content = (
                fetch_article_page(
                    link
                )
            )

            if (
                original_title
                and (
                    title.endswith(
                        "..."
                    )
                    or title.endswith(
                        "…"
                    )
                    or "..."
                    in title[-8:]
                    or "…"
                    in title[-8:]
                )
            ):

                title = original_title

            if len(
                full_content.strip()
            ) < 80:

                full_content = (
                    description
                    or title
                )

            summary, checkpoints = (
                generate_article_summary(
                    category,
                    title,
                    full_content
                )
            )

            pub_dt = candidate[
                "pub_dt"
            ]

            final_articles.append({
                "category": category,
                "date_str": (
                    pub_dt.strftime(
                        "[%m/%d]"
                    )
                ),
                "title": title,
                "summary": summary,
                "checkpoints": (
                    json.dumps(
                        checkpoints,
                        ensure_ascii=False
                    )
                ),
                "link": link,
                "pubDate": candidate[
                    "pubDate"
                ],
                "collected_at": (
                    now.isoformat()
                )
            })

            print(
                "     ✅ 요약 완료"
            )

            time.sleep(
                1
            )

    # --------------------------------------------------------
    # 8. 누적 저장
    # --------------------------------------------------------

    if final_articles:

        total_saved_count = (
            merge_and_save_articles(
                final_articles
            )
        )

        message = (
            "뉴스 수집 완료: "
            f"신규 {len(final_articles)}건 / "
            f"누적 {total_saved_count}건 저장"
        )

        write_status(
            True,
            message,
            total_saved_count
        )

        print(
            f"\n🎉 {message}"
        )

        return True

    # --------------------------------------------------------
    # API 자체가 전부 실패
    # --------------------------------------------------------

    if api_success_count == 0:

        previous_data = (
            load_previous_data()
        )

        message = (
            "네이버 API 호출이 모두 실패했습니다. "
            "기존 CSV는 보존했습니다."
        )

        write_status(
            False,
            message,
            len(
                previous_data
            )
        )

        print(
            f"\n❌ {message}"
        )

        return False

    # --------------------------------------------------------
    # 정상 실행됐지만 신규기사 없음
    #
    # 중요:
    # 기존 CSV를 절대 비우지 않습니다.
    # --------------------------------------------------------

    previous_data = (
        load_previous_data()
    )

    message = (
        "API 호출은 성공했지만 "
        "이번 수집 구간에는 "
        "최종 기준을 충족하는 신규 기사가 없습니다. "
        "기존 데이터는 보존합니다."
    )

    write_status(
        True,
        message,
        len(
            previous_data
        )
    )

    print(
        f"\nℹ️ {message}"
    )

    return True


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    try:

        success = (
            run_collection()
        )

        raise SystemExit(
            0
            if success
            else 1
        )

    except KeyboardInterrupt:

        message = (
            "사용자가 뉴스 수집을 중단했습니다."
        )

        write_status(
            False,
            message
        )

        print(
            f"\n⚠️ {message}"
        )

        raise SystemExit(
            130
        )

    except Exception as error:

        message = (
            "예상하지 못한 오류: "
            f"{error}"
        )

        write_status(
            False,
            message
        )

        print(
            f"\n❌ {message}"
        )

        raise
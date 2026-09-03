# -*- coding: utf-8 -*-
"""Cấu hình chung cho dự án Knowledge Graph kg_diabet."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Neo4j -------------------------------------------------------------
NEO4J_URI      = os.getenv("NEO4J_URI",      "neo4j://127.0.0.1:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "kg-diabet")

# --- Scraping ----------------------------------------------------------
SCRAPING_DELAY_MIN = 1.0
SCRAPING_DELAY_MAX = 3.0
MAX_RETRIES        = 3
REQUEST_TIMEOUT    = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ARTICLE_BASE_URLS = [
    "https://nhathuoclongchau.com.vn/benh/tieu-duong",
    "https://nhathuoclongchau.com.vn/bai-viet/tieu-duong",
]

DRUG_SEARCH_URLS = [
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=tieu+duong",
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=metformin",
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=insulin",
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=gliclazide",
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=glibenclamide",
    "https://nhathuoclongchau.com.vn/tim-kiem?keyword=glucagon",
]

# --- Đường dẫn dữ liệu -------------------------------------------------
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
RAW_DIR       = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

ARTICLES_JSON = os.path.join(RAW_DIR, "articles.json")
DRUGS_JSON    = os.path.join(RAW_DIR, "drugs.json")
ENTITIES_JSON = os.path.join(PROCESSED_DIR, "entities.json")
RELATIONS_JSON = os.path.join(PROCESSED_DIR, "relations.json")


def ensure_dirs():
    """Tạo các thư mục dữ liệu nếu chưa tồn tại."""
    for d in (RAW_DIR, PROCESSED_DIR):
        os.makedirs(d, exist_ok=True)


# --- Nguồn dữ liệu thực tế (robots.txt-friendly) -----------------------
# Long Châu chặn /tim-kiem và *?keyword= trong robots.txt, đồng thời trang
# tìm kiếm render sản phẩm bằng JavaScript. Vì vậy pipeline lấy dữ liệu qua
# sitemap + trang danh mục (đều được phép crawl và render sẵn server-side).
SITEMAP_INDEX   = "https://nhathuoclongchau.com.vn/sitemap.xml"
SITEMAP_DISEASE = "https://nhathuoclongchau.com.vn/sitemap_benh.xml"
SITEMAP_DRUG    = "https://nhathuoclongchau.com.vn/sitemap_thuoc.xml"
SITEMAP_ARTICLE_TEMPLATE = "https://nhathuoclongchau.com.vn/sitemap_baiviet{i}.xml"
N_ARTICLE_SITEMAPS = 4          # số file sitemap bài viết sẽ quét

# Chỉ dùng danh mục đặc hiệu cho tiểu đường. (Danh mục rộng như
# "hormon-noi-tiet-to" kéo theo thuốc tránh thai, nội tiết tố khác... -> nhiễu.)
DRUG_CATEGORY_URLS = [
    "https://nhathuoclongchau.com.vn/thuoc/thuoc-tri-tieu-duong",
]

# Từ khoá lọc URL bệnh / bài viết liên quan tiểu đường
DIABETES_URL_KEYWORDS = ["tieu-duong", "dai-thao-duong", "duong-huyet", "insulin"]

# Từ khoá lọc URL thuốc điều trị tiểu đường
DRUG_URL_KEYWORDS = [
    "metformin", "insulin", "gliclazide", "glibenclamide", "glucagon",
    "glimepirid", "sitagliptin", "dapagliflozin", "empagliflozin", "acarbose",
    "linagliptin", "pioglitazon", "vildagliptin", "repaglinid", "saxagliptin",
    "canagliflozin", "glipizid", "tolbutamid", "liraglutid", "glucophage",
    "diamicron", "januvia", "forxiga", "jardiance", "galvus", "tresiba",
    "lantus", "mixtard", "novomix", "humalog", "actrapid", "insulatard",
    "tieu-duong", "dai-thao-duong",
]

MAX_ARTICLES = 80    # giới hạn số bài viết scrape (đặt None để lấy tất cả)
MAX_DRUGS    = 100   # giới hạn số thuốc scrape

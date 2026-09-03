# -*- coding: utf-8 -*-
"""
BƯỚC 1 — Scraping dữ liệu tiểu đường từ Nhà thuốc Long Châu.

Chiến lược:
  * Long Châu là ứng dụng Next.js: toàn bộ dữ liệu của trang nằm trong thẻ
    <script id="__NEXT_DATA__"> dưới dạng JSON => parse JSON thay vì bóc CSS
    selector (bền hơn nhiều khi site đổi giao diện).
  * Trang /tim-kiem bị chặn trong robots.txt và render sản phẩm bằng JS, nên
    danh sách URL được lấy từ sitemap (được phép crawl) + trang danh mục thuốc.

Đầu ra:
  data/raw/articles.json   — bài viết & trang bệnh
  data/raw/drugs.json      — thuốc điều trị tiểu đường
"""

import json
import random
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

import config

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
SITE = "https://nhathuoclongchau.com.vn"

SESSION = requests.Session()
SESSION.headers.update(config.HEADERS)


# ----------------------------------------------------------------------
# Tiện ích HTTP
# ----------------------------------------------------------------------
def polite_sleep():
    time.sleep(random.uniform(config.SCRAPING_DELAY_MIN, config.SCRAPING_DELAY_MAX))


def fetch(url, retries=None, sleep=True):
    """GET một URL với retry + delay ngẫu nhiên. Trả về text hoặc None."""
    retries = retries if retries is not None else config.MAX_RETRIES
    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                if sleep:
                    polite_sleep()
                return resp.text
            print("    [%s] %s" % (resp.status_code, url))
            if resp.status_code == 404:
                return None
        except requests.RequestException as exc:
            print("    [loi %d/%d] %s: %s" % (attempt, retries, type(exc).__name__, exc))
        time.sleep(2 * attempt)          # backoff tăng dần
    return None


def get_next_data(html):
    """Bóc JSON trong thẻ __NEXT_DATA__ của trang Next.js."""
    if not html:
        return None
    match = NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def html_to_text(raw_html):
    """Chuyển đoạn HTML (rich text từ CMS) sang plain text sạch."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(str(raw_html), "lxml")
    text = soup.get_text(separator=" ")
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def get_sitemap_urls(sitemap_url):
    """Lấy toàn bộ <loc> trong một file sitemap."""
    xml = fetch(sitemap_url, sleep=False)
    if not xml:
        return []
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)


def matches(url, keywords):
    low = url.lower()
    return any(k in low for k in keywords)


# ----------------------------------------------------------------------
# 1A — Thu thập URL
# ----------------------------------------------------------------------
def collect_disease_urls():
    urls = get_sitemap_urls(config.SITEMAP_DISEASE)
    hits = [u for u in urls if matches(u, config.DIABETES_URL_KEYWORDS)]
    print("  sitemap_benh: %d URL -> %d trang benh lien quan" % (len(urls), len(hits)))
    return hits


def collect_article_urls(limit):
    hits = []
    for i in range(1, config.N_ARTICLE_SITEMAPS + 1):
        urls = get_sitemap_urls(config.SITEMAP_ARTICLE_TEMPLATE.format(i=i))
        found = [u for u in urls if matches(u, config.DIABETES_URL_KEYWORDS)]
        print("  sitemap_baiviet%d: %d URL -> %d bai lien quan" % (i, len(urls), len(found)))
        hits.extend(found)
        if limit and len(hits) >= limit:
            break
    return hits[:limit] if limit else hits


def collect_drug_urls(limit):
    """URL thuốc = sitemap thuốc (lọc theo hoạt chất) + trang danh mục."""
    urls = get_sitemap_urls(config.SITEMAP_DRUG)
    hits = [u for u in urls if matches(u, config.DRUG_URL_KEYWORDS)]
    print("  sitemap_thuoc: %d URL -> %d thuoc lien quan" % (len(urls), len(hits)))

    for cat_url in config.DRUG_CATEGORY_URLS:
        data = get_next_data(fetch(cat_url))
        if not data:
            continue
        view = data.get("props", {}).get("pageProps", {}).get("viewData") or {}
        products = view.get("products") or []
        print("  danh muc %s: %d san pham" % (cat_url.rsplit("/", 1)[-1], len(products)))
        for prod in products:
            slug = prod.get("slug")
            if slug:
                hits.append(SITE + "/" + slug.lstrip("/"))

    unique = list(dict.fromkeys(hits))       # giữ thứ tự, bỏ trùng
    return unique[:limit] if limit else unique


# ----------------------------------------------------------------------
# 1B — Parse từng loại trang
# ----------------------------------------------------------------------
DISEASE_SECTIONS = {
    "description":         "Tổng quan",
    "aetiologies":         "Nguyên nhân",
    "symptom":             "Triệu chứng",
    "risk":                "Yếu tố nguy cơ",
    "diagnoseAndTreaty":   "Chẩn đoán và điều trị",
    "livingAndPreventive": "Sinh hoạt và phòng ngừa",
}


def _sections_of(page):
    """Gom các section rich-text của trang bệnh / bài viết thành text sạch."""
    sections, parts = {}, []
    for key, label in DISEASE_SECTIONS.items():
        text = html_to_text(page.get(key))
        if text:
            sections[key] = text
            parts.append(label + ". " + text)
    return sections, "\n".join(parts)


def parse_disease_page(url):
    data = get_next_data(fetch(url))
    if not data:
        return None
    page = data.get("props", {}).get("pageProps", {}).get("data")
    if not isinstance(page, dict):
        return None

    sections, content = _sections_of(page)
    if not content:
        return None

    return {
        "title": page.get("headline") or page.get("name") or "",
        "name": page.get("name") or "",
        "url": url,
        "type": "disease",
        "short_description": page.get("shortDescription") or "",
        "content": content,
        "sections": sections,
        "tags": [t.get("title") for t in (page.get("tags") or []) if t.get("title")],
        "categories": [c.get("name") for c in (page.get("categories") or []) if c.get("name")],
    }


def parse_article_page(url):
    data = get_next_data(fetch(url))
    if not data:
        return None
    detail = data.get("props", {}).get("pageProps", {}).get("detail") or {}
    page = detail.get("data")
    if not isinstance(page, dict):
        return None

    sections, content = _sections_of(page)
    if not content:
        return None

    return {
        "title": page.get("name") or page.get("headline") or "",
        "name": page.get("name") or "",
        "url": url,
        "type": "article",
        "short_description": page.get("shortDescription") or "",
        "content": content,
        "sections": sections,
        "tags": [t.get("title") for t in (page.get("tags") or []) if t.get("title")],
        "categories": [c.get("name") for c in (page.get("categories") or []) if c.get("name")],
    }


def _first_price(product):
    """Lấy giá bán mặc định (đơn vị nhỏ nhất) từ mảng prices."""
    for price in product.get("prices") or []:
        value = price.get("price")
        if value:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def parse_drug_page(url):
    data = get_next_data(fetch(url))
    if not data:
        return None
    props = data.get("props", {}).get("pageProps", {}) or {}
    product = props.get("product")
    if not isinstance(product, dict):
        return None
    content = props.get("content") or {}

    categories = [c.get("name") for c in (product.get("categories") or []) if c.get("name")]

    return {
        "name": product.get("webName") or product.get("name") or "",
        "short_name": product.get("shortName") or product.get("name") or "",
        "generic_name": html_to_text(product.get("ingredient")) or html_to_text(product.get("webIngredient")),
        "category": categories[-1] if categories else "",
        "categories": categories,
        "description": html_to_text(product.get("shortDescription")) or html_to_text(content.get("description")),
        "indications": html_to_text(product.get("indications")) or html_to_text(content.get("usage")),
        "contraindications": html_to_text(product.get("contraindication")) or html_to_text(content.get("careful")),
        "side_effects": html_to_text(product.get("adverseEffect")) or html_to_text(content.get("adverseEffect")),
        "dosage": html_to_text(content.get("dosage")) or html_to_text(product.get("dosage")),
        "dosage_form": product.get("dosageForm") or "",
        "concentration": html_to_text(product.get("ingredient")),
        "specification": product.get("specification") or "",
        "manufacturer": product.get("manufactor") or product.get("producer") or product.get("brand") or "",
        "brand": product.get("brand") or "",
        "prescription": bool(product.get("prescription")),
        "price": _first_price(product),
        "sku": product.get("sku") or "",
        "url": url,
    }


# ----------------------------------------------------------------------
# 1C — Điều phối
# ----------------------------------------------------------------------
def scrape_articles():
    print("\n[1/2] Thu thap bai viet & trang benh...")
    disease_urls = collect_disease_urls()
    article_urls = collect_article_urls(config.MAX_ARTICLES)

    jobs = [(u, parse_disease_page, "benh") for u in disease_urls]
    jobs += [(u, parse_article_page, "bai viet") for u in article_urls
             if u not in set(disease_urls)]

    articles = []
    for i, (url, parser, kind) in enumerate(jobs, 1):
        item = parser(url)
        if item:
            articles.append(item)
            print("  [%d/%d] OK (%s) %s" % (i, len(jobs), kind, item["title"][:65]))
        else:
            print("  [%d/%d] -- bo qua %s" % (i, len(jobs), url))
    return articles


def scrape_drugs():
    print("\n[2/2] Thu thap thuoc...")
    urls = collect_drug_urls(config.MAX_DRUGS)

    drugs = []
    for i, url in enumerate(urls, 1):
        item = parse_drug_page(url)
        if item and item["name"]:
            drugs.append(item)
            print("  [%d/%d] OK %s" % (i, len(urls), item["name"][:65]))
        else:
            print("  [%d/%d] -- bo qua %s" % (i, len(urls), url))
    return drugs


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    print("  -> da luu %d ban ghi vao %s" % (len(obj), path))


def main():
    config.ensure_dirs()
    print("=" * 70)
    print("BUOC 1 - SCRAPING LONG CHAU")
    print("=" * 70)

    articles = scrape_articles()
    save_json(articles, config.ARTICLES_JSON)

    drugs = scrape_drugs()
    save_json(drugs, config.DRUGS_JSON)

    print("\nHoan tat Buoc 1:")
    print("  articles.json : %d bai" % len(articles))
    print("  drugs.json    : %d thuoc" % len(drugs))
    if not articles or not drugs:
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
BƯỚC 2 — NLP / NER: raw text  ->  entities + relations.

Kết hợp 3 kỹ thuật:
  1. Dictionary-based NER với canonical hoá (lexicon.py) — chính xác cao cho
     thuật ngữ y khoa tiếng Việt, vốn là cụm từ đa âm tiết cố định.
  2. underthesea (sent_tokenize / word_tokenize) để tách câu & tách từ tiếng
     Việt, làm đơn vị cho việc suy luận quan hệ ở mức câu.
  3. Luật (section-aware + regex + trigger word) để sinh quan hệ.

Đầu vào : data/raw/articles.json, data/raw/drugs.json
Đầu ra  : data/processed/entities.json, data/processed/relations.json
"""

import json
import re
import sys
from collections import OrderedDict, defaultdict

import config
import lexicon

try:
    from underthesea import sent_tokenize, word_tokenize
    HAS_UTS = True
except ImportError:                                    # pragma: no cover
    HAS_UTS = False
    print("[cảnh báo] Không import được underthesea -> dùng bộ tách câu regex.")


# ----------------------------------------------------------------------
# Tiện ích văn bản
# ----------------------------------------------------------------------
VN_WORD = r"0-9A-Za-zÀ-ỹ"          # ký tự "trong từ" của tiếng Việt


def normalize(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def split_sentences(text):
    text = normalize(text)
    if not text:
        return []
    if HAS_UTS:
        try:
            return sent_tokenize(text)
        except Exception:
            pass
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]


def build_alias_index(lexicons):
    """
    lexicons: dict {entity_type: {canonical: [aliases]}}
    Trả về list (compiled_regex, entity_type, canonical, alias_len) sắp xếp
    theo alias dài trước để cụm dài ("đái tháo đường type 2") thắng cụm ngắn
    ("đái tháo đường").
    """
    index = []
    for etype, table in lexicons.items():
        for canonical, aliases in table.items():
            for alias in aliases:
                pattern = re.compile(
                    r"(?<![%s])%s(?![%s])" % (VN_WORD, re.escape(alias), VN_WORD)
                )
                index.append((pattern, etype, canonical, len(alias)))
    index.sort(key=lambda item: item[3], reverse=True)
    return index


LEXICONS = {
    "Disease": lexicon.DISEASES,
    "Symptom": lexicon.SYMPTOMS,
    "LabTest": lexicon.LAB_TESTS,
    "RiskFactor": lexicon.RISK_FACTORS,
    "Complication": lexicon.COMPLICATIONS,
    "SideEffect": lexicon.SIDE_EFFECTS,
}
ALIAS_INDEX = build_alias_index(LEXICONS)


def find_entities(text, types=None):
    """
    Nhận diện thực thể trong text. Trả về OrderedDict {(type, canonical): count}.
    Vùng ký tự đã khớp bởi alias dài hơn sẽ bị "che" để tránh khớp chồng lấn.
    """
    low = normalize(text).lower()
    if not low:
        return OrderedDict()

    taken = [False] * len(low)
    found = OrderedDict()
    for pattern, etype, canonical, _ in ALIAS_INDEX:
        if types and etype not in types:
            continue
        for match in pattern.finditer(low):
            start, end = match.span()
            if any(taken[start:end]):
                continue
            for i in range(start, end):
                taken[i] = True
            key = (etype, canonical)
            found[key] = found.get(key, 0) + 1
    return found


def resolve_disease(names):
    """Nếu đã có thể bệnh cụ thể thì bỏ node 'Đái tháo đường' chung chung."""
    specific = [n for n in names if n != lexicon.GENERIC_DISEASE]
    return specific if specific else list(names)


FREQ_WORDS = [
    ("rất thường gặp", "rất thường gặp"),
    ("thường gặp", "thường gặp"),
    ("phổ biến", "thường gặp"),
    ("điển hình", "thường gặp"),
    ("ít gặp", "ít gặp"),
    ("hiếm gặp", "hiếm gặp"),
    ("rất hiếm", "hiếm gặp"),
]


def detect_frequency(text, default="không rõ"):
    low = normalize(text).lower()
    for needle, label in FREQ_WORDS:
        if needle in low:
            return label
    return default


def lab_reference(etype, name):
    """Làm giàu node :LabTest bằng ngưỡng tham chiếu biên soạn sẵn."""
    if etype != "LabTest":
        return {}
    ref = lexicon.LAB_REFERENCE.get(name)
    if not ref:
        return {}
    return {"normal_range": ref[0], "unit": ref[1]}


# ----------------------------------------------------------------------
# Bộ tích luỹ entity / relation
# ----------------------------------------------------------------------
class Store(object):
    def __init__(self):
        self.entities = defaultdict(dict)      # type -> {name: props}
        self.relations = OrderedDict()         # key -> relation dict

    def add_entity(self, etype, name, **props):
        name = normalize(name)
        if not name:
            return None
        node = self.entities[etype].setdefault(name, {"name": name})
        for key, value in props.items():
            value = normalize(value) if isinstance(value, str) else value
            if value in (None, "", []):
                continue
            if not node.get(key):
                node[key] = value
        return name

    def add_relation(self, from_type, from_name, rel, to_type, to_name,
                     properties=None, source_url=""):
        from_name, to_name = normalize(from_name), normalize(to_name)
        if not from_name or not to_name:
            return
        if from_type == to_type and from_name == to_name:
            return
        key = (from_type, from_name, rel, to_type, to_name)
        if key in self.relations:
            existing = self.relations[key]["properties"]
            for k, v in (properties or {}).items():
                if v and not existing.get(k):
                    existing[k] = v
            return
        self.relations[key] = {
            "from_type": from_type,
            "from_name": from_name,
            "relation": rel,
            "to_type": to_type,
            "to_name": to_name,
            "properties": dict(properties or {}),
            "source_url": source_url,
        }


STORE = Store()


# ----------------------------------------------------------------------
# 2A — Xử lý trang bệnh & bài viết
# ----------------------------------------------------------------------
SECTION_RELATIONS = {
    # section trong CMS Long Châu  ->  (loại thực thể cần tìm, quan hệ, chiều)
    "symptom":             ("Symptom",      "HAS_SYMPTOM",       "disease->x"),
    "risk":                ("RiskFactor",   "INCREASES_RISK_OF", "x->disease"),
    "aetiologies":         ("RiskFactor",   "INCREASES_RISK_OF", "x->disease"),
    "diagnoseAndTreaty":   ("LabTest",      "DIAGNOSED_BY",      "disease->x"),
    "livingAndPreventive": ("RiskFactor",   "INCREASES_RISK_OF", "x->disease"),
}

TRIGGERS = {
    "HAS_SYMPTOM":       ["triệu chứng", "dấu hiệu", "biểu hiện", "gặp phải"],
    "DIAGNOSED_BY":      ["chẩn đoán", "xét nghiệm", "kiểm tra", "tầm soát", "đo ", "định lượng"],
    "INCREASES_RISK_OF": ["nguy cơ", "dễ mắc", "yếu tố", "nguyên nhân", "gây ra", "dẫn đến", "tăng khả năng"],
    "CAUSES":            ["biến chứng", "gây ra", "dẫn đến", "gây", "hậu quả", "tổn thương"],
    "TREATED_BY":        ["điều trị", "chữa", "dùng thuốc", "kiểm soát", "chỉ định"],
}


def has_trigger(sentence, relation):
    low = sentence.lower()
    return any(t in low for t in TRIGGERS.get(relation, []))


# Regex quan hệ theo đặc tả dự án (nguồn bổ sung, độ phủ rộng hơn)
RELATION_PATTERNS = [
    {"relation": "HAS_SYMPTOM",
     "pattern": re.compile(r"(tiểu đường|đái tháo đường)[^.]{0,80}?(triệu chứng|dấu hiệu|biểu hiện)([^.]{0,200})")},
    {"relation": "TREATED_BY",
     "pattern": re.compile(r"(điều trị|dùng|sử dụng)\s+([^.]{0,60}?)\s+(để|cho|trong|điều trị)\s+[^.]{0,30}?(tiểu đường|đái tháo đường)")},
    {"relation": "DIAGNOSED_BY",
     "pattern": re.compile(r"(chẩn đoán|xét nghiệm|kiểm tra|tầm soát)([^.]{0,120})")},
    {"relation": "INCREASES_RISK_OF",
     "pattern": re.compile(r"([^.]{0,80})(nguy cơ|dễ mắc|tăng khả năng)([^.]{0,80}?)(tiểu đường|đái tháo đường)")},
]


def diseases_of_article(article):
    """Bệnh chủ đề của một trang = bệnh nhận diện được trong tiêu đề."""
    title = " ".join([article.get("title") or "", article.get("name") or ""])
    found = [name for (etype, name) in find_entities(title, {"Disease"})]
    if found:
        return resolve_disease(found)
    body = find_entities(article.get("short_description") or "", {"Disease"})
    found = [name for (etype, name) in body]
    return resolve_disease(found) if found else []


def process_article(article, store):
    url = article.get("url", "")
    sections = article.get("sections") or {}
    subjects = diseases_of_article(article)

    # --- node Disease chủ đề ---------------------------------------
    for name in subjects:
        store.add_entity(
            "Disease", name,
            description=article.get("short_description") or "",
            source_url=url,
        )

    # --- quan hệ theo section (độ chính xác cao) --------------------
    for section, (etype, relation, direction) in SECTION_RELATIONS.items():
        text = sections.get(section)
        if not text or not subjects:
            continue
        for sentence in split_sentences(text):
            for (found_type, found_name), _ in find_entities(sentence, {etype}).items():
                store.add_entity(found_type, found_name, source_url=url,
                                 description=sentence[:280],
                                 **lab_reference(found_type, found_name))
                props = {}
                if relation == "HAS_SYMPTOM":
                    props["frequency"] = detect_frequency(sentence)
                for disease in subjects:
                    if direction == "disease->x":
                        store.add_relation("Disease", disease, relation,
                                           found_type, found_name, props, url)
                    else:
                        store.add_relation(found_type, found_name, relation,
                                           "Disease", disease, props, url)

    # --- biến chứng: quét toàn bộ nội dung, cần trigger -------------
    for sentence in split_sentences(article.get("content") or ""):
        comps = find_entities(sentence, {"Complication"})
        if comps and has_trigger(sentence, "CAUSES") and subjects:
            for (etype, name), _ in comps.items():
                store.add_entity(etype, name, source_url=url,
                                 description=sentence[:280])
                for disease in subjects:
                    # "Hạ đường huyết" vừa là Disease vừa là Complication ->
                    # bỏ quan hệ tự thân vô nghĩa (X gây biến chứng chính X).
                    if name == disease:
                        continue
                    store.add_relation("Disease", disease, "CAUSES",
                                       "Complication", name, {}, url)
            # Complication -[:DETECTED_BY]-> LabTest (cùng câu)
            for (_, test) in find_entities(sentence, {"LabTest"}):
                store.add_entity("LabTest", test, source_url=url,
                                 **lab_reference("LabTest", test))
                for (_, name) in comps:
                    store.add_relation("Complication", name, "DETECTED_BY",
                                       "LabTest", test, {}, url)

    # --- đồng xuất hiện cấp câu + regex (nguồn bổ sung) -------------
    for sentence in split_sentences(article.get("content") or ""):
        low = sentence.lower()
        d_found = resolve_disease([n for (t, n) in find_entities(sentence, {"Disease"})])
        if not d_found:
            continue
        for pat in RELATION_PATTERNS:
            if not pat["pattern"].search(low):
                continue
            relation = pat["relation"]
            if relation == "HAS_SYMPTOM":
                targets, ttype = find_entities(sentence, {"Symptom"}), "Symptom"
            elif relation == "DIAGNOSED_BY":
                targets, ttype = find_entities(sentence, {"LabTest"}), "LabTest"
            elif relation == "INCREASES_RISK_OF":
                targets, ttype = find_entities(sentence, {"RiskFactor"}), "RiskFactor"
            else:
                continue
            for (etype, name), _ in targets.items():
                store.add_entity(etype, name, source_url=url,
                                 description=sentence[:280],
                                 **lab_reference(etype, name))
                if relation == "INCREASES_RISK_OF":
                    for disease in d_found:
                        store.add_relation(ttype, name, relation,
                                           "Disease", disease, {}, url)
                else:
                    props = {"frequency": detect_frequency(sentence)} if relation == "HAS_SYMPTOM" else {}
                    for disease in d_found:
                        store.add_relation("Disease", disease, relation,
                                           ttype, name, props, url)


# ----------------------------------------------------------------------
# 2B — Xử lý dữ liệu thuốc
# ----------------------------------------------------------------------
FREQ_BLOCK_RE = re.compile(
    r"(rất thường gặp|thường gặp|ít gặp|hiếm gặp|rất hiếm)\s*[::]?", re.I
)


def split_frequency_blocks(text):
    """Cắt phần 'tác dụng phụ' thành các khối theo tần suất ADR."""
    text = normalize(text)
    if not text:
        return []
    parts = FREQ_BLOCK_RE.split(text)
    if len(parts) == 1:
        return [("không rõ", text)]
    blocks = []
    for i in range(1, len(parts), 2):
        label = parts[i].lower()
        label = "hiếm gặp" if "hiếm" in label else ("ít gặp" if "ít" in label else "thường gặp")
        blocks.append((label, parts[i + 1]))
    return blocks


def severity_of(name):
    if name in lexicon.SEVERE_SIDE_EFFECTS:
        return "severe"
    if name in lexicon.MODERATE_SIDE_EFFECTS:
        return "moderate"
    return "mild"


def drug_classes_of(text):
    low = normalize(text).lower()
    return [cls for cls, keys in lexicon.DRUG_CLASSES.items()
            if any(k in low for k in keys)]


def ingredients_in(text):
    low = normalize(text).lower()
    return [ing for ing in lexicon.ACTIVE_INGREDIENTS
            if re.search(r"(?<![%s])%s" % (VN_WORD, re.escape(ing)), low)]


def process_drug(drug, store):
    url = drug.get("url", "")
    name = normalize(drug.get("name"))
    if not name:
        return

    store.add_entity(
        "Drug", name,
        generic_name=drug.get("generic_name"),
        dosage_form=drug.get("dosage_form"),
        concentration=drug.get("concentration"),
        manufacturer=drug.get("manufacturer"),
        price=drug.get("price"),
        specification=drug.get("specification"),
        prescription=drug.get("prescription"),
        sku=drug.get("sku"),
        source_url=url,
    )

    own_ingredients = set(ingredients_in(
        " ".join([drug.get("generic_name") or "", name])
    ))

    # --- BELONGS_TO: danh mục website + nhóm dược lý ----------------
    categories = list(drug.get("categories") or [])
    if drug.get("category"):
        categories.append(drug["category"])
    for cat in categories:
        cat = normalize(cat)
        if not cat or cat.lower() in ("thuốc",):
            continue
        store.add_entity("DrugCategory", cat)
        store.add_relation("Drug", name, "BELONGS_TO", "DrugCategory", cat, {}, url)
    for cls in drug_classes_of(" ".join([name, drug.get("generic_name") or ""])):
        store.add_entity("DrugCategory", cls)
        store.add_relation("Drug", name, "BELONGS_TO", "DrugCategory", cls, {}, url)

    # --- TREATED_BY: Disease -> Drug (từ chỉ định) ------------------
    indications = drug.get("indications") or ""
    diseases = resolve_disease([n for (t, n) in find_entities(indications, {"Disease"})])
    for disease in diseases:
        store.add_entity("Disease", disease, source_url=url)
        snippet = normalize(indications)[:300]
        store.add_relation("Disease", disease, "TREATED_BY", "Drug", name,
                           {"indication": snippet}, url)

    # --- HAS_SIDE_EFFECT -------------------------------------------
    for freq, block in split_frequency_blocks(drug.get("side_effects") or ""):
        for (etype, se_name), _ in find_entities(block, {"SideEffect"}).items():
            store.add_entity("SideEffect", se_name, severity=severity_of(se_name))
            store.add_relation("Drug", name, "HAS_SIDE_EFFECT",
                               "SideEffect", se_name, {"frequency": freq}, url)

    # --- CONTRAINDICATED_WITH: thuốc <-> hoạt chất khác -------------
    contra = drug.get("contraindications") or ""
    for ing in ingredients_in(contra):
        if ing in own_ingredients:
            continue
        other = ing.capitalize()
        store.add_entity("Drug", other, generic_name=ing)
        store.add_relation("Drug", name, "CONTRAINDICATED_WITH", "Drug", other,
                           {"note": "trích từ mục chống chỉ định / thận trọng"}, url)


# ----------------------------------------------------------------------
# 2C — Điều phối
# ----------------------------------------------------------------------
ENTITY_OUTPUT_KEYS = [
    ("diseases", "Disease"),
    ("symptoms", "Symptom"),
    ("drugs", "Drug"),
    ("lab_tests", "LabTest"),
    ("risk_factors", "RiskFactor"),
    ("complications", "Complication"),
    ("side_effects", "SideEffect"),
    ("drug_categories", "DrugCategory"),
]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        print("[loi] Khong tim thay %s - hay chay 01_scraping.py truoc." % path)
        sys.exit(1)


def corpus_stats(articles):
    """Thống kê nhỏ dùng underthesea word_tokenize (minh hoạ tách từ tiếng Việt)."""
    if not HAS_UTS or not articles:
        return None
    sample = normalize(articles[0].get("content", ""))[:1500]
    try:
        tokens = word_tokenize(sample)
    except Exception:
        return None
    return len(tokens)


def main():
    config.ensure_dirs()
    print("=" * 70)
    print("BUOC 2 - NLP EXTRACTION")
    print("=" * 70)

    articles = load_json(config.ARTICLES_JSON)
    drugs = load_json(config.DRUGS_JSON)
    print("Nap %d bai viet, %d thuoc" % (len(articles), len(drugs)))

    ntok = corpus_stats(articles)
    if ntok:
        print("underthesea word_tokenize: %d token tren mau 1500 ky tu" % ntok)

    for i, article in enumerate(articles, 1):
        process_article(article, STORE)
        if i % 20 == 0:
            print("  ...da xu ly %d/%d bai viet" % (i, len(articles)))

    for i, drug in enumerate(drugs, 1):
        process_drug(drug, STORE)
        if i % 20 == 0:
            print("  ...da xu ly %d/%d thuoc" % (i, len(drugs)))

    entities = OrderedDict()
    for out_key, etype in ENTITY_OUTPUT_KEYS:
        entities[out_key] = sorted(STORE.entities.get(etype, {}).values(),
                                   key=lambda n: n["name"])

    relations = list(STORE.relations.values())

    with open(config.ENTITIES_JSON, "w", encoding="utf-8") as fh:
        json.dump(entities, fh, ensure_ascii=False, indent=2)
    with open(config.RELATIONS_JSON, "w", encoding="utf-8") as fh:
        json.dump(relations, fh, ensure_ascii=False, indent=2)

    print("\nKet qua trich xuat:")
    for out_key, _ in ENTITY_OUTPUT_KEYS:
        print("  %-16s %d" % (out_key, len(entities[out_key])))
    print("  %-16s %d" % ("relations", len(relations)))

    by_rel = defaultdict(int)
    for rel in relations:
        by_rel[rel["relation"]] += 1
    print("\nQuan he theo loai:")
    for rel, count in sorted(by_rel.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (rel, count))

    print("\n-> %s" % config.ENTITIES_JSON)
    print("-> %s" % config.RELATIONS_JSON)


if __name__ == "__main__":
    main()

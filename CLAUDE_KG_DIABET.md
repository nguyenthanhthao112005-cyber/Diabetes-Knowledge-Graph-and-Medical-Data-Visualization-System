# Dự án: Knowledge Graph kg_diabet
## Hướng dẫn cho Claude Code trong VS Code

---

## 1. MÔ TẢ DỰ ÁN

Xây dựng Knowledge Graph về bệnh tiểu đường (kg_diabet) trong Neo4j.
Dữ liệu được thu thập tự động từ website Long Châu (nhathuoclongchau.com.vn).

**Pipeline hoàn chỉnh:**
```
Long Châu Website
      ↓  BƯỚC 1: Scraping (requests + BeautifulSoup)
  Raw Text (bài viết, thuốc, triệu chứng)
      ↓  BƯỚC 2: NLP / NER (underthesea + regex + LLM)
  Entities + Relations (JSON)
      ↓  BƯỚC 3: Import vào Neo4j
  Knowledge Graph kg_diabet
      ↓  BƯỚC 4: Cypher Queries
  Kết quả khai thác
```

---

## 2. THÔNG TIN KẾT NỐI NEO4J

```python
NEO4J_URI      = "neo4j://127.0.0.1:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "ĐIỀN_PASSWORD_CỦA_BẠN"   # <--- thay vào đây
NEO4J_DATABASE = "kg-diabet"
```

> **Lưu ý:** Database name là `kg-diabet` (dùng dấu gạch ngang, không phải gạch dưới).

---

## 3. CẤU TRÚC FILE DỰ ÁN

Tạo cấu trúc thư mục sau:

```
kg_diabet/
├── config.py                  # cấu hình kết nối Neo4j
├── 01_scraping.py             # scrape Long Châu
├── 02_nlp_extraction.py       # NER + relation extraction
├── 03_import_neo4j.py         # import vào Neo4j
├── 04_queries.py              # Cypher queries khai thác
├── notebook/
│   └── kg_diabet_full.ipynb   # Jupyter Notebook tổng hợp
├── data/
│   ├── raw/                   # raw text từ Long Châu
│   │   ├── articles.json
│   │   └── drugs.json
│   └── processed/
│       ├── entities.json      # entities đã extract
│       └── relations.json     # relations đã extract
├── requirements.txt
└── README.md
```

---

## 4. SCHEMA KNOWLEDGE GRAPH

### Node Labels và Properties:

```cypher
(:Disease {
    name: String,           -- tên bệnh (VD: "Đái tháo đường type 2")
    icd_code: String,       -- mã ICD nếu có
    description: String,    -- mô tả ngắn
    source_url: String      -- URL nguồn
})

(:Symptom {
    name: String,           -- tên triệu chứng (VD: "Khát nước nhiều")
    description: String
})

(:Drug {
    name: String,           -- tên thuốc (VD: "Metformin")
    generic_name: String,   -- tên generic
    dosage_form: String,    -- dạng bào chế
    concentration: String,  -- hàm lượng
    manufacturer: String,   -- nhà sản xuất
    price: Float,           -- giá
    source_url: String
})

(:RiskFactor {
    name: String,           -- VD: "Béo phì", "Ít vận động"
    description: String
})

(:LabTest {
    name: String,           -- VD: "HbA1c", "Glucose máu"
    normal_range: String,   -- ngưỡng bình thường
    unit: String            -- đơn vị đo
})

(:SideEffect {
    name: String,           -- VD: "Buồn nôn", "Hạ đường huyết"
    severity: String        -- mild/moderate/severe
})

(:Complication {
    name: String,           -- VD: "Biến chứng thận", "Mù lòa"
    description: String
})

(:DrugCategory {
    name: String            -- VD: "Thuốc hạ đường huyết", "Insulin"
})
```

### Relationship Types:

```cypher
(:Disease)-[:HAS_SYMPTOM {frequency: String}]->(:Symptom)
(:Disease)-[:TREATED_BY {indication: String}]->(:Drug)
(:Disease)-[:DIAGNOSED_BY]->(:LabTest)
(:RiskFactor)-[:INCREASES_RISK_OF]->(:Disease)
(:Drug)-[:HAS_SIDE_EFFECT {frequency: String}]->(:SideEffect)
(:Drug)-[:BELONGS_TO]->(:DrugCategory)
(:Drug)-[:CONTRAINDICATED_WITH]->(:Drug)
(:Disease)-[:CAUSES]->(:Complication)
(:Complication)-[:DETECTED_BY]->(:LabTest)
```

---

## 5. CHI TIẾT TỪNG BƯỚC

---

### BƯỚC 1 — Scraping Long Châu (01_scraping.py)

**Mục tiêu:** Thu thập dữ liệu thô từ Long Châu về tiểu đường.

**Các URL cần scrape:**

```python
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
```

**Yêu cầu kỹ thuật:**
- Dùng `requests` + `BeautifulSoup` là chính
- Nếu trang dùng JavaScript động → dùng `selenium` hoặc `playwright`
- Thêm delay ngẫu nhiên `time.sleep(random.uniform(1, 3))` giữa các request
- Thêm headers giả browser:
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"
}
```
- Xử lý lỗi: retry 3 lần nếu request thất bại
- Lưu kết quả vào `data/raw/articles.json` và `data/raw/drugs.json`

**Output format articles.json:**
```json
[
  {
    "title": "Bệnh tiểu đường type 2 là gì?",
    "url": "https://...",
    "content": "Nội dung bài viết...",
    "tags": ["tiểu đường", "type 2"]
  }
]
```

**Output format drugs.json:**
```json
[
  {
    "name": "Metformin 500mg",
    "generic_name": "Metformin hydrochloride",
    "category": "Thuốc trị tiểu đường",
    "description": "Mô tả thuốc...",
    "indications": "Chỉ định điều trị...",
    "contraindications": "Chống chỉ định...",
    "side_effects": "Tác dụng phụ...",
    "dosage": "Liều dùng...",
    "manufacturer": "Công ty ABC",
    "price": 50000,
    "url": "https://..."
  }
]
```

---

### BƯỚC 2 — NLP Extraction (02_nlp_extraction.py)

**Mục tiêu:** Từ raw text → trích xuất entities và relations tự động.

**Thư viện sử dụng:**
```python
import underthesea          # NLP tiếng Việt
from underthesea import ner, word_tokenize
import re
import json
```

**2A — Entity Recognition:**

Định nghĩa entity types và keywords để nhận diện:

```python
ENTITY_PATTERNS = {
    "Disease": [
        "tiểu đường", "đái tháo đường", "type 1", "type 2",
        "đái tháo đường thai kỳ", "tiền tiểu đường", "DM"
    ],
    "Symptom": [
        "khát nước", "đi tiểu nhiều", "mờ mắt", "tê bì",
        "mệt mỏi", "sụt cân", "chậm lành vết thương",
        "đói thường xuyên", "da ngứa"
    ],
    "LabTest": [
        "HbA1c", "glucose máu", "đường huyết", "xét nghiệm máu",
        "fasting glucose", "OGTT", "insulin máu", "C-peptide"
    ],
    "RiskFactor": [
        "béo phì", "thừa cân", "ít vận động", "di truyền",
        "huyết áp cao", "cholesterol cao", "tuổi tác",
        "stress", "ăn nhiều đường"
    ],
    "Complication": [
        "biến chứng thận", "bệnh võng mạc", "biến chứng tim mạch",
        "biến chứng thần kinh", "hoại tử", "mù lòa",
        "suy thận", "nhồi máu cơ tim"
    ]
}
```

**2B — Relation Extraction từ text:**

Dùng regex patterns để trích xuất quan hệ:

```python
RELATION_PATTERNS = [
    # HAS_SYMPTOM
    {
        "pattern": r"(tiểu đường|đái tháo đường)[^.]*?(triệu chứng|biểu hiện)[^.]*?([\w\s,]+)",
        "relation": "HAS_SYMPTOM"
    },
    # TREATED_BY
    {
        "pattern": r"(điều trị|dùng|sử dụng)\s+([\w\s]+)\s+(để|cho|trong)\s+(tiểu đường|đái tháo đường)",
        "relation": "TREATED_BY"
    },
    # DIAGNOSED_BY
    {
        "pattern": r"(chẩn đoán|xét nghiệm|kiểm tra)\s+(HbA1c|glucose|đường huyết)",
        "relation": "DIAGNOSED_BY"
    },
    # INCREASES_RISK_OF
    {
        "pattern": r"(béo phì|thừa cân|ít vận động)[^.]*?(nguy cơ|dễ mắc|tăng khả năng)",
        "relation": "INCREASES_RISK_OF"
    },
]
```

**2C — Extract từ drug data:**

Từ `drugs.json`, extract trực tiếp:
- `indications` → `(:Drug)-[:TREATED_BY]->(:Disease)`
- `side_effects` → `(:Drug)-[:HAS_SIDE_EFFECT]->(:SideEffect)`
- `contraindications` → `(:Drug)-[:CONTRAINDICATED_WITH]->(:Drug)`

**Output format entities.json:**
```json
{
  "diseases": [
    {"name": "Đái tháo đường type 2", "description": "...", "source_url": "..."}
  ],
  "symptoms": [
    {"name": "Khát nước nhiều", "description": "..."}
  ],
  "drugs": [...],
  "lab_tests": [...],
  "risk_factors": [...],
  "complications": [...]
}
```

**Output format relations.json:**
```json
[
  {
    "from_type": "Disease",
    "from_name": "Đái tháo đường type 2",
    "relation": "HAS_SYMPTOM",
    "to_type": "Symptom",
    "to_name": "Khát nước nhiều",
    "properties": {"frequency": "thường gặp"},
    "source_url": "..."
  }
]
```

---

### BƯỚC 3 — Import vào Neo4j (03_import_neo4j.py)

**Mục tiêu:** Nạp entities và relations vào database `kg-diabet`.

**Yêu cầu:**

```python
from neo4j import GraphDatabase

# Kết nối
driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j", "ĐIỀN_PASSWORD")
)

# Luôn chỉ định database
session = driver.session(database="kg-diabet")
```

**Import nodes — dùng MERGE để tránh trùng:**
```cypher
MERGE (d:Disease {name: $name})
SET d.description = $description,
    d.source_url = $source_url
```

**Import relationships:**
```cypher
MATCH (a:Disease {name: $from_name})
MATCH (b:Symptom {name: $to_name})
MERGE (a)-[:HAS_SYMPTOM]->(b)
```

**Tạo indexes sau khi import:**
```cypher
CREATE INDEX IF NOT EXISTS FOR (d:Disease) ON (d.name);
CREATE INDEX IF NOT EXISTS FOR (s:Symptom) ON (s.name);
CREATE INDEX IF NOT EXISTS FOR (dr:Drug) ON (dr.name);
CREATE INDEX IF NOT EXISTS FOR (l:LabTest) ON (l.name);
CREATE INDEX IF NOT EXISTS FOR (r:RiskFactor) ON (r.name);
```

**In thống kê sau khi import:**
```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;
MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count ORDER BY count DESC;
```

---

### BƯỚC 4 — Cypher Queries (04_queries.py)

**Viết ít nhất 10 queries khai thác KG, ví dụ:**

```cypher
-- Q1: Tất cả triệu chứng của tiểu đường type 2
MATCH (d:Disease {name: "Đái tháo đường type 2"})-[:HAS_SYMPTOM]->(s:Symptom)
RETURN d.name AS disease, collect(s.name) AS symptoms;

-- Q2: Thuốc điều trị tiểu đường type 2
MATCH (d:Disease)-[:TREATED_BY]->(drug:Drug)
WHERE d.name CONTAINS "type 2"
RETURN drug.name, drug.dosage_form, drug.price;

-- Q3: Xét nghiệm chẩn đoán
MATCH (d:Disease)-[:DIAGNOSED_BY]->(t:LabTest)
RETURN d.name, collect(t.name) AS tests;

-- Q4: Yếu tố nguy cơ
MATCH (r:RiskFactor)-[:INCREASES_RISK_OF]->(d:Disease)
RETURN r.name AS risk_factor, d.name AS disease;

-- Q5: Tác dụng phụ của Metformin
MATCH (drug:Drug)-[:HAS_SIDE_EFFECT]->(se:SideEffect)
WHERE drug.name CONTAINS "Metformin"
RETURN drug.name, collect(se.name) AS side_effects;

-- Q6: Biến chứng của bệnh tiểu đường
MATCH (d:Disease)-[:CAUSES]->(c:Complication)
RETURN d.name, collect(c.name) AS complications;

-- Q7: Tìm tất cả thuốc theo danh mục
MATCH (drug:Drug)-[:BELONGS_TO]->(cat:DrugCategory)
RETURN cat.name, collect(drug.name) AS drugs;

-- Q8: Bệnh nhân có triệu chứng X dùng thuốc gì?
MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom {name: "Khát nước nhiều"})
MATCH (d)-[:TREATED_BY]->(drug:Drug)
RETURN d.name AS disease, drug.name AS treatment;

-- Q9: Graph path từ RiskFactor → Disease → Complication
MATCH path = (r:RiskFactor)-[:INCREASES_RISK_OF]->(d:Disease)-[:CAUSES]->(c:Complication)
RETURN r.name, d.name, c.name;

-- Q10: Thống kê tổng quan KG
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS total ORDER BY total DESC;
```

---

### BƯỚC 5 — Jupyter Notebook (notebook/kg_diabet_full.ipynb)

Tạo notebook tổng hợp tất cả 4 bước thành 1 file duy nhất với các sections:

```
Section 1: Giới thiệu & Mục tiêu
Section 2: Cài đặt & Kết nối Neo4j
Section 3: Scraping Long Châu
Section 4: NLP Extraction
Section 5: Import vào Neo4j
Section 6: Thống kê KG
Section 7: Cypher Queries & Kết quả
Section 8: Visualization (nếu có)
Section 9: Kết luận
```

---

## 6. REQUIREMENTS

Tạo file `requirements.txt`:

```
requests==2.31.0
beautifulsoup4==4.12.2
selenium==4.15.0
underthesea==6.8.0
neo4j==5.14.0
python-dotenv==1.0.0
jupyter==1.0.0
pandas==2.1.0
tqdm==4.66.1
lxml==4.9.3
```

---

## 7. CONFIG FILE (config.py)

```python
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI",      "neo4j://127.0.0.1:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ĐIỀN_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "kg-diabet")

SCRAPING_DELAY_MIN = 1.0
SCRAPING_DELAY_MAX = 3.0
MAX_RETRIES        = 3

DATA_DIR      = "data"
RAW_DIR       = f"{DATA_DIR}/raw"
PROCESSED_DIR = f"{DATA_DIR}/processed"
```

Tạo file `.env`:
```
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ĐIỀN_PASSWORD_CỦA_BẠN
NEO4J_DATABASE=kg-diabet
```

---

## 8. THỨ TỰ CHẠY

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Scraping
python 01_scraping.py

# 3. NLP Extraction
python 02_nlp_extraction.py

# 4. Import vào Neo4j
python 03_import_neo4j.py

# 5. Chạy queries
python 04_queries.py

# 6. Mở notebook (tùy chọn)
jupyter notebook notebook/kg_diabet_full.ipynb
```

---

## 9. XỬ LÝ LỖI THƯỜNG GẶP

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| `ConnectionRefusedError` | Neo4j chưa chạy | Vào Neo4j Desktop → Start instance |
| `403 Forbidden` khi scrape | Long Châu chặn bot | Thêm headers, tăng delay |
| `Encoding error` | Text tiếng Việt | Dùng `encoding='utf-8'` |
| `Database does not exist` | Sai tên DB | Kiểm tra lại: `kg-diabet` |
| `underthesea` lỗi | Chưa download model | Chạy: `underthesea.download('VnCoreNLP')` |

---

## 10. KIỂM TRA KẾT QUẢ

Sau khi chạy xong, vào Neo4j Desktop → Click **"Query"** → chạy:

```cypher
-- Xem tổng quan KG
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;

-- Xem 10 nodes đầu tiên
MATCH (n) RETURN n LIMIT 10;

-- Visualize graph nhỏ
MATCH (d:Disease)-[r]->(n) RETURN d, r, n LIMIT 30;
```

---

## GHI CHÚ QUAN TRỌNG

1. **Thay password** trong `config.py` và `.env` trước khi chạy
2. **Database name** là `kg-diabet` (dấu gạch ngang `-`)
3. Nếu Long Châu thay đổi HTML structure → cần điều chỉnh CSS selectors trong `01_scraping.py`
4. Chạy từng file theo thứ tự 01 → 02 → 03 → 04
5. Dữ liệu raw được lưu vào `data/raw/` trước khi xử lý

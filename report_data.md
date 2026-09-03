# BÁO CÁO DỮ LIỆU KNOWLEDGE GRAPH `kg-diabet`

## 1. Tổng quan

Knowledge Graph `kg-diabet` mô hình hóa tri thức về bệnh đái tháo đường, bao
gồm bệnh lý, thuốc, triệu chứng, xét nghiệm, yếu tố nguy cơ, biến chứng, tác
dụng phụ và nhóm thuốc. Dữ liệu được thu thập từ Nhà thuốc Long Châu, xử lý
bằng pipeline NLP tiếng Việt và lưu trong Neo4j.

Số liệu trong báo cáo này được tổng hợp từ snapshot hiện hành:

- `data/processed/entities.json`
- `data/processed/relations.json`

Snapshot chứa **185 nodes**, **1.172 relationships**, **8 loại node** và
**9 loại relationship**. Tại thời điểm tạo báo cáo Neo4j không hoạt động, vì
vậy kết quả 5 truy vấn mẫu được đối chiếu trực tiếp trên snapshot dùng để
import. Khi database `kg-diabet` chứa đúng snapshot này, kết quả Cypher tương
ứng sẽ giống nội dung trình bày bên dưới.

---

## 2. Thống kê Knowledge Graph

### 2.1. Số nodes theo từng loại

| STT | Neo4j label | Ý nghĩa | Số nodes | Tỷ lệ |
|---:|---|---|---:|---:|
| 1 | `Drug` | Thuốc/hoạt chất | 84 | 45,41% |
| 2 | `SideEffect` | Tác dụng phụ | 31 | 16,76% |
| 3 | `Symptom` | Triệu chứng | 15 | 8,11% |
| 4 | `RiskFactor` | Yếu tố nguy cơ | 15 | 8,11% |
| 5 | `Complication` | Biến chứng | 12 | 6,49% |
| 6 | `LabTest` | Xét nghiệm | 11 | 5,95% |
| 7 | `DrugCategory` | Nhóm dược lý | 9 | 4,86% |
| 8 | `Disease` | Bệnh/thể bệnh | 8 | 4,32% |
| | **Tổng cộng** | | **185** | **100%** |

### 2.2. Số relationships theo từng loại

| STT | Relationship type | Ý nghĩa | Số relationships | Tỷ lệ |
|---:|---|---|---:|---:|
| 1 | `HAS_SIDE_EFFECT` | Thuốc có tác dụng phụ | 593 | 50,60% |
| 2 | `BELONGS_TO` | Thuốc thuộc nhóm dược lý | 135 | 11,52% |
| 3 | `CONTRAINDICATED_WITH` | Cảnh báo phối hợp/chống chỉ định thuốc | 124 | 10,58% |
| 4 | `TREATED_BY` | Bệnh được điều trị bằng thuốc | 91 | 7,76% |
| 5 | `INCREASES_RISK_OF` | Yếu tố làm tăng nguy cơ mắc bệnh | 70 | 5,97% |
| 6 | `HAS_SYMPTOM` | Bệnh có triệu chứng | 55 | 4,69% |
| 7 | `DIAGNOSED_BY` | Bệnh được chẩn đoán bằng xét nghiệm | 43 | 3,67% |
| 8 | `CAUSES` | Bệnh gây ra biến chứng | 43 | 3,67% |
| 9 | `DETECTED_BY` | Biến chứng được phát hiện bằng xét nghiệm | 18 | 1,54% |
| | **Tổng cộng** | | **1.172** | **100%** |

Nhóm `HAS_SIDE_EFFECT` chiếm tỷ trọng lớn nhất vì mỗi sản phẩm thuốc có thể
liên kết với nhiều tác dụng phụ và tần suất xuất hiện khác nhau.

---

## 3. Schema Knowledge Graph

### 3.1. Node labels và thuộc tính

| Label | Thuộc tính sử dụng |
|---|---|
| `Disease` | `name`, `description`, `icd_code`, `source_url` |
| `Symptom` | `name`, `description`, `source_url` |
| `Drug` | `name`, `generic_name`, `dosage_form`, `concentration`, `manufacturer`, `price`, `specification`, `prescription`, `sku`, `source_url` |
| `RiskFactor` | `name`, `description`, `source_url` |
| `LabTest` | `name`, `description`, `normal_range`, `unit`, `source_url` |
| `SideEffect` | `name`, `severity` |
| `Complication` | `name`, `description`, `source_url` |
| `DrugCategory` | `name` |

Thuộc tính `name` được dùng làm khóa logic khi import bằng `MERGE`. Thuộc tính
`source_url` giữ liên kết tới nguồn để hỗ trợ truy vết dữ liệu.

### 3.2. Relationship schema

| Node nguồn | Relationship | Node đích | Thuộc tính quan hệ |
|---|---|---|---|
| `Disease` | `HAS_SYMPTOM` | `Symptom` | `frequency`, `source_url` |
| `Disease` | `TREATED_BY` | `Drug` | `indication`, `source_url` |
| `Disease` | `DIAGNOSED_BY` | `LabTest` | `source_url` |
| `RiskFactor` | `INCREASES_RISK_OF` | `Disease` | `source_url` |
| `Drug` | `HAS_SIDE_EFFECT` | `SideEffect` | `frequency`, `source_url` |
| `Drug` | `BELONGS_TO` | `DrugCategory` | `source_url` |
| `Drug` | `CONTRAINDICATED_WITH` | `Drug` | `note`, `source_url` |
| `Disease` | `CAUSES` | `Complication` | `source_url` |
| `Complication` | `DETECTED_BY` | `LabTest` | `source_url` |

Mô hình quan hệ tổng quát:

```text
(RiskFactor) ──INCREASES_RISK_OF──▶ (Disease)
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
          HAS_SYMPTOM            TREATED_BY          DIAGNOSED_BY
                 │                    │                    │
                 ▼                    ▼                    ▼
            (Symptom)              (Drug)              (LabTest)
                                      │
                       ┌──────────────┼──────────────────┐
                       │              │                  │
                HAS_SIDE_EFFECT   BELONGS_TO   CONTRAINDICATED_WITH
                       │              │                  │
                       ▼              ▼                  ▼
                 (SideEffect)  (DrugCategory)         (Drug)

(Disease) ──CAUSES──▶ (Complication) ──DETECTED_BY──▶ (LabTest)
```

### 3.3. Indexes

Pipeline import tạo index trên thuộc tính `name` của các label được tra cứu
thường xuyên:

```cypher
CREATE INDEX IF NOT EXISTS FOR (d:Disease) ON (d.name);
CREATE INDEX IF NOT EXISTS FOR (s:Symptom) ON (s.name);
CREATE INDEX IF NOT EXISTS FOR (dr:Drug) ON (dr.name);
CREATE INDEX IF NOT EXISTS FOR (l:LabTest) ON (l.name);
CREATE INDEX IF NOT EXISTS FOR (r:RiskFactor) ON (r.name);
CREATE INDEX IF NOT EXISTS FOR (c:Complication) ON (c.name);
CREATE INDEX IF NOT EXISTS FOR (se:SideEffect) ON (se.name);
CREATE INDEX IF NOT EXISTS FOR (dc:DrugCategory) ON (dc.name);
```

---

## 4. Năm Cypher query mẫu và kết quả

### Query 1 — Triệu chứng của đái tháo đường type 2

```cypher
MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
WHERE toLower(d.name) CONTAINS "type 2"
RETURN d.name AS disease,
       count(DISTINCT s) AS total_symptoms,
       collect(DISTINCT s.name) AS symptoms;
```

**Kết quả:**

| Bệnh | Số triệu chứng | Danh sách triệu chứng |
|---|---:|---|
| Đái tháo đường type 2 | 8 | Buồn nôn; Khát nước nhiều; Mệt mỏi; Mờ mắt; Tê bì chân tay; Vết thâm da (gai đen); Đi tiểu nhiều; Đói thường xuyên |

### Query 2 — Các thuốc điều trị đái tháo đường type 2

```cypher
MATCH (d:Disease)-[:TREATED_BY]->(drug:Drug)
WHERE toLower(d.name) CONTAINS "type 2"
RETURN DISTINCT drug.name AS drug,
       drug.dosage_form AS dosage_form,
       drug.manufacturer AS manufacturer
ORDER BY drug
LIMIT 10;
```

Toàn bộ snapshot có **50 thuốc** liên kết với bệnh đái tháo đường type 2. Mười
kết quả đầu tiên theo thứ tự tên:

| STT | Thuốc | Dạng bào chế | Nhà sản xuất/xuất xứ |
|---:|---|---|---|
| 1 | Bút tiêm Humalog Mix 75/25 KwixPen điều trị đái tháo đường (5 cây x 3ml) | Hỗn dịch tiêm trong bút tiêm nạp sẵn | Pháp |
| 2 | Bút tiêm Insulatard FlexPen 100IU/ml Novo Nordisk điều trị bệnh đái tháo đường (5 cây) | Hỗn dịch tiêm trong bút tiêm nạp sẵn | Đan Mạch |
| 3 | Bút tiêm NovoMix 30 FlexPen Novo Nordisk điều trị đái tháo đường (5 cây x 3ml) | Hỗn dịch tiêm trong bút tiêm nạp sẵn | Đan Mạch |
| 4 | Hỗn dịch tiêm Mixtard 30 Novo Nordisk điều trị bệnh đái tháo đường (10ml) | Hỗn dịch tiêm | Đan Mạch |
| 5 | Thuốc A.T Sitagliptin 100 mg An Thiên cải thiện kiểm soát đường huyết (3 vỉ x 10 viên) | Viên nén bao phim | Việt Nam |
| 6 | Thuốc A.T Vildagliptin 50mg An Thiên điều trị đái tháo đường típ 2 (3 vỉ x 10 viên) | Viên nén | Việt Nam |
| 7 | Thuốc Acarbose 50 SaVi điều trị đái tháo đường (10 vỉ x 10 viên) | Viên nén bao phim | Việt Nam |
| 8 | Thuốc Acarbose Friulchem 50mg Famar hỗ trợ điều trị đái tháo đường típ 2 (9 vỉ x 10 viên) | Viên nén | Ý |
| 9 | Thuốc DAPAGLIFLOZIN TABLET 10MG Macleods điều trị đái tháo đường típ 2 (3 vỉ x 10 viên) | Viên nén bao phim | Ấn Độ |
| 10 | Thuốc Fordia MR 500mg United điều trị đái tháo đường típ 2 (6 vỉ x 10 viên) | Viên nén bao phim giải phóng có kiểm soát | Việt Nam |

### Query 3 — Xét nghiệm dùng cho đái tháo đường type 2

```cypher
MATCH (d:Disease)-[:DIAGNOSED_BY]->(test:LabTest)
WHERE toLower(d.name) CONTAINS "type 2"
RETURN d.name AS disease,
       count(DISTINCT test) AS total_tests,
       collect(DISTINCT test.name) AS tests;
```

**Kết quả:**

| Bệnh | Số xét nghiệm | Danh sách xét nghiệm |
|---|---:|---|
| Đái tháo đường type 2 | 7 | Glucose huyết tương lúc đói; Glucose máu bất kỳ; HbA1c; Insulin máu; Nghiệm pháp dung nạp glucose (OGTT); Xét nghiệm lipid máu; Xét nghiệm đường huyết |

### Query 4 — Yếu tố làm tăng nguy cơ đái tháo đường type 2

```cypher
MATCH (risk:RiskFactor)-[:INCREASES_RISK_OF]->(d:Disease)
WHERE toLower(d.name) CONTAINS "type 2"
RETURN d.name AS disease,
       count(DISTINCT risk) AS total_risk_factors,
       collect(DISTINCT risk.name) AS risk_factors;
```

**Kết quả:**

| Bệnh | Số yếu tố | Danh sách yếu tố nguy cơ |
|---|---:|---|
| Đái tháo đường type 2 | 12 | Béo phì; Chế độ ăn nhiều đường; Hút thuốc lá; Hội chứng buồng trứng đa nang; Kháng insulin; Rối loạn lipid máu; Stress; Thừa cân; Tiền sử gia đình/di truyền; Tuổi cao; Tăng huyết áp; Ít vận động |

### Query 5 — Biến chứng của đái tháo đường type 2

```cypher
MATCH (d:Disease)-[:CAUSES]->(complication:Complication)
WHERE toLower(d.name) CONTAINS "type 2"
RETURN d.name AS disease,
       count(DISTINCT complication) AS total_complications,
       collect(DISTINCT complication.name) AS complications;
```

**Kết quả:**

| Bệnh | Số biến chứng | Danh sách biến chứng |
|---|---:|---|
| Đái tháo đường type 2 | 8 | Bệnh thần kinh đái tháo đường; Bệnh thận đái tháo đường; Bệnh võng mạc đái tháo đường; Loét bàn chân đái tháo đường; Nhiễm toan ceton; Nhiễm trùng; Nhồi máu cơ tim; Đột quỵ |

---

## 5. Cấu trúc thư mục project

```text
kg_diabet/
├── .env                         # thông tin kết nối cục bộ, không commit
├── .env.example                 # cấu hình mẫu
├── .gitignore
├── app.py                       # Flask API + Neo4j/JSON repository
├── config.py                    # cấu hình Neo4j, scraping và đường dẫn
├── lexicon.py                   # từ điển thực thể y khoa tiếng Việt
├── 01_scraping.py               # thu thập bài viết và thuốc
├── 02_nlp_extraction.py         # trích xuất entity và relationship
├── 03_import_neo4j.py           # import dữ liệu, tạo index
├── 04_queries.py                # bộ Cypher query khai thác KG
├── requirements.txt             # Python dependencies
├── README.md                    # hướng dẫn dự án và web app
├── CLAUDE_KG_DIABET.md          # đặc tả ban đầu của dự án
├── report_data.md               # báo cáo dữ liệu này
├── data/
│   ├── raw/
│   │   ├── articles.json        # bài viết thô
│   │   └── drugs.json           # dữ liệu thuốc thô
│   └── processed/
│       ├── entities.json        # nodes đã chuẩn hóa
│       └── relations.json       # relationships đã trích xuất
├── notebook/
│   └── kg_diabet_full.ipynb     # notebook tổng hợp pipeline
├── tests/
│   └── test_web_app.py          # smoke tests cho web API
└── web/
    ├── index.html               # giao diện dashboard
    ├── styles.css               # theme và responsive layout
    ├── app.js                   # graph canvas, tìm kiếm, thống kê
    └── favicon.svg              # biểu tượng ứng dụng
```

Các thư mục sinh tự động như `.venv/`, `__pycache__/` và `.pytest_cache/` không
được liệt kê trong cấu trúc logic của project.

---

## 6. Tech stack

| Tầng | Công nghệ | Vai trò |
|---|---|---|
| Ngôn ngữ backend | Python 3.12 | Pipeline dữ liệu và web API |
| Web framework | Flask 3 | Phục vụ giao diện và các endpoint `/api/*` |
| WSGI server | Waitress 3 | Chạy web server ổn định trên Windows/LAN |
| Graph database | Neo4j 5 | Lưu nodes, relationships và thực thi Cypher |
| Neo4j client | Neo4j Python Driver | Kết nối ứng dụng Python với database `kg-diabet` |
| Cấu hình | `python-dotenv` | Đọc URI, user, password và database từ `.env` |
| Frontend | HTML5, CSS3, JavaScript ES6 | Dashboard responsive, tra cứu và tương tác người dùng |
| Graph visualization | HTML Canvas 2D | Force-directed graph, kéo, zoom, chọn và làm nổi node; không phụ thuộc thư viện graph ngoài |
| Thu thập dữ liệu | Requests, BeautifulSoup, lxml, Selenium | Scraping nội dung bài viết và thuốc |
| NLP tiếng Việt | underthesea, regex, lexicon tùy chỉnh | Tách câu/từ, nhận diện entity và trích xuất relation |
| Xử lý/phân tích | Pandas, NetworkX, Matplotlib | Thống kê, phân tích và trực quan hóa trong notebook |
| Notebook | Jupyter | Tổng hợp và trình diễn pipeline end-to-end |
| Định dạng dữ liệu | JSON UTF-8 | Snapshot raw/processed và chế độ fallback khi Neo4j tắt |
| Kiểm thử | Python `unittest`, Flask test client | Kiểm tra API, tìm kiếm, graph và node detail |

### Kiến trúc web app

```text
Trình duyệt desktop/mobile
          │ HTTP / JSON
          ▼
      Flask REST API
          │
          ├── Neo4j `kg-diabet` (ưu tiên khi online)
          │
          └── JSON snapshot (fallback chỉ đọc khi Neo4j offline)
```

Web server lắng nghe trên `0.0.0.0`, vì vậy thiết bị di động trong cùng mạng
Wi-Fi có thể truy cập qua địa chỉ IP LAN của máy tính.

---

## 7. Lưu ý về dữ liệu

- Knowledge Graph phục vụ học tập và nghiên cứu, không thay thế chẩn đoán hoặc
  chỉ định điều trị của nhân viên y tế.
- Tên thuốc bao gồm sản phẩm thương mại và một số hoạt chất tham chiếu dùng làm
  đầu mút cho quan hệ `CONTRAINDICATED_WITH`.
- Quan hệ `CONTRAINDICATED_WITH` được trích từ phần chống chỉ định/thận trọng;
  cần đọc thuộc tính `note` và kiểm tra lại `source_url` trước khi diễn giải.
- Giá của thuốc kê đơn có thể để trống do nguồn công khai không công bố giá.

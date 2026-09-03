# Knowledge Graph kg_diabet

Knowledge Graph về **bệnh đái tháo đường (tiểu đường)** xây dựng trong Neo4j từ
dữ liệu thu thập tự động trên website Nhà thuốc Long Châu
(`nhathuoclongchau.com.vn`).

```
Long Châu Website
      │  BƯỚC 1 — Scraping (requests + BeautifulSoup, parse __NEXT_DATA__)
      ▼
  Raw text  (data/raw/articles.json, data/raw/drugs.json)
      │  BƯỚC 2 — NLP / NER (underthesea + lexicon + luật)
      ▼
  Entities + Relations  (data/processed/entities.json, relations.json)
      │  BƯỚC 3 — Import Neo4j (MERGE + UNWIND batch)
      ▼
  Knowledge Graph  kg-diabet
      │  BƯỚC 4 — Cypher queries
      ▼
  Kết quả khai thác
```

---

## 1. Cài đặt

```bash
pip install -r requirements.txt
```

Tạo file `.env` (đã có sẵn trong repo, sửa lại password của bạn):

```
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password của bạn>
NEO4J_DATABASE=kg-diabet
```

Có thể sao chép `.env.example` nếu cần tạo lại file cấu hình. `.env` đã được
đưa vào `.gitignore` để tránh vô tình commit mật khẩu.

> Database `kg-diabet` dùng **dấu gạch ngang**, phải tồn tại và ở trạng thái
> *online* trong Neo4j Desktop trước khi chạy Bước 3.

### Web app GlucoGraph

Dashboard web có sẵn các chức năng:

* đồ thị force-directed tương tác (kéo, zoom, lọc, tìm node, xem chi tiết);
* tra cứu thuốc, triệu chứng, xét nghiệm, biến chứng và yếu tố nguy cơ;
* thống kê node, quan hệ, phân bố loại và thực thể trung tâm;
* giao diện responsive cho máy tính và điện thoại;
* tự động dùng snapshot trong `data/processed/` nếu Neo4j đang tắt.

Khởi động:

```bash
pip install -r requirements.txt
python app.py
```

Mở trên máy tính: **http://127.0.0.1:5000**.

Để mở trên điện thoại, kết nối điện thoại và máy tính vào cùng Wi-Fi, sau đó
truy cập địa chỉ LAN được in ngay khi chạy `python app.py`, ví dụ
`http://192.168.0.101:5000`. Nếu Windows Firewall hỏi quyền, chọn **Allow access**
cho mạng **Private**. Server mặc định lắng nghe trên `0.0.0.0` nên không cần sửa
code.

Các biến tùy chọn:

```bash
APP_PORT=8000           # đổi cổng (PowerShell: $env:APP_PORT="8000")
FLASK_DEBUG=1           # bật debug server khi phát triển
```

Kiểm thử nhanh:

```bash
python -m unittest discover -s tests -v
```

---

## 2. Thứ tự chạy

```bash
python 01_scraping.py         # thu thập raw text  -> data/raw/
python 02_nlp_extraction.py   # NER + relation     -> data/processed/
python 03_import_neo4j.py     # nạp vào Neo4j      (thêm --reset để xoá sạch trước)
python 04_queries.py          # chạy 15 Cypher query khai thác

jupyter notebook notebook/kg_diabet_full.ipynb   # bản tổng hợp cả 4 bước
```

`04_queries.py` nhận tham số để chạy chọn lọc: `python 04_queries.py 2 5 9`.

---

## 3. Kết quả thực tế (lần chạy 01/09/2026)

**Bước 1 — Scraping:** 95 trang (15 trang bệnh + 80 bài viết) và 64 thuốc.

**Bước 2 — NLP:** 175 thực thể, 1172 quan hệ.

**Bước 3 — Neo4j `kg-diabet`:** **185 node / 1172 quan hệ**

| Node | Số lượng | | Quan hệ | Số lượng |
|---|---:|---|---|---:|
| `Drug` | 84 | | `HAS_SIDE_EFFECT` | 593 |
| `SideEffect` | 31 | | `BELONGS_TO` | 135 |
| `Symptom` | 15 | | `CONTRAINDICATED_WITH` | 124 |
| `RiskFactor` | 15 | | `TREATED_BY` | 91 |
| `Complication` | 12 | | `INCREASES_RISK_OF` | 70 |
| `LabTest` | 11 | | `HAS_SYMPTOM` | 55 |
| `DrugCategory` | 9 | | `CAUSES` | 43 |
| `Disease` | 8 | | `DIAGNOSED_BY` | 43 |
| | | | `DETECTED_BY` | 18 |

8 thể bệnh được canonical hoá: *Đái tháo đường*, *type 1*, *type 2*, *thai kỳ*,
*tiền đái tháo đường*, *ở trẻ em*, *hạ đường huyết*, *tăng đường huyết*.

9 nhóm dược lý: Biguanid (29 thuốc), Insulin (13), ức chế DPP-4 (12),
Sulfonylurea (7), ức chế SGLT2 (7), ức chế alpha-glucosidase (3)…

---

## 4. Cấu trúc file

| File | Vai trò |
|------|---------|
| `config.py` | Cấu hình Neo4j, nguồn dữ liệu, đường dẫn, tham số scraping |
| `lexicon.py` | Từ điển thực thể y khoa tiếng Việt (canonical + biến thể) |
| `01_scraping.py` | Thu thập bài viết / trang bệnh / trang thuốc từ Long Châu |
| `02_nlp_extraction.py` | Nhận diện thực thể + trích xuất quan hệ |
| `03_import_neo4j.py` | Import vào Neo4j, tạo index, in thống kê |
| `04_queries.py` | 15 Cypher query khai thác KG |
| `notebook/kg_diabet_full.ipynb` | Notebook tổng hợp toàn bộ pipeline |
| `data/raw/` | `articles.json`, `drugs.json` |
| `data/processed/` | `entities.json`, `relations.json` |

---

## 5. Schema Knowledge Graph

### Node labels

| Label | Thuộc tính chính |
|-------|------------------|
| `Disease` | `name`, `description`, `icd_code`, `source_url` |
| `Symptom` | `name`, `description` |
| `Drug` | `name`, `generic_name`, `dosage_form`, `concentration`, `manufacturer`, `price`, `specification`, `prescription`, `sku`, `source_url` |
| `RiskFactor` | `name`, `description` |
| `LabTest` | `name`, `normal_range`, `unit` |
| `SideEffect` | `name`, `severity` (mild / moderate / severe) |
| `Complication` | `name`, `description` |
| `DrugCategory` | `name` |

### Relationship types

```cypher
(:Disease)-[:HAS_SYMPTOM {frequency}]->(:Symptom)
(:Disease)-[:TREATED_BY {indication}]->(:Drug)
(:Disease)-[:DIAGNOSED_BY]->(:LabTest)
(:RiskFactor)-[:INCREASES_RISK_OF]->(:Disease)
(:Drug)-[:HAS_SIDE_EFFECT {frequency}]->(:SideEffect)
(:Drug)-[:BELONGS_TO]->(:DrugCategory)
(:Drug)-[:CONTRAINDICATED_WITH {note}]->(:Drug)
(:Disease)-[:CAUSES]->(:Complication)
(:Complication)-[:DETECTED_BY]->(:LabTest)
```

Mọi quan hệ đều mang thêm `source_url` để truy vết về trang gốc.

---

## 6. Ghi chú kỹ thuật

**Vì sao không scrape `/tim-kiem?keyword=...`?**
`robots.txt` của Long Châu chặn `/tim-kiem` và mọi URL `*?keyword=`, đồng thời
trang này render danh sách sản phẩm bằng JavaScript nên `requests` chỉ nhận về
mảng rỗng. Pipeline dùng các nguồn *được phép crawl* và render sẵn server-side:

* `sitemap_benh.xml` → 14 trang bệnh liên quan tiểu đường (có sẵn các mục
  *triệu chứng*, *nguyên nhân*, *yếu tố nguy cơ*, *chẩn đoán & điều trị*).
* `sitemap_baiviet1..4.xml` → bài viết chuyên đề tiểu đường.
* `sitemap_thuoc.xml` lọc theo hoạt chất (metformin, insulin, gliclazide,
  glibenclamide, glucagon, gliptin, gliflozin…) + trang danh mục
  `/thuoc/thuoc-tri-tieu-duong`.

**Vì sao parse `__NEXT_DATA__` thay vì CSS selector?**
Long Châu là ứng dụng Next.js — toàn bộ dữ liệu của trang nằm trong thẻ
`<script id="__NEXT_DATA__">` dưới dạng JSON. Đọc JSON vừa đầy đủ hơn (có cả
chỉ định, chống chỉ định, ADR, giá, nhà sản xuất) vừa không vỡ khi site đổi
giao diện.

**Kỹ thuật NLP.** Thuật ngữ y khoa tiếng Việt là cụm từ đa âm tiết cố định nên
dictionary-based NER cho độ chính xác cao hơn NER thống kê. `lexicon.py` định
nghĩa *canonical name → danh sách biến thể*, nhờ đó "tiểu đường tuýp 2",
"đái tháo đường type 2", "tiểu đường loại 2" gộp về **cùng một node**. Alias dài
được ưu tiên khớp trước alias ngắn để "đái tháo đường type 2" không bị nuốt
thành "đái tháo đường". `underthesea` đảm nhiệm tách câu (`sent_tokenize`) và
tách từ (`word_tokenize`) — quan hệ chỉ được sinh khi hai thực thể cùng xuất
hiện trong **một câu** và câu đó chứa *trigger word* phù hợp, hoặc khi thực thể
nằm trong đúng section ngữ nghĩa của trang bệnh (mục "Triệu chứng" → `HAS_SYMPTOM`,
mục "Yếu tố nguy cơ" → `INCREASES_RISK_OF`, …).

---

## 7. Kiểm tra kết quả trong Neo4j Browser

```cypher
// Tổng quan
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;

// 10 node đầu tiên
MATCH (n) RETURN n LIMIT 10;

// Visualize đồ thị quanh các bệnh
MATCH (d:Disease)-[r]->(n) RETURN d, r, n LIMIT 30;

// Toàn cảnh một thể bệnh
MATCH p = (:Disease {name: "Đái tháo đường type 2"})-[*1..1]-() RETURN p;
```

---

## 8. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| `ConnectionRefusedError` / `ServiceUnavailable` | Neo4j chưa chạy | Neo4j Desktop → Start instance |
| `Database does not exist` | Sai tên DB | Phải là `kg-diabet` (gạch ngang) |
| `AuthError` | Sai password | Sửa `NEO4J_PASSWORD` trong `.env` |
| `403` / `429` khi scrape | Bị chặn bot | Tăng `SCRAPING_DELAY_MIN/MAX` trong `config.py` |
| `UnicodeEncodeError` khi in ra console | Console Windows dùng cp1252 | `set PYTHONIOENCODING=utf-8` trước khi chạy |
| `articles.json` rỗng | Long Châu đổi cấu trúc | Kiểm tra lại key trong `__NEXT_DATA__` ở `01_scraping.py` |

---

## 9. Lưu ý về dữ liệu

Dữ liệu được trích xuất tự động từ nội dung thương mại/phổ thông của một nhà
thuốc bán lẻ. Knowledge Graph này phục vụ mục đích **học tập và nghiên cứu**,
**không dùng để chẩn đoán hay điều trị**. Mọi node và quan hệ đều giữ
`source_url` để đối chiếu lại nguồn gốc.

Ba giới hạn cần biết khi đọc kết quả:

* **`Drug.price` luôn rỗng.** Cả 64 thuốc thu được đều là **thuốc kê đơn**, và
  Long Châu không công bố giá thuốc kê đơn trên trang công khai (`price: null`
  trong dữ liệu gốc). Đây là giới hạn của nguồn, không phải lỗi pipeline — code
  vẫn đọc giá bình thường nếu gặp thuốc không kê đơn.
* **`CONTRAINDICATED_WITH` chỉ là cảnh báo, không phải chống chỉ định tuyệt đối.**
  Mục "chống chỉ định / thận trọng" của Long Châu trộn lẫn chống chỉ định thật
  với tương tác thuốc và phối hợp cần theo dõi (ví dụ Metformin + Insulin là
  phác đồ phối hợp hợp lệ, nhưng vẫn được nhắc trong mục này). Quan hệ mang
  thuộc tính `note` ghi rõ nguồn gốc trích xuất.
* **Node `Drug` gồm cả "hoạt chất tham chiếu".** Ngoài 64 sản phẩm thật, đồ thị
  có thêm ~20 node kiểu `Insulin`, `Corticosteroid`, `Furosemid`… sinh ra từ tên
  hoạt chất được nhắc trong mục chống chỉ định. Chúng không có `sku`/`source_url`
  và chỉ đóng vai trò đầu mút cho `CONTRAINDICATED_WITH`.

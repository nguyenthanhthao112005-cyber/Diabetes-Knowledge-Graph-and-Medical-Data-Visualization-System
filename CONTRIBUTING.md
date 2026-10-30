# Đóng góp cho dự án

Cảm ơn bạn đã quan tâm tới Diabetes Knowledge Graph & Medical Data
Visualization. Mọi đóng góp nên tập trung vào chất lượng dữ liệu, khả năng truy
vết nguồn và trải nghiệm tra cứu.

## Quy trình phát triển

1. Fork repository và tạo nhánh từ `main`.
2. Tạo virtual environment, sau đó cài `requirements.txt`.
3. Không commit `.env`, mật khẩu Neo4j hoặc dữ liệu có thông tin cá nhân.
4. Giữ nguyên `source_url` khi bổ sung thực thể hay quan hệ mới.
5. Chạy kiểm thử trước khi tạo pull request:

   ```bash
   python -m compileall -q .
   python -m unittest discover -s tests -v
   ```

6. Trong pull request, mô tả mục tiêu, thay đổi dữ liệu/schema (nếu có) và cách
   kiểm chứng kết quả.

## Quy ước dữ liệu

- Tên thực thể dùng dạng canonical, còn các cách viết khác được đặt trong
  lexicon alias.
- Quan hệ mới phải có nguồn và tránh suy diễn y khoa không được văn bản hỗ trợ.
- Không đưa dữ liệu bệnh nhân hoặc thông tin định danh cá nhân vào repository.
- Khi thay đổi schema, cập nhật cả `README.md`, pipeline import và API liên quan.

## Báo lỗi

Với lỗi thông thường, hãy tạo GitHub Issue kèm các bước tái hiện, phiên bản
Python, hệ điều hành và log đã loại bỏ thông tin nhạy cảm. Với lỗ hổng bảo mật,
hãy làm theo [SECURITY.md](SECURITY.md).

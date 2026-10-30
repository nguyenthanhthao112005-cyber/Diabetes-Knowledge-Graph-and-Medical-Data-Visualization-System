# Chính sách bảo mật

## Phiên bản được hỗ trợ

Nhánh `main` là phiên bản đang được duy trì.

## Báo cáo lỗ hổng

Không đăng công khai mật khẩu Neo4j, token, nội dung `.env` hoặc chi tiết khai
thác lỗ hổng đang hoạt động. Hãy dùng mục **Security → Report a vulnerability**
của repository (nếu đã bật Private vulnerability reporting) hoặc liên hệ riêng
với chủ repository qua hồ sơ GitHub.

Trong báo cáo, vui lòng cung cấp:

- thành phần và phiên bản bị ảnh hưởng;
- các bước tái hiện tối thiểu;
- mức độ ảnh hưởng dự kiến;
- đề xuất khắc phục nếu có.

Dự án này là công cụ học tập/nghiên cứu và không xử lý dữ liệu bệnh nhân. Nếu
bạn dùng dự án trong môi trường thật, hãy bảo vệ Neo4j bằng xác thực mạnh, giới
hạn truy cập mạng và không bật `FLASK_DEBUG` ở production.

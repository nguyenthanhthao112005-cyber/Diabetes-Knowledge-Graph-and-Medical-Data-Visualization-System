"""
Cấu hình ứng dụng: nạp API key và đường dẫn dữ liệu từ biến môi trường.

Các khoá bí mật KHÔNG được viết thẳng trong mã nguồn. Thứ tự ưu tiên khi nạp:

1. Biến môi trường của hệ điều hành (dùng cho CI/CD, máy chủ)
2. File ``.env`` đặt ở thư mục gốc dự án (dùng khi phát triển cục bộ)

Xem ``.env.example`` để biết danh sách biến cần khai báo.
"""

import os
import sys
from pathlib import Path

def _configure_console_encoding() -> None:
    """Ép stdout/stderr dùng UTF-8.

    Console mặc định của Windows (cp1252/cp1258) không mã hoá được tiếng Việt
    có dấu, khiến mọi lệnh ``print`` thông báo lỗi tự nó ném UnicodeEncodeError
    và làm sập ứng dụng. Gọi ngay khi import để mọi module đều an toàn.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


_configure_console_encoding()

# Thư mục gốc của dự án (thư mục chứa src/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Nạp file .env nếu có python-dotenv; nếu không thì đọc thủ công để
# ứng dụng vẫn chạy được khi người dùng chưa cài thêm thư viện.
_ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path) -> None:
    """Đọc file .env đơn giản (KEY=VALUE) mà không cần thư viện ngoài."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        # Biến môi trường thật luôn được ưu tiên hơn file .env
        os.environ.setdefault(key, value)


try:
    from dotenv import load_dotenv

    load_dotenv(_ENV_FILE)
except ImportError:
    _load_env_file(_ENV_FILE)


def _get_key(*names: str) -> str:
    """Trả về giá trị đầu tiên tìm thấy trong các tên biến môi trường."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


# API key cho Google Gemini.
# Khai báo GOOGLE_API_KEY là đủ cho cả ba tính năng AI; các biến còn lại chỉ
# cần thiết khi bạn muốn tách hạn mức (quota) riêng cho từng tính năng.
GOOGLE_API_KEY = _get_key("GOOGLE_API_KEY")
GOOGLE_API_KEY_AUTO_INPUT = _get_key("GOOGLE_API_KEY_AUTO_INPUT", "GOOGLE_API_KEY")
GOOGLE_API_KEY_OCR = _get_key("GOOGLE_API_KEY_OCR", "GOOGLE_API_KEY")

# Tên model Gemini dùng chung cho ChatBot, Auto Input và OCR
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Đường dẫn file cơ sở dữ liệu SQLite. Dùng đường dẫn tuyệt đối để ứng dụng
# luôn mở đúng file dù được khởi chạy từ thư mục nào.
DB_PATH = str(Path(os.environ.get("FINANCE_DB_PATH", BASE_DIR / "finance.db")).resolve())


def is_ai_configured() -> bool:
    """Kiểm tra đã cấu hình ít nhất một API key cho các tính năng AI chưa."""
    return bool(GOOGLE_API_KEY or GOOGLE_API_KEY_AUTO_INPUT or GOOGLE_API_KEY_OCR)

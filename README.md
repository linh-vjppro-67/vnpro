# PRO Enterprise Hub

Ứng dụng quản trị tổng thể dành cho doanh nghiệp kinh doanh, lắp đặt và bảo hành cân điện tử/giải pháp kỹ thuật. Hệ thống tập trung dữ liệu bán hàng, chi phí, đơn hàng, dự án kỹ thuật, kho, công nợ và CSKH.

## Kiến trúc

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + JWT + RBAC
- Database: PostgreSQL (Docker), SQLite dùng được cho local demo
- Reverse proxy: Nginx
- Production package: Docker Compose, health check, audit log, seed data, API docs

## Chạy nhanh bằng Docker

```bash
cp .env.example .env
docker compose up --build
```

- Web: http://localhost
- API docs: http://localhost/api/docs
- Health: http://localhost/api/health

Tài khoản demo:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Ban giám đốc | director@proscale.vn | Demo@123 |
| Kinh doanh | sales@proscale.vn | Demo@123 |
| Kế toán | accounting@proscale.vn | Demo@123 |
| Kho | warehouse@proscale.vn | Demo@123 |
| Kỹ thuật | technical@proscale.vn | Demo@123 |
| Quản trị hệ thống | admin@proscale.vn | Demo@123 |

## Chạy local không Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000

cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Biến môi trường quan trọng

- `SECRET_KEY`: thay bằng chuỗi ngẫu nhiên mạnh khi deploy.
- `DATABASE_URL`: PostgreSQL production hoặc SQLite local.
- `CORS_ORIGINS`: danh sách domain frontend.
- `VITE_API_URL`: URL API, mặc định `/api` khi chạy qua Nginx.

## Phạm vi production starter

Đã có: xác thực, phân quyền, dashboard, bán hàng, ngân sách/chi phí, đơn hàng/dự án, tồn kho, công nợ, CSKH, integration log, audit log, Docker/Nginx, test API cơ bản.

Trước go-live thực tế nên bổ sung: SSO/MFA, backup/restore, object storage cho hồ sơ, email/SMS thật, workflow phê duyệt theo hạn mức, mapping API hệ thống thực tế, penetration test và quy trình vận hành/giám sát.

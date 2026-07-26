# VNPRO Enterprise Hub

Ứng dụng quản trị tổng thể dành cho Công ty Cổ phần Giải pháp và Công nghệ Cân điện tử Pro Việt Nam. Hệ thống tập trung dữ liệu bán hàng, chi phí, đơn hàng, dự án kỹ thuật, kho, công nợ và CSKH.

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
| Ban giám đốc | director@vnpro.vn | Demo@123 |
| Kinh doanh | sales@vnpro.vn | Demo@123 |
| Kế toán | accounting@vnpro.vn | Demo@123 |
| Kho | warehouse@vnpro.vn | Demo@123 |
| Kỹ thuật | technical@vnpro.vn | Demo@123 |
| Quản trị hệ thống | admin@vnpro.vn | Demo@123 |

## Chạy local không Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed_mockup
uvicorn app.main:app --reload --port 8000
```

Để nạp thêm bộ dữ liệu trình diễn đầy đủ các trạng thái nghiệp vụ:

```bash
cd backend
python -m app.seed_mockup
```

Lệnh này chỉ cộng thêm các mã `*-DEMO-*` còn thiếu, có thể chạy lại nhiều lần
và không xóa hoặc ghi đè dữ liệu người dùng đã tạo.

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

## Phạm vi nghiệp vụ đã triển khai

- CRM: Lead, Opportunity, yêu cầu khảo sát, BOM, báo giá nhiều phiên bản, duyệt và khóa báo giá.
- Hợp đồng: lịch thanh toán, duyệt, ký và lưu thông tin người ký/file ký; sinh Sales Order kế thừa dòng hàng.
- Mua hàng và kho: PR, duyệt mua, PO, kiểm chứng từ, kiểm nhận đạt/cách ly/từ chối, nhập kho, giữ và xuất hàng.
- Triển khai: Project, Work Order, checklist, nghiệm thu và điều kiện phát hành hóa đơn/đóng đơn.
- Ngân sách: kiểm tra Budget, committed cost, duyệt chi, thanh toán và Budget vs Actual.
- Công nợ: hóa đơn, phải thu, nhật ký nhắc nợ/cam kết, thu tiền và kiểm soát số dư.
- CSKH: hồ sơ bảo hành, ticket SLA, phản hồi, xử lý, khách hàng xác nhận, đóng và mở lại.
- Nền tảng: JWT, RBAC phía backend, khóa tài khoản tức thời, audit log, thông báo nội bộ, tệp đính kèm có version, Docker/Nginx và health check.

Trước khi go-live trên hạ tầng thật, đơn vị vận hành vẫn cần thay toàn bộ secret/mật khẩu demo, cấu hình backup PostgreSQL và object storage, SMTP/SMS thực tế, TLS/domain, giám sát, kiểm thử tải và penetration test.

## Luồng nghiệp vụ trung tâm VNPRO

Hệ thống lấy `Contract → SalesOrder → Project` làm xương sống. Màn hình
**Luồng đơn hàng** (`/order-flow`) tổng hợp:

```text
CRM → Khảo sát/BOM → Báo giá → Hợp đồng → Sales Order
    → Kiểm tồn → Giữ hàng hoặc Yêu cầu mua → Xuất kho
    → Project/Work Order → Nghiệm thu → Hóa đơn
    → Công nợ/Phiếu thu → Đóng đơn → CSKH/Bảo hành
```

Quy tắc dữ liệu quan trọng:

- Sales Order phải có dòng hàng trước khi xác nhận.
- Không giữ hoặc xuất hàng nếu tồn khả dụng không đủ.
- Phần thiếu có thể tự động sinh yêu cầu mua gắn với Project.
- Chỉ nghiệm thu đơn khi có biên bản nghiệm thu đã duyệt.
- Chỉ phát hành hóa đơn sau nghiệm thu và tổng hóa đơn không vượt giá trị đơn.
- Phiếu thu không được vượt số công nợ còn lại.
- Chỉ đóng đơn khi đã thu đủ tiền và Project đã hoàn tất.
- Đề nghị chi đi qua `Draft → Submitted/Over Budget → Approved → Paid`; actual
  cost chỉ cập nhật ngân sách khi đã thanh toán.

### Nâng cấp database

```bash
cd backend
.venv/bin/alembic upgrade head
```

Migration `0006_vnpro_order_flow` bổ sung luồng đơn hàng trung tâm. Migration
`0007_srs_production_core` bổ sung kiểm nhận hàng, quarantine, yêu cầu kỹ thuật
SLA, version hồ sơ, cấu hình duyệt, committed budget, bảo hành và nhắc nợ.
Migration `0008_integrity_hardening` và `0009_invoice_atomicity` bổ sung foreign
key/check/unique constraint, audit context, chống ghi vượt tồn/ngân sách/công nợ
và phát hành hóa đơn nguyên tử.

Toàn bộ revision Alembic dùng DDL bất biến (`op.create_table`, `op.add_column`,
`op.create_index`) và có downgrade đối xứng. Bộ test dựng database bằng chính
chuỗi Alembic thay vì `Base.metadata.create_all`.

### Bảo mật và tính toàn vẹn

- SQLite local/test bật `PRAGMA foreign_keys=ON`; PostgreSQL vẫn là database production khuyến nghị.
- JWT phiên đăng nhập được giữ trong cookie `HttpOnly`, frontend không lưu token trong `localStorage`.
- Tài khoản tự khóa 15 phút sau 5 lần nhập sai liên tiếp.
- Các cập nhật tồn kho, committed budget, công nợ và tổng hóa đơn dùng conditional atomic update.
- Attachment kiểm tra entity/quyền, chuẩn hóa path, giới hạn dung lượng và xác minh magic bytes.
- Audit log có request ID, IP, before/after và được bảo vệ append-only ở ORM.

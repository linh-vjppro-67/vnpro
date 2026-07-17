# Kiến trúc hệ thống

## Luồng nghiệp vụ lõi

1. Marketing/Kinh doanh tạo khách hàng và cơ hội.
2. Sales phối hợp Kỹ thuật và Sales Admin để khảo sát, báo giá và chốt đơn.
3. Đơn hàng được chuyển thành dự án triển khai kỹ thuật.
4. Kho xuất hàng theo đơn/dự án, Kế toán theo dõi hóa đơn và công nợ.
5. Chi phí được ghi nhận theo phòng ban/dự án, trình duyệt và đối chiếu ngân sách.
6. CSKH tiếp nhận bảo hành, điều phối Kỹ thuật và theo dõi SLA.
7. Dashboard tổng hợp dữ liệu cho Ban giám đốc.

## Thành phần

- `frontend`: SPA React, route-based code splitting, responsive UI.
- `backend`: REST API FastAPI, JWT, RBAC, audit log.
- `db`: PostgreSQL production; Alembic quản lý schema.
- `nginx`: reverse proxy, single public endpoint.

## Dữ liệu chính

User, Customer, Opportunity, SalesOrder, Project, Budget, Expense, Product, StockMovement, Receivable, SupportTicket, IntegrationLog, AuditLog.


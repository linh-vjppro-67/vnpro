from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import (
    AcceptanceRecord, ApprovalRequest, Budget, Contract, ContractPaymentSchedule, Customer, Expense, Lead, Opportunity,
    Product, Project, PurchaseOrder, PurchaseOrderItem, PurchaseRequest, Quotation, QuotationItem, Receivable,
    SalesOrder, StockMovement, StockReservation, Supplier, SupportTicket, Task, User, WorkOrder,
)

USERS = [
    ("admin@proscale.vn", "Quản trị hệ thống", "SYSTEM_ADMIN", "CNTT"),
    ("director@proscale.vn", "Nguyễn Minh Giám", "DIRECTOR", "Ban Giám đốc"),
    ("sales@proscale.vn", "Trần Hoài Sales", "SALES", "Kinh doanh"),
    ("accounting@proscale.vn", "Lê Mai Kế toán", "ACCOUNTING", "Kế toán"),
    ("warehouse@proscale.vn", "Phạm Anh Kho", "WAREHOUSE", "Kho"),
    ("technical@proscale.vn", "Vũ Nam Kỹ thuật", "TECH_FIELD", "Kỹ thuật"),
    ("techsolution@proscale.vn", "Đặng Quốc Kỹ thuật giải pháp", "TECH_SOLUTION", "Kỹ thuật"),
    ("salesadmin@proscale.vn", "Đỗ Lan Sales Admin", "SALES_ADMIN", "Kinh doanh"),
    ("cskh@proscale.vn", "Ngô Hà CSKH", "CUSTOMER_SERVICE", "CSKH"),
    ("hr@proscale.vn", "Bùi An Nhân sự", "HR", "Nhân sự"),
]


def seed():
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)):
            return
        users = []
        for email, name, role, dept in USERS:
            u = User(email=email, full_name=name, role=role, department=dept, hashed_password=get_password_hash("Demo@123"))
            db.add(u); users.append(u)
        db.flush()
        admin, director, sales, accounting, warehouse, technical, techsolution, salesadmin, cskh, hr = users

        customers = [
            Customer(code="KH-001", name="Công ty CP Thực phẩm An Việt", tax_code="0101234567", phone="0901234567", email="mua.hang@anviet.vn", address="Hà Nội", segment="Sản xuất", owner_id=sales.id),
            Customer(code="KH-002", name="Nhà máy Dược phẩm Minh Tâm", tax_code="0109876543", phone="0912345678", email="qa@minhtam.vn", address="Bắc Ninh", segment="Dược phẩm", owner_id=sales.id),
            Customer(code="KH-003", name="Công ty Logistics Đông Dương", tax_code="0312345678", phone="0932123456", email="ops@dongduong.vn", address="Hải Phòng", segment="Logistics", owner_id=sales.id),
            Customer(code="KH-004", name="Siêu thị Hưng Phát", tax_code="0103456789", phone="0988123456", email="purchase@hungphat.vn", address="Hà Nội", segment="Bán lẻ", owner_id=sales.id),
        ]
        db.add_all(customers); db.flush()

        leads = [
            Lead(code="LD-2026-001", source="WEBSITE", company_name="Công ty TNHH Vật liệu Xây dựng Hòa Bình", contact_name="Anh Tuấn", phone="0977111222", email="tuan@hoabinh-vlxd.vn", need_summary="Quan tâm cân băng tải cho dây chuyền xi măng", potential_level="MEDIUM", owner_id=sales.id, status="NEW"),
            Lead(code="LD-2026-002", source="REFERRAL", company_name="Công ty CP Thức ăn chăn nuôi Việt Thắng", contact_name="Chị Hương", phone="0966222333", email="huong@vietthang.vn", need_summary="Cần thay thế cân định lượng cũ", potential_level="MEDIUM", owner_id=sales.id, status="CONTACTED"),
            Lead(code="LD-2026-003", source="FAIR", company_name="Công ty CP Bao bì Sông Hồng", contact_name="Ông Khải", phone="0955333444", email="khai@songhong-baobi.vn", need_summary="Đầu tư mới dây chuyền cân đóng bao tự động", potential_level="HIGH", owner_id=sales.id, status="QUALIFIED"),
        ]
        db.add_all(leads); db.flush()

        opps = [
            Opportunity(code="CH-2026-001", customer_id=customers[0].id, title="Hệ thống cân đóng gói 8 line", stage="PROPOSAL", expected_value=Decimal("1850000000"), probability=70, expected_close_date=date.today()+timedelta(days=18), owner_id=sales.id),
            Opportunity(code="CH-2026-002", customer_id=customers[1].id, title="Cân kiểm tra phòng sạch", stage="TECHNICAL_SURVEY", expected_value=Decimal("720000000"), probability=50, expected_close_date=date.today()+timedelta(days=35), owner_id=sales.id),
            Opportunity(code="CH-2026-003", customer_id=customers[2].id, title="Cân xe tải 100 tấn", stage="NEGOTIATION", expected_value=Decimal("980000000"), probability=80, expected_close_date=date.today()+timedelta(days=10), owner_id=sales.id),
            Opportunity(code="CH-2026-004", customer_id=customers[3].id, title="Nâng cấp 30 cân bàn", stage="LEAD", expected_value=Decimal("450000000"), probability=20, expected_close_date=date.today()+timedelta(days=60), owner_id=sales.id),
        ]
        db.add_all(opps); db.flush()

        customer5 = Customer(code="KH-LD-2026-003", name=leads[2].company_name, phone=leads[2].phone, email=leads[2].email, segment="Sản xuất", owner_id=sales.id)
        db.add(customer5); db.flush()
        opp5 = Opportunity(code="CH-2026-005", customer_id=customer5.id, title="Dây chuyền cân đóng bao tự động", stage="QUALIFICATION", expected_value=Decimal("610000000"), probability=25, expected_close_date=date.today()+timedelta(days=50), owner_id=sales.id, lead_id=leads[2].id)
        db.add(opp5); db.flush()
        leads[2].status = "CONVERTED"
        leads[2].converted_to_opportunity_id = opp5.id

        orders = [
            SalesOrder(code="DH-2026-041", customer_id=customers[0].id, opportunity_id=opps[0].id, title="Cung cấp cân định lượng và tích hợp PLC", status="IMPLEMENTING", total_amount=Decimal("1680000000"), cost_estimate=Decimal("1120000000"), payment_status="PARTIAL", due_date=date.today()+timedelta(days=25), created_by=sales.id),
            SalesOrder(code="DH-2026-037", customer_id=customers[2].id, opportunity_id=opps[2].id, title="Lắp đặt cân xe tải 80 tấn", status="CONFIRMED", total_amount=Decimal("830000000"), cost_estimate=Decimal("570000000"), payment_status="UNPAID", due_date=date.today()+timedelta(days=42), created_by=sales.id),
            SalesOrder(code="DH-2026-029", customer_id=customers[3].id, title="Bảo trì hệ thống cân bán lẻ", status="COMPLETED", total_amount=Decimal("320000000"), cost_estimate=Decimal("145000000"), payment_status="PARTIAL", due_date=date.today()-timedelta(days=15), created_by=sales.id),
        ]
        db.add_all(orders); db.flush()

        projects = [
            Project(code="DA-2026-011", name="Triển khai cân định lượng An Việt", customer_id=customers[0].id, order_id=orders[0].id, status="IN_PROGRESS", manager_id=technical.id, start_date=date.today()-timedelta(days=20), due_date=date.today()+timedelta(days=25), progress=62, budget_amount=Decimal("1120000000"), actual_cost=Decimal("685000000")),
            Project(code="DA-2026-012", name="Cân xe tải Đông Dương", customer_id=customers[2].id, order_id=orders[1].id, status="PLANNING", manager_id=technical.id, start_date=date.today()+timedelta(days=5), due_date=date.today()+timedelta(days=42), progress=18, budget_amount=Decimal("570000000"), actual_cost=Decimal("52000000")),
        ]
        db.add_all(projects); db.flush()

        work_orders = [
            WorkOrder(code="WO-2026-021", project_id=projects[0].id, title="Lắp đặt cân định lượng line 3", location="Nhà máy An Việt - Hà Nội", scheduled_date=date.today()-timedelta(days=10), technician_id=technical.id, materials_needed="Loadcell Zemic H8C x4, đầu cân CAS CI-2001A x1", checklist="Lắp đặt cơ khí; Đấu nối điện; Calibrate; Test tải", status="DONE", created_by=technical.id),
            WorkOrder(code="WO-2026-022", project_id=projects[1].id, title="Khảo sát và chuẩn bị lắp đặt cân xe tải", location="Đông Dương - Hải Phòng", scheduled_date=date.today()+timedelta(days=5), technician_id=technical.id, materials_needed="Bộ cân ô tô 100 tấn", checklist="Khảo sát nền móng; Chuẩn bị mặt bằng", status="PLANNED", created_by=technical.id),
        ]
        db.add_all(work_orders); db.flush()

        acceptance1 = AcceptanceRecord(code="NT-2026-011", work_order_id=work_orders[0].id, project_id=projects[0].id, summary="Đã lắp đặt và test tải đạt yêu cầu line 3", customer_signed_by="Ông Nguyễn Văn Bình", status="APPROVED", created_by=technical.id, approved_by=director.id)
        db.add(acceptance1); db.flush()
        db.add(ApprovalRequest(entity_type="ACCEPTANCE_RECORD", entity_id=acceptance1.id, requested_by=technical.id, approver_id=director.id, status="APPROVED", decision_note="Nghiệm thu đạt, đồng ý", decided_at=datetime.now(timezone.utc)-timedelta(days=1)))

        budgets = [
            Budget(code="NS-2026-KD", name="Ngân sách Kinh doanh 2026", department="Kinh doanh", period="2026", amount=Decimal("900000000"), spent_amount=Decimal("436000000"), status="APPROVED", owner_id=sales.id),
            Budget(code="NS-2026-KT", name="Ngân sách Kỹ thuật 2026", department="Kỹ thuật", period="2026", amount=Decimal("1500000000"), spent_amount=Decimal("812000000"), status="APPROVED", owner_id=technical.id),
            Budget(code="NS-2026-HC", name="Chi phí vận hành văn phòng", department="HCVP", period="2026", amount=Decimal("620000000"), spent_amount=Decimal("318000000"), status="APPROVED", owner_id=hr.id),
        ]
        db.add_all(budgets)
        expenses = [
            Expense(code="CP-00081", description="Mua loadcell dự phòng dự án An Việt", amount=Decimal("185000000"), category="Vật tư", department="Kỹ thuật", project_id=projects[0].id, status="APPROVED", expense_date=date.today()-timedelta(days=3), created_by=technical.id, approved_by=director.id),
            Expense(code="CP-00082", description="Chi phí vận chuyển thiết bị Bắc Ninh", amount=Decimal("28000000"), category="Vận chuyển", department="Kỹ thuật", project_id=projects[0].id, status="APPROVED", expense_date=date.today()-timedelta(days=2), created_by=technical.id, approved_by=director.id),
            Expense(code="CP-00083", description="Chi phí hội chợ công nghiệp", amount=Decimal("76000000"), category="Marketing", department="Kinh doanh", status="PENDING", expense_date=date.today(), created_by=sales.id),
            Expense(code="CP-00084", description="Văn phòng phẩm tháng 7", amount=Decimal("12500000"), category="Vận hành", department="HCVP", status="APPROVED", expense_date=date.today()-timedelta(days=5), created_by=hr.id, approved_by=director.id),
        ]
        db.add_all(expenses)

        products = [
            Product(sku="CAS-CI2001A", name="Đầu cân CAS CI-2001A", category="Đầu cân", unit="Cái", sale_price=Decimal("18500000"), cost_price=Decimal("12200000"), min_stock=5, quantity_on_hand=8),
            Product(sku="LC-ZEMIC-H8C-2T", name="Loadcell Zemic H8C 2 tấn", category="Loadcell", unit="Cái", sale_price=Decimal("7800000"), cost_price=Decimal("5100000"), min_stock=10, quantity_on_hand=7),
            Product(sku="SCALE-PRO-300KG", name="Cân bàn điện tử 300kg", category="Cân bàn", unit="Bộ", sale_price=Decimal("12500000"), cost_price=Decimal("7600000"), min_stock=6, quantity_on_hand=14),
            Product(sku="IND-WB-100T", name="Bộ cân ô tô 100 tấn", category="Cân ô tô", unit="Bộ", sale_price=Decimal("720000000"), cost_price=Decimal("480000000"), min_stock=1, quantity_on_hand=1),
            Product(sku="PRINTER-TMU220", name="Máy in phiếu Epson TM-U220", category="Phụ kiện", unit="Cái", sale_price=Decimal("6200000"), cost_price=Decimal("4100000"), min_stock=4, quantity_on_hand=3),
        ]
        db.add_all(products); db.flush()

        quotation1 = Quotation(code="BG-2026-001", opportunity_id=opps[2].id, customer_id=customers[2].id, status="APPROVED", created_by=sales.id, approved_by=director.id, payment_terms="30% tạm ứng, 40% khi lắp đặt, 30% khi nghiệm thu", warranty_terms="24 tháng", delivery_terms="45 ngày kể từ ngày đặt hàng")
        item1 = QuotationItem(product_id=products[3].id, name=products[3].name, quantity=1, unit_price=products[3].sale_price, discount_percent=Decimal("5"))
        quotation1.items = [item1]
        quotation1.total_amount = item1.quantity * item1.unit_price * (Decimal(1) - item1.discount_percent / Decimal(100))
        db.add(quotation1); db.flush()

        contract1 = Contract(code="HD-2026-001", quotation_id=quotation1.id, customer_id=customers[2].id, opportunity_id=opps[2].id, total_value=quotation1.total_amount, warranty_terms="24 tháng", status="ACTIVE", signed_by="Ông Trần Văn Long", created_by=sales.id, approved_by=director.id, sales_order_id=orders[1].id)
        contract1.payment_schedule = [
            ContractPaymentSchedule(description="Tạm ứng 30% khi ký hợp đồng", amount=contract1.total_value * Decimal("0.3"), invoiced=True),
            ContractPaymentSchedule(description="Thanh toán 40% khi lắp đặt", amount=contract1.total_value * Decimal("0.4"), invoiced=False),
            ContractPaymentSchedule(description="Thanh toán 30% khi nghiệm thu", amount=contract1.total_value * Decimal("0.3"), invoiced=False),
        ]
        db.add(contract1); db.flush()
        orders[1].contract_id = contract1.id

        quotation2 = Quotation(code="BG-2026-002", opportunity_id=opps[0].id, customer_id=customers[0].id, status="SUBMITTED", created_by=sales.id, payment_terms="50% tạm ứng, 50% khi giao hàng", warranty_terms="12 tháng", delivery_terms="30 ngày")
        item2 = QuotationItem(product_id=products[0].id, name=products[0].name, quantity=8, unit_price=products[0].sale_price, discount_percent=Decimal("3"))
        quotation2.items = [item2]
        quotation2.total_amount = item2.quantity * item2.unit_price * (Decimal(1) - item2.discount_percent / Decimal(100))
        db.add(quotation2); db.flush()

        approvals = [
            ApprovalRequest(entity_type="QUOTATION", entity_id=quotation1.id, requested_by=sales.id, approver_id=director.id, status="APPROVED", decision_note="Đồng ý chiết khấu 5%", decided_at=datetime.now(timezone.utc)-timedelta(days=4)),
            ApprovalRequest(entity_type="QUOTATION", entity_id=quotation2.id, requested_by=sales.id, approver_id=salesadmin.id, status="PENDING"),
        ]
        db.add_all(approvals)

        suppliers = [
            Supplier(code="NCC-001", name="Công ty TNHH Thiết bị Công nghiệp Toàn Cầu", tax_code="0100112233", phone="0243999888", email="sales@toancau-equip.vn", address="Hà Nội", contact_person="Ông Phạm Đức Long"),
            Supplier(code="NCC-002", name="Công ty CP Cân điện tử Việt Đức", tax_code="0201122334", phone="0225888777", email="contact@vietduc-scale.vn", address="Hải Phòng", contact_person="Bà Lê Thị Ngọc"),
        ]
        db.add_all(suppliers); db.flush()

        purchase_request1 = PurchaseRequest(code="YCM-2026-005", department="Kho", project_id=projects[1].id, product_id=products[3].id, quantity=1, reason="Bổ sung hàng cho dự án Đông Dương", status="APPROVED", created_by=warehouse.id, approved_by=director.id)
        db.add(purchase_request1); db.flush()

        purchase_order1 = PurchaseOrder(code="PO-2026-014", supplier_id=suppliers[0].id, purchase_request_id=purchase_request1.id, expected_delivery_date=date.today()+timedelta(days=20), status="RECEIVED", created_by=warehouse.id)
        po_item1 = PurchaseOrderItem(product_id=products[3].id, quantity=1, unit_price=products[3].cost_price)
        purchase_order1.items = [po_item1]
        purchase_order1.total_amount = po_item1.quantity * po_item1.unit_price
        db.add(purchase_order1); db.flush()
        products[3].quantity_on_hand += po_item1.quantity
        db.add(StockMovement(product_id=products[3].id, movement_type="IN", quantity=po_item1.quantity, reference=purchase_order1.code, note=f"Nhập kho từ PO {purchase_order1.code}", created_by=warehouse.id))

        purchase_request2 = PurchaseRequest(code="YCM-2026-006", department="Kỹ thuật", product_id=products[1].id, quantity=20, reason="Bổ sung loadcell dự phòng cho các dự án đang triển khai", status="DRAFT", created_by=technical.id)
        db.add(purchase_request2)

        reservation1 = StockReservation(product_id=products[3].id, sales_order_id=orders[1].id, quantity=1, status="RESERVED", created_by=warehouse.id)
        db.add(reservation1); db.flush()
        products[3].reserved_quantity += reservation1.quantity

        receivables = [
            Receivable(customer_id=customers[0].id, order_id=orders[0].id, invoice_no="HD-000041", amount=Decimal("840000000"), paid_amount=Decimal("500000000"), due_date=date.today()+timedelta(days=12), status="PARTIAL"),
            Receivable(customer_id=customers[2].id, order_id=orders[1].id, invoice_no="HD-000037", amount=Decimal("249000000"), paid_amount=Decimal("0"), due_date=date.today()+timedelta(days=8), status="OPEN"),
            Receivable(customer_id=customers[3].id, order_id=orders[2].id, invoice_no="HD-000029", amount=Decimal("320000000"), paid_amount=Decimal("220000000"), due_date=date.today()-timedelta(days=15), status="OVERDUE"),
        ]
        db.add_all(receivables)

        tickets = [
            SupportTicket(code="CS-2026-071", customer_id=customers[0].id, project_id=projects[0].id, subject="Cân line 3 hiển thị dao động", priority="HIGH", status="IN_PROGRESS", assigned_to=technical.id, sla_due_at=datetime.now(timezone.utc)+timedelta(hours=3)),
            SupportTicket(code="CS-2026-072", customer_id=customers[3].id, subject="Yêu cầu lịch bảo trì định kỳ", priority="LOW", status="OPEN", assigned_to=cskh.id, sla_due_at=datetime.now(timezone.utc)+timedelta(hours=36)),
        ]
        db.add_all(tickets)

        tasks = [
            Task(code="CV-2026-101", title="Chuẩn bị hồ sơ khảo sát kỹ thuật Đông Dương", department="Kỹ thuật", assigned_to=technical.id, assigned_by=techsolution.id, priority="HIGH", due_date=date.today()+timedelta(days=3), status="IN_PROGRESS"),
            Task(code="CV-2026-102", title="Tổng hợp báo giá đối thủ cho cơ hội CH-2026-004", department="Kinh doanh", assigned_to=sales.id, assigned_by=salesadmin.id, priority="MEDIUM", due_date=date.today()+timedelta(days=5), status="NEW"),
            Task(code="CV-2026-103", title="Rà soát công nợ quá hạn tháng 6", department="Kế toán", assigned_to=accounting.id, assigned_by=director.id, priority="HIGH", due_date=date.today()-timedelta(days=1), status="DONE_PENDING_REVIEW", progress_note="Đã rà soát 3 khách hàng quá hạn, chờ xác nhận"),
            Task(code="CV-2026-104", title="Kiểm kê kho vật tư loadcell", department="Kho", assigned_to=warehouse.id, assigned_by=director.id, priority="LOW", due_date=date.today()-timedelta(days=10), status="CONFIRMED", progress_note="Đã kiểm kê xong, số liệu khớp hệ thống", confirmed_by=director.id, confirmed_at=datetime.now(timezone.utc)-timedelta(days=8)),
        ]
        db.add_all(tasks)
        db.commit()
        print("Seeded PRO Enterprise Hub demo data")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

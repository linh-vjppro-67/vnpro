"""Nạp thêm dữ liệu trình diễn, không xóa và không ghi đè dữ liệu người dùng.

Chạy nhiều lần an toàn: python -m app.seed_mockup
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import (
    ApprovalRule, Budget, CollectionActivity, Customer, Expense, GoodsReceipt,
    GoodsReceiptLine, Lead, Notification, Opportunity, Product, Project,
    PurchaseOrder, PurchaseOrderItem, PurchaseRequest, Quotation, QuotationItem,
    Receivable, SalesOrder, SalesOrderItem, SolutionBOM, SolutionBOMItem,
    Supplier, SupportTicket, Task, TechnicalRequest, TechnicalSurvey, TicketEvent,
    User, WarrantyProfile, WorkOrder,
)


def one(db, model, field, value):
    return db.scalar(select(model).where(getattr(model, field) == value))


def add_unique(db, model, field, value, **values):
    row = one(db, model, field, value)
    if row:
        return row, False
    row = model(**{field: value}, **values)
    db.add(row)
    db.flush()
    return row, True


def seed_mockup():
    db = SessionLocal()
    added: dict[str, int] = {}

    def track(model, created):
        if created:
            key = model.__tablename__
            added[key] = added.get(key, 0) + 1

    try:
        today = date.today()
        now = datetime.now(timezone.utc)
        sales = one(db, User, "email", "sales@vnpro.vn")
        director = one(db, User, "email", "director@vnpro.vn")
        accounting = one(db, User, "email", "accounting@vnpro.vn")
        warehouse = one(db, User, "email", "warehouse@vnpro.vn")
        technical = one(db, User, "email", "technical@vnpro.vn")
        tech_solution = one(db, User, "email", "techsolution@vnpro.vn")
        cskh = one(db, User, "email", "cskh@vnpro.vn")
        if not all([sales, director, accounting, warehouse, technical, tech_solution, cskh]):
            raise RuntimeError("Hãy chạy `python -m app.seed` trước để tạo tài khoản nền.")

        customer_data = [
            ("KH-DEMO-01", "Công ty CP Thép Thành Công", "Sản xuất", "Hải Dương"),
            ("KH-DEMO-02", "Nhà máy Xi măng Đại Việt", "Vật liệu xây dựng", "Ninh Bình"),
            ("KH-DEMO-03", "Công ty TNHH Nông sản Bình Minh", "Nông sản", "Hưng Yên"),
            ("KH-DEMO-04", "Công ty Logistics Bắc Nam", "Logistics", "Hải Phòng"),
            ("KH-DEMO-05", "Nhà máy Dược phẩm An Khang", "Dược phẩm", "Bắc Ninh"),
            ("KH-DEMO-06", "Công ty Bao bì Tân Phú", "Bao bì", "Hà Nam"),
        ]
        customers = []
        for i, (code, name, segment, address) in enumerate(customer_data, 1):
            row, created = add_unique(
                db, Customer, "code", code, name=name, segment=segment, address=address,
                tax_code=f"01090000{i:02d}", phone=f"09090000{i:02d}",
                email=f"muahang{i}@khachhang-demo.vn", owner_id=sales.id,
            )
            customers.append(row); track(Customer, created)

        product_data = [
            ("VNPRO-IND-01", "Đầu cân điện tử công nghiệp VNPRO I200", "Đầu cân", "Cái", 18_500_000, 12_200_000, 12, 4, "A-01"),
            ("VNPRO-LC-02", "Loadcell hợp kim 2 tấn", "Loadcell", "Cái", 7_800_000, 5_100_000, 36, 10, "A-02"),
            ("VNPRO-WB-80T", "Bộ cân ô tô 80 tấn", "Cân ô tô", "Bộ", 680_000_000, 455_000_000, 2, 1, "B-01"),
            ("VNPRO-BELT-01", "Bộ cân băng tải định lượng", "Cân băng tải", "Bộ", 325_000_000, 218_000_000, 1, 1, "B-02"),
            ("VNPRO-PRN-01", "Máy in phiếu cân nhiệt", "Phụ kiện", "Cái", 6_200_000, 4_100_000, 9, 3, "C-01"),
            ("VNPRO-JBOX-04", "Hộp nối 4 loadcell chống nước", "Phụ kiện", "Cái", 3_600_000, 2_150_000, 18, 5, "C-02"),
            ("VNPRO-SCALE-300", "Cân bàn điện tử 300 kg", "Cân bàn", "Bộ", 12_500_000, 7_600_000, 20, 6, "D-01"),
            ("VNPRO-SERVICE-CAL", "Dịch vụ hiệu chuẩn tại hiện trường", "Dịch vụ", "Lần", 8_000_000, 3_500_000, 0, 0, "DV"),
        ]
        products = []
        for sku, name, category, unit, sale, cost, stock, minimum, location in product_data:
            row, created = add_unique(
                db, Product, "sku", sku, name=name, category=category, unit=unit,
                sale_price=Decimal(sale), cost_price=Decimal(cost), quantity_on_hand=stock,
                min_stock=minimum, reserved_quantity=0, quarantine_quantity=0,
                warehouse_location=location, is_active=True,
            )
            products.append(row); track(Product, created)

        lead_data = [
            ("LD-DEMO-01", "Công ty Gạch men Á Châu", "Chị Ngọc", "WEBSITE", "Cân băng tải cấp liệu", "NEW"),
            ("LD-DEMO-02", "Nhà máy Thức ăn Chăn nuôi Hòa Phát", "Anh Dũng", "REFERRAL", "Nâng cấp cân đóng bao", "CONTACTED"),
            ("LD-DEMO-03", "Công ty Khoáng sản Đông Bắc", "Anh Hải", "FAIR", "Cân ô tô 100 tấn", "QUALIFIED"),
            ("LD-DEMO-04", "Hợp tác xã Nông nghiệp Phú Xuyên", "Chị Lan", "TELESALES", "Cân sàn kho nông sản", "NOT_QUALIFIED"),
        ]
        for code, company, contact, source, need, status in lead_data:
            row, created = add_unique(
                db, Lead, "code", code, company_name=company, contact_name=contact,
                source=source, need_summary=need, potential_level="HIGH" if status == "QUALIFIED" else "MEDIUM",
                owner_id=sales.id, phone="0901234567", status=status,
            )
            track(Lead, created)

        opportunity_data = [
            ("CH-DEMO-01", 0, "Hệ thống cân xe tải nhà máy thép", "TECHNICAL_SURVEY", 1_250_000_000, 55),
            ("CH-DEMO-02", 1, "Cân băng tải cấp liệu clinker", "PROPOSAL", 780_000_000, 70),
            ("CH-DEMO-03", 2, "Dây chuyền cân đóng gói nông sản", "NEGOTIATION", 465_000_000, 80),
            ("CH-DEMO-04", 4, "Cân kiểm tra phòng sạch", "QUALIFICATION", 320_000_000, 35),
            ("CH-DEMO-05", 5, "Nâng cấp cân đóng bao tự động", "LOST", 540_000_000, 0),
        ]
        opportunities = []
        for code, customer_idx, title, stage, value, probability in opportunity_data:
            row, created = add_unique(
                db, Opportunity, "code", code, customer_id=customers[customer_idx].id,
                title=title, stage=stage, expected_value=Decimal(value), probability=probability,
                expected_close_date=today + timedelta(days=20 + customer_idx * 8), owner_id=sales.id,
            )
            opportunities.append(row); track(Opportunity, created)

        survey, created = add_unique(
            db, TechnicalSurvey, "code", "KS-DEMO-01", opportunity_id=opportunities[0].id,
            location="Nhà máy thép Thành Công, Hải Dương", requirements="Cân xe tải 80 tấn, kết nối ERP và camera",
            current_state="Đã có móng cân cũ, cần cải tạo", recommendation="Thay loadcell, đầu cân và tủ điều khiển",
            survey_date=today - timedelta(days=4), engineer_id=tech_solution.id, status="COMPLETED", created_by=sales.id,
        )
        track(TechnicalSurvey, created)
        bom, created = add_unique(
            db, SolutionBOM, "code", "BOM-DEMO-01", opportunity_id=opportunities[0].id,
            survey_id=survey.id, name="BOM cân xe tải 80 tấn", scope="Thiết bị, lắp đặt và tích hợp dữ liệu",
            status="APPROVED", created_by=tech_solution.id,
        )
        if created:
            bom.items = [
                SolutionBOMItem(product_id=products[2].id, name=products[2].name, quantity=1, unit="Bộ", estimated_cost=products[2].cost_price),
                SolutionBOMItem(product_id=products[4].id, name=products[4].name, quantity=1, unit="Cái", estimated_cost=products[4].cost_price),
            ]
        track(SolutionBOM, created)

        tech_request_data = [
            ("YC-KT-DEMO-01", opportunities[0], "SURVEY", "Khảo sát móng cân và đường truyền", "ASSIGNED", technical.id, 6),
            ("YC-KT-DEMO-02", opportunities[1], "SOLUTION", "Lập phương án và BOM cân băng tải", "IN_PROGRESS", tech_solution.id, 18),
            ("YC-KT-DEMO-03", opportunities[3], "CONSULTING", "Tư vấn tiêu chuẩn phòng sạch", "NEED_INFO", tech_solution.id, 30),
        ]
        for code, opp, kind, scope, status, assignee, hours in tech_request_data:
            row, created = add_unique(
                db, TechnicalRequest, "code", code, opportunity_id=opp.id, request_type=kind,
                scope=scope, site_address=opp.customer.address, priority="HIGH" if hours < 10 else "MEDIUM",
                sla_due_at=now + timedelta(hours=hours), assignee_id=assignee, status=status, created_by=sales.id,
            )
            track(TechnicalRequest, created)

        quotation_data = [
            ("BG-DEMO-01", opportunities[1], customers[1], "DRAFT", products[3], 2, 325_000_000, 218_000_000),
            ("BG-DEMO-02", opportunities[2], customers[2], "SUBMITTED", products[6], 20, 12_500_000, 7_600_000),
            ("BG-DEMO-03", opportunities[0], customers[0], "APPROVED", products[2], 1, 680_000_000, 455_000_000),
        ]
        for code, opp, customer, status, product, qty, price, cost in quotation_data:
            total = Decimal(qty * price) * Decimal("1.08")
            estimate = Decimal(qty * cost)
            row, created = add_unique(
                db, Quotation, "code", code, opportunity_id=opp.id, customer_id=customer.id,
                total_amount=total, estimated_cost=estimate,
                margin_percent=(total-estimate)/total*100, valid_until=today+timedelta(days=30),
                currency="VND", payment_terms="40% tạm ứng, 50% khi giao, 10% sau nghiệm thu",
                warranty_terms="Bảo hành 24 tháng", delivery_terms="30-45 ngày", status=status,
                created_by=sales.id, approved_by=director.id if status == "APPROVED" else None,
            )
            if created:
                row.items = [QuotationItem(
                    product_id=product.id, name=product.name, quantity=qty, unit=product.unit,
                    unit_price=Decimal(price), estimated_cost=Decimal(cost), discount_percent=0, tax_rate=8,
                )]
            track(Quotation, created)

        order_data = [
            ("DH-DEMO-01", customers[0], opportunities[0], "DRAFT", products[2], 1, 680_000_000),
            ("DH-DEMO-02", customers[1], opportunities[1], "WAITING_INVENTORY", products[3], 2, 325_000_000),
            ("DH-DEMO-03", customers[2], opportunities[2], "IN_IMPLEMENTATION", products[6], 12, 12_500_000),
            ("DH-DEMO-04", customers[3], None, "CLOSED", products[0], 2, 18_500_000),
        ]
        orders = []
        for code, customer, opp, status, product, qty, price in order_data:
            row, created = add_unique(
                db, SalesOrder, "code", code, customer_id=customer.id,
                opportunity_id=opp.id if opp else None, title=f"Đơn hàng mẫu - {product.name}",
                status=status, total_amount=Decimal(qty * price), cost_estimate=Decimal(qty) * product.cost_price,
                payment_status="PAID" if status == "CLOSED" else "UNPAID",
                due_date=today+timedelta(days=35), created_by=sales.id,
            )
            if created:
                db.add(SalesOrderItem(
                    sales_order_id=row.id, product_id=product.id, name=product.name,
                    quantity=qty, unit_price=Decimal(price), fulfilled_quantity=qty if status in ["IN_IMPLEMENTATION", "CLOSED"] else 0,
                ))
            orders.append(row); track(SalesOrder, created)

        project, created = add_unique(
            db, Project, "code", "DA-DEMO-01", name="Triển khai cân đóng gói Bình Minh",
            customer_id=customers[2].id, order_id=orders[2].id, status="IN_PROGRESS",
            manager_id=technical.id, start_date=today-timedelta(days=8), due_date=today+timedelta(days=25),
            progress=45, budget_amount=Decimal("100000000"), actual_cost=Decimal("38000000"),
        )
        track(Project, created)
        for code, title, status, offset in [
            ("WO-DEMO-01", "Lắp đặt cơ khí và đấu nối", "IN_PROGRESS", 1),
            ("WO-DEMO-02", "Hiệu chuẩn và chạy thử", "PLANNED", 5),
        ]:
            row, created = add_unique(
                db, WorkOrder, "code", code, project_id=project.id, title=title,
                location="Kho Bình Minh, Hưng Yên", scheduled_date=today+timedelta(days=offset),
                technician_id=technical.id, materials_needed="Thiết bị theo BOM", checklist="An toàn; Lắp đặt; Đấu nối; Test tải",
                status=status, created_by=technical.id,
            )
            track(WorkOrder, created)

        supplier, created = add_unique(
            db, Supplier, "code", "NCC-DEMO-01", name="Công ty Thiết bị Đo lường Đông Á",
            tax_code="0109555888", phone="02439990000", email="sales@donga-demo.vn",
            address="Hà Nội", contact_person="Anh Quang",
        )
        track(Supplier, created)
        pr, created = add_unique(
            db, PurchaseRequest, "code", "YCM-DEMO-01", department="Kho", project_id=project.id,
            product_id=products[1].id, quantity=20, reason="Bổ sung loadcell cho đơn DH-DEMO-02",
            status="APPROVED", created_by=warehouse.id, approved_by=director.id,
        )
        track(PurchaseRequest, created)
        po, created = add_unique(
            db, PurchaseOrder, "code", "PO-DEMO-01", supplier_id=supplier.id, purchase_request_id=pr.id,
            total_amount=Decimal("102000000"), expected_delivery_date=today+timedelta(days=3),
            status="ORDERED", created_by=warehouse.id,
        )
        if created:
            po.items = [PurchaseOrderItem(product_id=products[1].id, quantity=20, unit_price=Decimal("5100000"))]
        track(PurchaseOrder, created)
        receipt, created = add_unique(
            db, GoodsReceipt, "code", "GR-DEMO-01", purchase_order_id=po.id, supplier_id=supplier.id,
            received_date=today, delivery_note="PGH-DEMO-001",
            document_checklist=json.dumps({"purchase_order": True, "delivery_note": True, "quality_record": True}),
            status="INSPECTED", created_by=warehouse.id,
        )
        if created:
            receipt.lines = [GoodsReceiptLine(
                product_id=products[1].id, received_quantity=20, accepted_quantity=18,
                quarantine_quantity=2, rejected_quantity=0, quality_note="18 đạt, 2 chờ kiểm tra độ lệch tín hiệu",
            )]
        track(GoodsReceipt, created)

        budget_data = [
            ("NS-DEMO-KD", "Ngân sách Kinh doanh quý hiện tại", "Kinh doanh", 600_000_000, 210_000_000, 75_000_000),
            ("NS-DEMO-KT", "Ngân sách Kỹ thuật quý hiện tại", "Kỹ thuật", 900_000_000, 425_000_000, 130_000_000),
            ("NS-DEMO-KHO", "Ngân sách Kho vận quý hiện tại", "Kho", 500_000_000, 180_000_000, 102_000_000),
        ]
        budgets = []
        for code, name, department, amount, spent, committed in budget_data:
            row, created = add_unique(
                db, Budget, "code", code, name=name, department=department,
                period=f"Q{(today.month-1)//3+1}/{today.year}", amount=Decimal(amount),
                spent_amount=Decimal(spent), committed_amount=Decimal(committed),
                status="APPROVED", owner_id=director.id,
            )
            budgets.append(row); track(Budget, created)
        for code, desc, amount, department, category, status, budget in [
            ("CP-DEMO-01", "Chi phí khảo sát nhà máy Hải Dương", 8_500_000, "Kỹ thuật", "Công tác", "DRAFT", budgets[1]),
            ("CP-DEMO-02", "Thuê xe vận chuyển thiết bị", 18_000_000, "Kho", "Vận chuyển", "SUBMITTED", budgets[2]),
            ("CP-DEMO-03", "Mua vật tư phụ lắp đặt", 32_000_000, "Kỹ thuật", "Vật tư", "APPROVED", budgets[1]),
            ("CP-DEMO-04", "Chi phí hội chợ thiết bị công nghiệp", 45_000_000, "Kinh doanh", "Marketing", "OVER_BUDGET", budgets[0]),
        ]:
            row, created = add_unique(
                db, Expense, "code", code, description=desc, amount=Decimal(amount),
                category=category, department=department, status=status, expense_date=today,
                budget_id=budget.id, created_by=sales.id if department == "Kinh doanh" else technical.id,
                approved_by=director.id if status == "APPROVED" else None,
            )
            track(Expense, created)

        receivable_data = [
            ("HĐ-DEMO-001", customers[0], orders[0], 680_000_000, 272_000_000, today+timedelta(days=10), "PARTIAL"),
            ("HĐ-DEMO-002", customers[2], orders[2], 150_000_000, 0, today-timedelta(days=7), "OVERDUE"),
            ("HĐ-DEMO-003", customers[3], orders[3], 37_000_000, 37_000_000, today-timedelta(days=2), "PAID"),
        ]
        receivables = []
        for invoice, customer, order, amount, paid, due, status in receivable_data:
            row, created = add_unique(
                db, Receivable, "invoice_no", invoice, customer_id=customer.id, order_id=order.id,
                amount=Decimal(amount), paid_amount=Decimal(paid), due_date=due, status=status,
            )
            receivables.append(row); track(Receivable, created)
        if not db.scalar(select(CollectionActivity.id).where(CollectionActivity.receivable_id == receivables[1].id)):
            db.add(CollectionActivity(
                receivable_id=receivables[1].id, activity_date=now-timedelta(days=1),
                channel="Điện thoại", result="Kế toán khách hàng hẹn thanh toán sau khi đối chiếu biên bản",
                promised_date=today+timedelta(days=5), promised_amount=Decimal("150000000"),
                next_follow_up=today+timedelta(days=3), created_by=accounting.id,
            ))
            added["collection_activities"] = added.get("collection_activities", 0) + 1

        warranty, created = add_unique(
            db, WarrantyProfile, "code", "BH-DEMO-01", customer_id=customers[3].id,
            sales_order_id=orders[3].id, product_id=products[0].id, serial_no="VNPRO-I200-260701",
            start_date=today-timedelta(days=60), end_date=today+timedelta(days=670),
            coverage="Bảo hành lỗi thiết bị, linh kiện và công lắp đặt",
            exclusions="Không áp dụng hư hỏng do nguồn điện hoặc tác động cơ học", status="ACTIVE",
        )
        track(WarrantyProfile, created)
        ticket_data = [
            ("CS-DEMO-01", customers[3], orders[3], "Đầu cân hiển thị không ổn định", "HIGH", "IN_PROGRESS", "IN_WARRANTY"),
            ("CS-DEMO-02", customers[0], orders[0], "Yêu cầu hướng dẫn xuất báo cáo", "MEDIUM", "OPEN", "NOT_CHECKED"),
            ("CS-DEMO-03", customers[2], orders[2], "Đặt lịch bảo trì định kỳ", "LOW", "RESOLVED", "OUT_OF_WARRANTY"),
        ]
        for code, customer, order, subject, priority, status, warranty_status in ticket_data:
            row, created = add_unique(
                db, SupportTicket, "code", code, customer_id=customer.id, sales_order_id=order.id,
                subject=subject, description=f"Dữ liệu mẫu: {subject}", priority=priority, status=status,
                assigned_to=cskh.id, sla_due_at=now+timedelta(hours={"HIGH": 4, "MEDIUM": 24, "LOW": 48}[priority]),
                first_response_at=now-timedelta(hours=1) if status != "OPEN" else None,
                resolved_at=now if status == "RESOLVED" else None,
                resolution="Đã thống nhất lịch xử lý với khách hàng" if status == "RESOLVED" else None,
                warranty_status=warranty_status,
            )
            if created:
                db.add(TicketEvent(ticket_id=row.id, action="CREATE", note="Ticket dữ liệu trình diễn", actor_id=cskh.id))
            track(SupportTicket, created)

        for code, title, department, assignee, priority, status, offset in [
            ("CV-DEMO-01", "Hoàn thiện BOM cơ hội CH-DEMO-01", "Kỹ thuật", tech_solution, "HIGH", "IN_PROGRESS", 2),
            ("CV-DEMO-02", "Gọi lại khách hàng lead LD-DEMO-02", "Kinh doanh", sales, "MEDIUM", "NEW", 1),
            ("CV-DEMO-03", "Đối chiếu công nợ HĐ-DEMO-002", "Kế toán", accounting, "HIGH", "DONE_PENDING_REVIEW", -1),
            ("CV-DEMO-04", "Kiểm tra 2 loadcell đang quarantine", "Kho", warehouse, "HIGH", "NEW", 1),
        ]:
            row, created = add_unique(
                db, Task, "code", code, title=title, department=department,
                assigned_to=assignee.id, assigned_by=director.id, priority=priority,
                due_date=today+timedelta(days=offset), status=status,
                progress_note="Đã cập nhật dữ liệu mẫu" if status == "DONE_PENDING_REVIEW" else None,
            )
            track(Task, created)

        rules = [
            ("QUOTATION", "Báo giá đến 500 triệu", Decimal("500000000"), "SALES_ADMIN", 1),
            ("QUOTATION", "Báo giá trên 500 triệu", None, "DIRECTOR", 2),
            ("EXPENSE", "Chi vượt ngân sách", None, "DIRECTOR", 1),
            ("PURCHASE_REQUEST", "Yêu cầu mua hàng", None, "DIRECTOR", 1),
        ]
        for document_type, name, max_amount, role, step in rules:
            exists = db.scalar(select(ApprovalRule.id).where(ApprovalRule.document_type == document_type, ApprovalRule.name == name))
            if not exists:
                db.add(ApprovalRule(
                    document_type=document_type, name=name, max_amount=max_amount,
                    over_budget=True if name == "Chi vượt ngân sách" else None,
                    approver_role=role, step_no=step, sla_hours=24, is_active=True,
                ))
                added["approval_rules"] = added.get("approval_rules", 0) + 1

        notification_data = [
            ("TECH_SOLUTION", "Yêu cầu khảo sát mới", "YC-KT-DEMO-01 cần tiếp nhận khảo sát tại Hải Dương", "TECHNICAL_REQUEST"),
            ("WAREHOUSE", "PO sắp giao hàng", "PO-DEMO-01 dự kiến giao trong 3 ngày", "PURCHASE_ORDER"),
            ("ACCOUNTING", "Công nợ quá hạn", "HĐ-DEMO-002 đã quá hạn 7 ngày", "RECEIVABLE"),
            ("CUSTOMER_SERVICE", "Ticket SLA cao", "CS-DEMO-01 cần phản hồi trong 4 giờ", "SUPPORT_TICKET"),
        ]
        for role, title, message, entity_type in notification_data:
            exists = db.scalar(select(Notification.id).where(Notification.role == role, Notification.title == title))
            if not exists:
                db.add(Notification(role=role, title=title, message=message, entity_type=entity_type, is_read=False))
                added["notifications"] = added.get("notifications", 0) + 1

        db.commit()
        totals = {
            "customers": db.scalar(select(func.count(Customer.id))),
            "leads": db.scalar(select(func.count(Lead.id))),
            "opportunities": db.scalar(select(func.count(Opportunity.id))),
            "products": db.scalar(select(func.count(Product.id))),
            "orders": db.scalar(select(func.count(SalesOrder.id))),
            "projects": db.scalar(select(func.count(Project.id))),
            "expenses": db.scalar(select(func.count(Expense.id))),
            "tickets": db.scalar(select(func.count(SupportTicket.id))),
        }
        print("Đã thêm:", added)
        print("Tổng dữ liệu:", totals)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_mockup()

import os
import tempfile
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

test_db = Path(tempfile.gettempdir()) / f"vnpro_test_{os.getpid()}.db"
test_db.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
os.environ["SECRET_KEY"] = "test-secret-key"

from alembic.config import Config
from alembic import command
alembic_config = Config("alembic.ini")
command.upgrade(alembic_config, "head")

from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.core.security import get_password_hash

with SessionLocal() as db:
    db.add_all([
        User(email="admin@test.vn", full_name="Admin", role="SYSTEM_ADMIN", department="IT", hashed_password=get_password_hash("Demo@123")),
        User(email="director@test.vn", full_name="Director", role="DIRECTOR", department="BGĐ", hashed_password=get_password_hash("Demo@123")),
        User(email="accounting@test.vn", full_name="Accounting", role="ACCOUNTING", department="Kế toán", hashed_password=get_password_hash("Demo@123")),
        User(email="warehouse@test.vn", full_name="Warehouse", role="WAREHOUSE", department="Kho", hashed_password=get_password_hash("Demo@123")),
    ])
    db.commit()

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me():
    login = client.post("/auth/login", json={"email": "admin@test.vn", "password": "Demo@123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "SYSTEM_ADMIN"


def test_login_preflight_allows_local_dev_origin():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def auth_headers(email="admin@test.vn"):
    token = client.post("/auth/login", json={"email": email, "password": "Demo@123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_vnpro_order_inventory_flow():
    from app.models import Customer, Product, SalesOrder
    with SessionLocal() as db:
        customer = Customer(code="KH-FLOW", name="Khách hàng Flow", segment="Sản xuất")
        product = Product(sku="SKU-FLOW", name="Bộ cân Flow", category="Cân", unit="Bộ", quantity_on_hand=3, reserved_quantity=0)
        db.add_all([customer, product]); db.flush()
        order = SalesOrder(code="SO-FLOW", customer_id=customer.id, title="Đơn hàng kiểm thử flow", status="DRAFT", total_amount=1000, cost_estimate=600)
        db.add(order); db.commit()
        order_id, product_id = order.id, product.id
    headers = auth_headers()
    assert client.post(f"/order-flow/orders/{order_id}/items", headers=headers, json={
        "product_id": product_id, "quantity": 2, "unit_price": 500,
    }).status_code == 201
    assert client.post(f"/order-flow/orders/{order_id}/confirm", headers=headers).json()["status"] == "WAITING_INVENTORY"
    reserved = client.post(f"/order-flow/orders/{order_id}/reserve", headers=headers)
    assert reserved.status_code == 200
    assert reserved.json()["order"]["status"] == "READY_FOR_DELIVERY"
    issued = client.post(f"/order-flow/orders/{order_id}/issue", headers=headers)
    assert issued.status_code == 200
    assert issued.json()["status"] == "IN_IMPLEMENTATION"
    workspace = client.get(f"/order-flow/orders/{order_id}/workspace", headers=headers).json()
    assert workspace["inventory"][0]["stock_on_hand"] == 1
    assert workspace["inventory"][0]["reserved_for_order"] == 0
    assert client.post(f"/order-flow/orders/{order_id}/invoice", headers=headers, json={
        "invoice_no": "INV-TOO-EARLY", "due_date": "2026-08-30", "amount_before_vat": 1000,
    }).status_code == 409


def test_budget_expense_payment_flow():
    from app.models import Budget
    with SessionLocal() as db:
        db.add(Budget(code="BUD-FLOW", name="Ngân sách test", department="Kỹ thuật", period="2026", amount=1000, spent_amount=0, status="APPROVED"))
        db.commit()
    headers = auth_headers()
    created = client.post("/costs/expenses", headers=headers, json={
        "code": "EXP-FLOW", "description": "Chi phí test", "amount": 400,
        "category": "Vật tư", "department": "Kỹ thuật", "expense_date": "2026-07-24",
    })
    assert created.status_code == 201
    expense_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"
    assert client.post(f"/costs/expenses/{expense_id}/submit", headers=headers).json()["status"] == "SUBMITTED"
    assert client.post(f"/costs/expenses/{expense_id}/approve", headers=auth_headers("director@test.vn"), json={}).json()["status"] == "APPROVED"
    with SessionLocal() as db:
        budget = db.query(Budget).filter(Budget.code == "BUD-FLOW").one()
        assert budget.committed_amount == 400
    paid = client.post(f"/costs/expenses/{expense_id}/pay", headers=auth_headers("accounting@test.vn"), json={
        "paid_date": "2026-07-24", "amount": 400, "method": "BANK_TRANSFER", "transaction_ref": "UNC-TEST",
    })
    assert paid.status_code == 200
    assert paid.json()["status"] == "PAID"
    assert client.post(f"/costs/expenses/{expense_id}/reject", headers=auth_headers("director@test.vn"), json={}).status_code == 409
    with SessionLocal() as db:
        budget = db.query(Budget).filter(Budget.code == "BUD-FLOW").one()
        assert budget.committed_amount == 0
        assert budget.spent_amount == 400


def test_technical_request_state_machine():
    from app.models import Customer, Opportunity
    with SessionLocal() as db:
        customer = Customer(code="KH-TECH", name="Khách hàng kỹ thuật", segment="Dự án")
        db.add(customer); db.flush()
        opportunity = Opportunity(code="OPP-TECH", customer_id=customer.id, title="Khảo sát trạm cân", stage="QUALIFIED", expected_value=1000)
        db.add(opportunity); db.commit()
        opportunity_id = opportunity.id
    headers = auth_headers()
    created = client.post("/production/technical-requests", headers=headers, json={
        "code": "TR-TECH", "opportunity_id": opportunity_id, "request_type": "SURVEY",
        "scope": "Khảo sát hiện trạng và lập BOM", "priority": "HIGH", "sla_hours": 4,
    })
    assert created.status_code == 201
    request_id = created.json()["id"]
    assert created.json()["status"] == "NEW"
    assert client.post(f"/production/technical-requests/{request_id}/action", headers=headers, json={
        "action": "ASSIGN", "assignee_id": 1,
    }).json()["status"] == "ASSIGNED"
    assert client.post(f"/production/technical-requests/{request_id}/action", headers=headers, json={"action": "ACCEPT"}).json()["status"] == "IN_PROGRESS"
    assert client.post(f"/production/technical-requests/{request_id}/action", headers=headers, json={"action": "COMPLETE"}).status_code == 422
    assert client.post(f"/production/technical-requests/{request_id}/action", headers=headers, json={
        "action": "COMPLETE", "note": "Đã khảo sát và chốt BOM",
    }).json()["status"] == "COMPLETED"


def test_quotation_margin_tax_and_version_clone():
    from app.models import Customer, Opportunity, Product
    with SessionLocal() as db:
        customer = Customer(code="KH-BG", name="Khách hàng báo giá", segment="Dự án")
        product = Product(sku="SKU-BG", name="Đầu cân báo giá", category="Đầu cân", unit="Cái", quantity_on_hand=1)
        db.add_all([customer, product]); db.flush()
        opportunity = Opportunity(code="OPP-BG", customer_id=customer.id, title="Cơ hội báo giá", stage="PROPOSAL", expected_value=1000)
        db.add(opportunity); db.commit()
        customer_id, product_id, opportunity_id = customer.id, product.id, opportunity.id
    created = client.post("/crm/quotations", headers=auth_headers(), json={
        "code": "BG-TEST", "opportunity_id": opportunity_id, "customer_id": customer_id,
        "valid_until": "2026-08-31", "currency": "VND",
        "items": [{"product_id": product_id, "name": "Đầu cân báo giá", "unit": "Cái", "quantity": 2,
                   "unit_price": 100, "estimated_cost": 60, "discount_percent": 10, "tax_rate": 10}],
    })
    assert created.status_code == 201
    assert float(created.json()["total_amount"]) == 198
    assert float(created.json()["estimated_cost"]) == 120
    assert round(float(created.json()["margin_percent"]), 2) == 33.33
    cloned = client.post(f"/crm/quotations/{created.json()['id']}/clone", headers=auth_headers())
    assert cloned.status_code == 201
    assert cloned.json()["code"] == "BG-TEST-V2"
    assert cloned.json()["version_no"] == 2


def test_goods_receipt_requires_inspection_and_separates_quarantine():
    from app.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier
    with SessionLocal() as db:
        supplier = Supplier(code="NCC-GR", name="Nhà cung cấp GR")
        product = Product(sku="SKU-GR", name="Loadcell GR", category="Thiết bị", unit="Cái", quantity_on_hand=0)
        wrong_product = Product(sku="SKU-GR-WRONG", name="Sản phẩm không đặt", category="Thiết bị", unit="Cái", quantity_on_hand=0)
        db.add_all([supplier, product, wrong_product]); db.flush()
        po = PurchaseOrder(code="PO-GR", supplier_id=supplier.id, status="ORDERED", total_amount=1000)
        po.items = [PurchaseOrderItem(product_id=product.id, quantity=10, unit_price=100)]
        db.add(po); db.commit()
        po_id, product_id, wrong_product_id = po.id, product.id, wrong_product.id
    headers = auth_headers()
    incomplete = client.post("/production/goods-receipts", headers=headers, json={
        "code": "GR-BAD", "purchase_order_id": po_id, "received_date": "2026-07-26",
        "document_checklist": {"po": True, "delivery": False},
        "lines": [{"product_id": product_id, "received_quantity": 10, "accepted_quantity": 8, "quarantine_quantity": 2, "rejected_quantity": 0}],
    })
    assert incomplete.status_code == 422
    wrong = client.post("/production/goods-receipts", headers=headers, json={
        "code": "GR-WRONG", "purchase_order_id": po_id, "received_date": "2026-07-26",
        "document_checklist": {"po": True, "delivery": True, "quality": True},
        "lines": [{"product_id": wrong_product_id, "received_quantity": 999, "accepted_quantity": 999, "quarantine_quantity": 0, "rejected_quantity": 0}],
    })
    assert wrong.status_code == 422
    created = client.post("/production/goods-receipts", headers=headers, json={
        "code": "GR-GOOD", "purchase_order_id": po_id, "received_date": "2026-07-26",
        "document_checklist": {"po": True, "delivery": True, "quality": True},
        "lines": [{"product_id": product_id, "received_quantity": 10, "accepted_quantity": 8, "quarantine_quantity": 2, "rejected_quantity": 0}],
    })
    assert created.status_code == 201
    assert client.post(f"/production/goods-receipts/{created.json()['id']}/post", headers=headers).json()["status"] == "POSTED"
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        assert product.quantity_on_hand == 8
        assert product.quarantine_quantity == 2


def test_inventory_movement_and_foreign_key_enforcement():
    from sqlalchemy.exc import IntegrityError
    from app.models import Product, Project
    with SessionLocal() as db:
        product = Product(sku="SKU-MOVE", name="Sản phẩm movement", category="Kho", unit="Cái", quantity_on_hand=5)
        db.add(product); db.commit(); product_id = product.id
    moved = client.post("/inventory/movements", headers=auth_headers(), json={
        "product_id": product_id, "movement_type": "out", "quantity": 2, "reference": "TEST-MOVE",
    })
    assert moved.status_code == 201
    assert moved.json()["quantity_on_hand"] == 3
    with SessionLocal() as db:
        db.add(Project(code="PRJ-BAD-FK", name="FK invalid", customer_id=999999, order_id=999999))
        try:
            db.commit()
            assert False, "SQLite phải chặn foreign key không tồn tại"
        except IntegrityError:
            db.rollback()


def test_concurrent_reservations_cannot_overbook_stock():
    from app.models import Product
    with SessionLocal() as db:
        product = Product(sku="SKU-RACE", name="Sản phẩm race", category="Kho", unit="Cái", quantity_on_hand=10, reserved_quantity=0)
        db.add(product); db.commit(); product_id = product.id
    headers = auth_headers()
    def reserve():
        return client.post("/inventory/reservations", headers=headers, json={"product_id": product_id, "quantity": 8})
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: reserve(), range(2)))
    assert sorted(x.status_code for x in responses) == [201, 409]
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        assert product.reserved_quantity == 8
        assert product.reserved_quantity <= product.quantity_on_hand


def test_full_payment_synchronizes_order_and_payment_status():
    from app.models import Customer, Receivable, SalesOrder
    with SessionLocal() as db:
        customer = Customer(code="KH-PAY", name="Khách hàng payment", segment="Dự án")
        db.add(customer); db.flush()
        order = SalesOrder(code="SO-PAY", customer_id=customer.id, title="Đơn thu tiền", status="INVOICED", total_amount=1000, payment_status="UNPAID")
        db.add(order); db.flush()
        receivable = Receivable(customer_id=customer.id, order_id=order.id, invoice_no="INV-PAY", amount=1000, paid_amount=0, due_date=date(2026, 8, 1), status="OPEN")
        db.add(receivable); db.commit(); order_id, receivable_id = order.id, receivable.id
    response = client.post(f"/order-flow/orders/{order_id}/receipts", headers=auth_headers(), json={
        "code": "PT-PAY", "receivable_id": receivable_id, "amount": 1000,
        "received_date": "2026-07-26", "method": "BANK_TRANSFER", "transaction_ref": "BANK-PAY",
    })
    assert response.status_code == 201
    with SessionLocal() as db:
        order = db.get(SalesOrder, order_id)
        assert order.status == "PAID"
        assert order.payment_status == "PAID"


def test_permission_negative_and_upload_validation():
    denied = client.get("/finance/receivables", headers=auth_headers("warehouse@test.vn"))
    assert denied.status_code == 403
    bad_entity = client.post(
        "/production/attachments/../../etc/1", headers=auth_headers(),
        data={"document_type": "SIGNED"}, files={"file": ("x.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert bad_entity.status_code in {404, 422}
    from app.models import Customer
    with SessionLocal() as db:
        customer = Customer(code="KH-UPLOAD", name="Upload test", segment="Test")
        db.add(customer); db.commit(); customer_id = customer.id
    unsupported = client.post(
        f"/production/attachments/CONTRACT/{customer_id}", headers=auth_headers(),
        data={"document_type": "SIGNED"}, files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert unsupported.status_code in {404, 415}


def test_warranty_ticket_sla_and_customer_confirmation():
    from app.models import Customer, SalesOrder
    with SessionLocal() as db:
        customer = Customer(code="KH-BH", name="Khách hàng bảo hành", segment="Sản xuất")
        db.add(customer); db.flush()
        order = SalesOrder(code="SO-BH", customer_id=customer.id, title="Đơn bảo hành", status="ACCEPTED", total_amount=1000)
        db.add(order); db.commit()
        customer_id, order_id = customer.id, order.id
    headers = auth_headers()
    warranty = client.post("/production/warranties", headers=headers, json={
        "code": "BH-TEST", "customer_id": customer_id, "sales_order_id": order_id,
        "start_date": "2026-01-01", "end_date": "2026-12-31", "coverage": "Lỗi kỹ thuật",
    })
    assert warranty.status_code == 201
    ticket = client.post("/support/tickets", headers=headers, json={
        "code": "TK-BH", "customer_id": customer_id, "sales_order_id": order_id,
        "subject": "Cân hiển thị sai", "description": "Cần hiệu chuẩn", "priority": "HIGH",
    })
    assert ticket.status_code == 201
    assert ticket.json()["warranty_status"] == "IN_WARRANTY"
    ticket_id = ticket.json()["id"]
    assert client.post(f"/support/tickets/{ticket_id}/respond", headers=headers, json={"note": "Đã tiếp nhận"}).json()["status"] == "IN_PROGRESS"
    assert client.post(f"/support/tickets/{ticket_id}/close", headers=headers, json={"note": "Đóng"}).status_code == 409
    assert client.post(f"/support/tickets/{ticket_id}/resolve", headers=headers, json={"note": "Đã hiệu chuẩn"}).json()["status"] == "RESOLVED"
    assert client.post(f"/support/tickets/{ticket_id}/close", headers=headers, json={"note": "Khách hàng xác nhận"}).json()["status"] == "CLOSED"


def test_locked_account_cannot_login_or_use_existing_token():
    with SessionLocal() as db:
        locked_user = User(
            email="lock-test@vnpro.vn", full_name="Nhân sự khóa test", role="SALES",
            department="Kinh doanh", hashed_password=get_password_hash("Demo@123"),
        )
        db.add(locked_user); db.commit()
        user_id = locked_user.id
    user_login = client.post("/auth/login", json={"email": "lock-test@vnpro.vn", "password": "Demo@123"})
    assert user_login.status_code == 200
    user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
    locked = client.patch(f"/admin/users/{user_id}/active", headers=auth_headers(), json={"is_active": False})
    assert locked.status_code == 200
    assert locked.json()["is_active"] is False
    assert client.get("/auth/me", headers=user_headers).status_code == 401
    assert client.post("/auth/login", json={"email": "lock-test@vnpro.vn", "password": "Demo@123"}).status_code == 403

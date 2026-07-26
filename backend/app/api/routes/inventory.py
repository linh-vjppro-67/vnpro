from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.workflow import assert_transition
from app.db.session import get_db
from app.models import Product, StockMovement, StockReservation, User
from app.schemas import ProductOut, StockMovementCreate, StockReservationCreate, StockReservationOut
from app.services import audit

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/products", response_model=list[ProductOut])
def products(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.INVENTORY_READ))):
    return db.scalars(select(Product).order_by(Product.category, Product.name)).all()


@router.post("/movements", status_code=201)
def movement(payload: StockMovementCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    product = db.scalar(select(Product).where(Product.id == payload.product_id).with_for_update())
    if not product:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    kind = payload.movement_type.upper()
    if kind not in {"IN", "OUT", "ADJUST"}:
        raise HTTPException(422, "movement_type phải là IN, OUT hoặc ADJUST")
    if kind == "IN":
        result = db.execute(update(Product).where(Product.id == product.id).values(quantity_on_hand=Product.quantity_on_hand + payload.quantity))
    elif kind == "OUT":
        result = db.execute(update(Product).where(
            Product.id == product.id, Product.quantity_on_hand - Product.reserved_quantity >= payload.quantity
        ).values(quantity_on_hand=Product.quantity_on_hand - payload.quantity))
    else:
        if payload.quantity < product.reserved_quantity:
            raise HTTPException(409, "Tồn kiểm kê không được thấp hơn số đã giữ")
        result = db.execute(update(Product).where(Product.id == product.id).values(quantity_on_hand=payload.quantity))
    if result.rowcount != 1:
        raise HTTPException(409, "Tồn khả dụng không đủ hoặc vừa được cập nhật")
    db.refresh(product)
    values = payload.model_dump()
    values["movement_type"] = kind
    item = StockMovement(**values, created_by=user.id)
    db.add(item); db.flush(); audit(db, user, "STOCK_" + kind, "PRODUCT", product.id, payload.reference); db.commit()
    return {"id": item.id, "product_id": product.id, "quantity_on_hand": product.quantity_on_hand}


# ---------------------------------------------------------------------------
# Stock reservations (giữ hàng cho đơn hàng / dự án)
# ---------------------------------------------------------------------------

@router.get("/reservations", response_model=list[StockReservationOut])
def reservations(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.INVENTORY_READ))):
    return db.scalars(select(StockReservation).order_by(StockReservation.created_at.desc())).all()


@router.post("/reservations", response_model=StockReservationOut, status_code=201)
def create_reservation(payload: StockReservationCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    product = db.scalar(select(Product).where(Product.id == payload.product_id).with_for_update())
    if not product:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    available = product.quantity_on_hand - product.reserved_quantity
    if available < payload.quantity:
        raise HTTPException(409, f"Tồn khả dụng không đủ (còn {available} {product.unit})")
    item = StockReservation(**payload.model_dump(), status="RESERVED", created_by=user.id)
    changed = db.execute(update(Product).where(
        Product.id == product.id,
        Product.quantity_on_hand - Product.reserved_quantity >= payload.quantity,
    ).values(reserved_quantity=Product.reserved_quantity + payload.quantity))
    if changed.rowcount != 1:
        raise HTTPException(409, "Tồn khả dụng vừa được cập nhật, vui lòng thử lại")
    db.add(item); db.flush(); audit(db, user, "RESERVE", "PRODUCT", product.id, f"{payload.quantity} {product.unit}"); db.commit(); db.refresh(item)
    return item


@router.post("/reservations/{reservation_id}/release", response_model=StockReservationOut)
def release_reservation(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    item = db.get(StockReservation, reservation_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy phiếu giữ hàng")
    assert_transition("STOCK_RESERVATION", item.status, "RELEASED")
    product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
    changed = db.execute(update(Product).where(
        Product.id == product.id, Product.reserved_quantity >= item.quantity,
    ).values(reserved_quantity=Product.reserved_quantity - item.quantity))
    if changed.rowcount != 1:
        raise HTTPException(409, "Số lượng giữ không còn hợp lệ")
    item.status = "RELEASED"
    audit(db, user, "RELEASE", "PRODUCT", product.id, f"{item.quantity} {product.unit}")
    db.commit(); db.refresh(item)
    return item


@router.post("/reservations/{reservation_id}/fulfill", response_model=StockReservationOut)
def fulfill_reservation(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    item = db.get(StockReservation, reservation_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy phiếu giữ hàng")
    assert_transition("STOCK_RESERVATION", item.status, "FULFILLED")
    product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
    if product.quantity_on_hand < item.quantity or product.reserved_quantity < item.quantity:
        raise HTTPException(409, "Tồn kho hoặc số lượng giữ không còn đủ")
    changed = db.execute(update(Product).where(
        Product.id == product.id, Product.reserved_quantity >= item.quantity,
        Product.quantity_on_hand >= item.quantity,
    ).values(
        reserved_quantity=Product.reserved_quantity - item.quantity,
        quantity_on_hand=Product.quantity_on_hand - item.quantity,
    ))
    if changed.rowcount != 1:
        raise HTTPException(409, "Tồn kho vừa được cập nhật, không thể xuất")
    reference = f"SO-{item.sales_order_id}" if item.sales_order_id else (f"DA-{item.project_id}" if item.project_id else None)
    db.add(StockMovement(product_id=product.id, movement_type="OUT", quantity=item.quantity, reference=reference, note="Xuất kho theo phiếu giữ hàng", created_by=user.id))
    item.status = "FULFILLED"
    audit(db, user, "FULFILL", "PRODUCT", product.id, f"{item.quantity} {product.unit}")
    db.commit(); db.refresh(item)
    return item

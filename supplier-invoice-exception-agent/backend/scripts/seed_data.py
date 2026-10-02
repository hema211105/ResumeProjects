from app.data import GOODS_RECEIPTS, INVOICES, PURCHASE_ORDERS, SUPPLIERS
from app.models.db import Base, SessionLocal, engine
from app.models.tables import GoodsReceipt, HistoricalException, Invoice, PurchaseOrder, User


def seed() -> dict[str, int]:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for index, supplier in enumerate(SUPPLIERS, start=1):
            db.merge(User(id=f"user-{index:03d}", email=f"ap.user{index:03d}@example.test", display_name=f"AP Reviewer {index:03d}", role="analyst"))
        for record in INVOICES.values():
            db.merge(Invoice(
                id=record.invoice_id, supplier=record.supplier, po_number=record.po_number,
                invoice_date=record.invoice_date, currency=record.currency, quantity=record.quantity,
                unit_price=record.unit_price, subtotal=record.subtotal, tax=record.tax,
                total=record.total, line_items=[line.model_dump() for line in record.line_items],
            ))
        for record in PURCHASE_ORDERS.values():
            db.merge(PurchaseOrder(id=record.id, supplier=record.supplier, currency=record.currency, quantity=record.quantity, unit_price=record.unit_price, contract_id=record.contract_id))
        for record in GOODS_RECEIPTS.values():
            db.merge(GoodsReceipt(id=record.id, po_number=record.po_number, quantity_received=record.quantity_received, received_date=record.received_date))
        for index in range(50):
            db.merge(HistoricalException(
                id=f"HIST-{index + 1:03d}", invoice_id=f"INV-{1004 + index}",
                issue_type=("quantity_mismatch", "price_mismatch", "tax_mismatch", "missing_receipt", "supplier_mismatch")[index % 5],
                resolution="Synthetic case seeded for retrieval and evaluation; reviewer disposition is required.",
                confidence=round(0.65 + (index % 30) / 100, 2),
            ))
        db.commit()
    return {"users": len(SUPPLIERS), "invoices": len(INVOICES), "purchase_orders": len(PURCHASE_ORDERS), "goods_receipts": len(GOODS_RECEIPTS), "historical_exceptions": 50}


if __name__ == "__main__":
    print(seed())
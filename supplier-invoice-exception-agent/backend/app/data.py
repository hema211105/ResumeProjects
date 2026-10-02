from app.schemas import GoodsReceiptData, InvoiceData, LineItem, PurchaseOrderData

INVOICES: dict[str, InvoiceData] = {
    "INV-1001": InvoiceData(
        invoice_id="INV-1001", supplier="Northstar Components", invoice_date="2026-09-12",
        po_number="PO-9001", quantity=100, unit_price=12.5, subtotal=1250, tax=100,
        total=1350, currency="USD",
        line_items=[LineItem(description="Precision valve", quantity=100, unit_price=12.5, amount=1250)],
    ),
    "INV-1002": InvoiceData(
        invoice_id="INV-1002", supplier="Harbor Office Supply", invoice_date="2026-09-16",
        po_number="PO-9002", quantity=120, unit_price=18, subtotal=2160, tax=172.8,
        total=2332.8, currency="USD",
        line_items=[LineItem(description="Ergonomic chair", quantity=120, unit_price=18, amount=2160)],
    ),
    "INV-1003": InvoiceData(
        invoice_id="INV-1003", supplier="Aster Industrial", invoice_date="2026-09-21",
        po_number="PO-MISSING", quantity=20, unit_price=425, subtotal=8500, tax=680,
        total=9180, currency="USD",
        line_items=[LineItem(description="Servo motor", quantity=20, unit_price=425, amount=8500)],
    ),
}

PURCHASE_ORDERS: dict[str, PurchaseOrderData] = {
    "PO-9001": PurchaseOrderData(id="PO-9001", supplier="Northstar Components", currency="USD", quantity=100, unit_price=12.5, contract_id="CTR-410"),
    "PO-9002": PurchaseOrderData(id="PO-9002", supplier="Harbor Office Supply", currency="USD", quantity=100, unit_price=18, contract_id="CTR-411"),
}

GOODS_RECEIPTS: dict[str, GoodsReceiptData] = {
    "GR-7001": GoodsReceiptData(id="GR-7001", po_number="PO-9001", quantity_received=100, received_date="2026-09-10"),
    "GR-7002": GoodsReceiptData(id="GR-7002", po_number="PO-9002", quantity_received=100, received_date="2026-09-15"),
}

RECEIPT_BY_PO = {receipt.po_number: receipt for receipt in GOODS_RECEIPTS.values()}

SUPPLIERS = [f"Synthetic Supplier {index:03d}" for index in range(1, 101)]

for index in range(200):
    sequence = index + 1
    invoice_id = f"INV-{1004 + index}"
    po_id = f"PO-{10000 + index}"
    supplier = SUPPLIERS[index % len(SUPPLIERS)]
    po_quantity = 25 + (index * 7) % 100
    invoice_quantity = po_quantity + 5 if index % 10 == 0 else po_quantity
    po_price = round(7.5 + (index * 3.17) % 190, 2)
    invoice_price = round(po_price * 1.08, 2) if index % 11 == 0 else po_price
    currency = "EUR" if index % 19 == 0 else "USD"
    invoice_supplier = f"Unverified {supplier}" if index % 23 == 0 else supplier
    subtotal = round(invoice_quantity * invoice_price, 2)
    tax_rate = 0.1 if index % 13 == 0 else 0.08
    tax = round(subtotal * tax_rate, 2)
    invoice_po = None if index % 37 == 0 else po_id

    INVOICES[invoice_id] = InvoiceData(
        invoice_id=invoice_id,
        supplier=invoice_supplier,
        invoice_date=f"2026-{1 + (index // 28) % 9:02d}-{1 + index % 27:02d}",
        po_number=invoice_po,
        quantity=invoice_quantity,
        unit_price=invoice_price,
        subtotal=subtotal,
        tax=tax,
        total=round(subtotal + tax, 2),
        currency=currency,
        line_items=[LineItem(description=f"Synthetic line item {sequence:03d}", quantity=invoice_quantity, unit_price=invoice_price, amount=subtotal)],
    )
    PURCHASE_ORDERS[po_id] = PurchaseOrderData(
        id=po_id,
        supplier=supplier,
        currency="USD" if index % 19 else "EUR",
        quantity=po_quantity,
        unit_price=po_price,
        contract_id=f"CTR-{500 + index % 80:03d}",
    )
    if index % 29 != 0:
        receipt_id = f"GR-{10000 + index}"
        receipt = GoodsReceiptData(
            id=receipt_id,
            po_number=po_id,
            quantity_received=max(0, po_quantity - 3) if index % 10 == 0 else po_quantity,
            received_date=INVOICES[invoice_id].invoice_date,
        )
        GOODS_RECEIPTS[receipt_id] = receipt
        RECEIPT_BY_PO[po_id] = receipt

for index in range(40):
    po_id = f"PO-{11000 + index}"
    PURCHASE_ORDERS[po_id] = PurchaseOrderData(
        id=po_id,
        supplier=SUPPLIERS[index % len(SUPPLIERS)],
        currency="USD",
        quantity=50 + index,
        unit_price=20 + index,
        contract_id=f"CTR-{600 + index:03d}",
    )
    receipt_id = f"GR-{11000 + index}"
    receipt = GoodsReceiptData(id=receipt_id, po_number=po_id, quantity_received=50 + index, received_date="2026-08-15")
    GOODS_RECEIPTS[receipt_id] = receipt
    RECEIPT_BY_PO[po_id] = receipt

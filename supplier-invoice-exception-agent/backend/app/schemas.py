from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)


class InvoiceData(BaseModel):
    invoice_id: str
    supplier: str
    invoice_date: str
    po_number: str | None = None
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)
    tax: float = Field(ge=0)
    total: float = Field(ge=0)
    currency: str
    line_items: list[LineItem] = Field(default_factory=list)


class PurchaseOrderData(BaseModel):
    id: str
    supplier: str
    currency: str
    quantity: float
    unit_price: float
    contract_id: str


class GoodsReceiptData(BaseModel):
    id: str
    po_number: str
    quantity_received: float
    received_date: str


class ToolResult(BaseModel):
    ok: bool
    data: Any = None
    error: str | None = None
    tool: str


class Evidence(BaseModel):
    claim: str
    source: str
    citation: str


class InvestigationResult(BaseModel):
    issue_type: str
    summary: str
    evidence: list[Evidence]
    policy_reference: list[str]
    recommended_action: str
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool


class ApprovalRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT", "MODIFY"]
    reviewer: str = "ap.user"
    rationale: str = ""
    modified_action: str | None = None


class RunRequest(BaseModel):
    invoice_id: str
    user_id: str = "demo-user"
    session_id: str | None = None
    query: str = "Investigate this supplier invoice."


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    user_id: str = "demo-user"


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    title: str
    source: str
    category: str
    section: str = "General"
    page: int = 1
    version: str = "1.0"
    effective_date: str = "2026-01-01"

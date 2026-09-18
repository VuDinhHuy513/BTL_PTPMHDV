"""TODO — hóa đơn và hoàn tiền.

    GET  /invoices?from=&to=
    GET  /invoices/{invoice_id}
    POST /payments/{payment_id}/refund     201

Router này không đặt prefix vì gộp hai nhóm URL khác nhau.
"""
from fastapi import APIRouter

router = APIRouter(tags=["09. Hóa đơn & Thanh toán"])

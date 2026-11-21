from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
import psycopg2.errors
from ..dependencies import get_waybill_generator
from ..services.waybill import WaybillGenerator
from ..models import (
    WaybillCreate,
    WaybillResponse,
    WaybillListResponse
)

router = APIRouter(prefix="/api/waybills", tags=["waybills"])

@router.get("", response_model=WaybillListResponse)
def list_waybills(generator: WaybillGenerator = Depends(get_waybill_generator)):
    items = generator.list_all()
    return {"items": items}

@router.get("/{waybill_id}", response_model=WaybillResponse)
def get_waybill(waybill_id: int, generator: WaybillGenerator = Depends(get_waybill_generator)):
    item = generator.get_by_id(waybill_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Waybill with ID {waybill_id} not found", "code": "NOT_FOUND"}
        )
    return item

@router.post("", response_model=WaybillResponse, status_code=status.HTTP_201_CREATED)
def create_waybill(payload: WaybillCreate, generator: WaybillGenerator = Depends(get_waybill_generator)):
    try:
        item = generator.create(
            supplier_id=payload.supplier_id,
            items=payload.items,
            currency=payload.currency,
            exchange_rate=payload.exchange_rate,
            notes=payload.notes
        )
        return item
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(err), "code": "VALIDATION_ERROR"}
        )
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid supplier ID or ingredient ID", "code": "VALIDATION_ERROR"}
        )

@router.get("/{waybill_id}/print", response_class=HTMLResponse)
def print_waybill(waybill_id: int, generator: WaybillGenerator = Depends(get_waybill_generator)):
    wb = generator.get_printable(waybill_id)
    if not wb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Waybill with ID {waybill_id} not found", "code": "NOT_FOUND"}
        )

    rows_html = ""
    for idx, it in enumerate(wb.get("items", []), start=1):
        rows_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td>{it['ingredient_name']}</td>
            <td style="text-align: center;">{it['unit']}</td>
            <td style="text-align: right;">{it['quantity']}</td>
            <td style="text-align: right;">{it['unit_price']} {wb['currency']}</td>
            <td style="text-align: right;">{it['line_total']} {wb['currency']}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <title>Qaimə № {wb['waybill_number']}</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{
            font-family: 'Times New Roman', Times, serif;
            color: #111;
            margin: 0;
            padding: 20px;
            background: #fff;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #000;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            font-size: 24px;
            letter-spacing: 2px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
            font-size: 14px;
            line-height: 1.6;
        }}
        .meta-box {{
            border: 1px solid #999;
            padding: 12px;
            border-radius: 4px;
        }}
        .meta-box h3 {{
            margin: 0 0 8px 0;
            font-size: 15px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 8px 10px;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .totals-table {{
            width: 320px;
            margin-left: auto;
            border-collapse: collapse;
            font-size: 14px;
            margin-bottom: 35px;
        }}
        .totals-table td {{
            border: none;
            padding: 5px 10px;
        }}
        .totals-table tr.grand-total td {{
            border-top: 2px solid #000;
            font-weight: bold;
            font-size: 16px;
        }}
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 50px;
            margin-top: 40px;
            font-size: 14px;
        }}
        .sign-line {{
            border-bottom: 1px solid #000;
            margin-top: 40px;
            margin-bottom: 5px;
        }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TƏHVİL-TƏSLİM QAİMƏSİ</h1>
        <div><strong>Qaimə №:</strong> {wb['waybill_number']}</div>
        <div><strong>Tarix:</strong> {wb.get('formatted_date', '')}</div>
    </div>

    <div class="meta-grid">
        <div class="meta-box">
            <h3>Təchizatçı Məlumatları</h3>
            <div><strong>Ad:</strong> {wb['supplier_name']}</div>
            <div><strong>VÖEN:</strong> {wb.get('supplier_voen', '')}</div>
            <div><strong>Telefon:</strong> {wb.get('supplier_phone', '')}</div>
            <div><strong>Ünvan:</strong> {wb.get('supplier_address', '') or '—'}</div>
        </div>
        <div class="meta-box">
            <h3>Alıcı Məlumatları</h3>
            <div><strong>Müəssisə:</strong> SmartBaku HoReCa ERP</div>
            <div><strong>Valyuta:</strong> {wb['currency']} (Məzənnə: {wb['exchange_rate']})</div>
            <div><strong>Qeydlər:</strong> {wb.get('notes', '') or '—'}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 40px;">№</th>
                <th>Məhsulun adı</th>
                <th style="width: 70px;">Ölçü vahidi</th>
                <th style="width: 90px;">Miqdar</th>
                <th style="width: 100px;">Vahid qiymət</th>
                <th style="width: 110px;">Cəmi</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <table class="totals-table">
        <tr>
            <td style="text-align: right;"><strong>Ara cəm:</strong></td>
            <td style="text-align: right;">{wb['subtotal']} {wb['currency']}</td>
        </tr>
        <tr>
            <td style="text-align: right;"><strong>ƏDV ({wb['edv_rate']}%):</strong></td>
            <td style="text-align: right;">{wb['edv_amount']} {wb['currency']}</td>
        </tr>
        <tr class="grand-total">
            <td style="text-align: right;">YEKUN:</td>
            <td style="text-align: right;">{wb['total']} {wb['currency']}</td>
        </tr>
    </table>

    <div class="signatures">
        <div>
            <div>Təhvil verdi (Təchizatçı):</div>
            <div class="sign-line"></div>
            <div style="font-size: 12px; color: #666; text-align: center;">(İmza və Möhür)</div>
        </div>
        <div>
            <div>Təhvil aldı (Məsul şəxs):</div>
            <div class="sign-line"></div>
            <div style="font-size: 12px; color: #666; text-align: center;">(İmza)</div>
        </div>
    </div>

    <script class="no-print">
        window.addEventListener('DOMContentLoaded', () => {{
            setTimeout(() => {{
                window.print();
            }}, 300);
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

from datetime import datetime
from decimal import Decimal
from typing import Any
from ..database import DatabaseManager
from ..models import WaybillItemInput
from .inventory import InventoryService

class WaybillGenerator:
    def __init__(
        self,
        db: DatabaseManager,
        inventory: InventoryService | None = None,
        edv_rate: Decimal = Decimal("18.00")
    ) -> None:
        self.db = db
        self.inventory = inventory
        self.edv_rate = edv_rate

    def generate_waybill_number(self, cursor: Any) -> str:
        today_str = datetime.now().strftime("%Y%m%d")
        cursor.execute("SELECT COUNT(*) AS count FROM waybills WHERE DATE(created_at) = CURRENT_DATE;")
        count = cursor.fetchone()["count"] + 1
        candidate = f"WB-{today_str}-{count:04d}"

        # Ensure uniqueness
        while True:
            cursor.execute("SELECT 1 FROM waybills WHERE waybill_number = %s;", (candidate,))
            if not cursor.fetchone():
                break
            count += 1
            candidate = f"WB-{today_str}-{count:04d}"

        return candidate

    def create(
        self,
        supplier_id: int,
        items: list[WaybillItemInput],
        currency: str = "AZN",
        exchange_rate: Decimal = Decimal("1.000000"),
        notes: str | None = ""
    ) -> dict[str, Any]:
        if not items:
            raise ValueError("Waybill must have at least one line item.")

        with self.db.get_connection() as (_, cursor):
            cursor.execute("SELECT id, name FROM suppliers WHERE id = %s;", (supplier_id,))
            supplier = cursor.fetchone()
            if not supplier:
                raise ValueError(f"Supplier with ID {supplier_id} not found.")

            # Validate all ingredients exist before making modifications
            ingredient_ids = [it.ingredient_id for it in items]
            cursor.execute(
                "SELECT id, name FROM ingredients WHERE id = ANY(%s);",
                (ingredient_ids,)
            )
            found_ingredients = {r["id"]: r["name"] for r in cursor.fetchall()}
            for i_id in ingredient_ids:
                if i_id not in found_ingredients:
                    raise ValueError(f"Ingredient with ID {i_id} not found.")

            # 1. Compute line totals and subtotal
            line_items_data = []
            subtotal = Decimal("0.00")
            for it in items:
                line_total = round(it.quantity * it.unit_price, 2)
                subtotal += line_total
                line_items_data.append((it, line_total))

            # 2. Compute 18% ƏDV and total
            edv_amount = round(subtotal * self.edv_rate / Decimal("100"), 2)
            total = subtotal + edv_amount

            # 3. Generate waybill number
            waybill_number = self.generate_waybill_number(cursor)

            # 4. Insert waybills row
            cursor.execute(
                """
                INSERT INTO waybills (
                    waybill_number, supplier_id, subtotal, edv_rate, edv_amount,
                    total, currency, exchange_rate, notes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, created_at;
                """,
                (
                    waybill_number,
                    supplier_id,
                    subtotal,
                    self.edv_rate,
                    edv_amount,
                    total,
                    currency,
                    exchange_rate,
                    notes or ""
                )
            )
            wb_row = cursor.fetchone()
            waybill_id = wb_row["id"]

            # 5. Insert waybill_items and update ingredient stock
            for it, line_total in line_items_data:
                cursor.execute(
                    """
                    INSERT INTO waybill_items (waybill_id, ingredient_id, quantity, unit_price, line_total)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (waybill_id, it.ingredient_id, it.quantity, it.unit_price, line_total)
                )

                # Increase stock and update last unit price
                cursor.execute(
                    """
                    UPDATE ingredients
                    SET quantity = quantity + %s,
                        unit_price = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (it.quantity, it.unit_price, it.ingredient_id)
                )

        return self.get_by_id(waybill_id)  # type: ignore

    def list_all(self) -> list[dict[str, Any]]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT w.id, w.waybill_number, w.supplier_id, s.name AS supplier_name,
                       w.subtotal, w.edv_rate, w.edv_amount, w.total,
                       w.currency, w.exchange_rate, w.notes, w.created_at
                FROM waybills w
                JOIN suppliers s ON w.supplier_id = s.id
                ORDER BY w.created_at DESC;
                """
            )
            return cursor.fetchall()

    def get_by_id(self, waybill_id: int) -> dict[str, Any] | None:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT w.id, w.waybill_number, w.supplier_id, s.name AS supplier_name,
                       w.subtotal, w.edv_rate, w.edv_amount, w.total,
                       w.currency, w.exchange_rate, w.notes, w.created_at
                FROM waybills w
                JOIN suppliers s ON w.supplier_id = s.id
                WHERE w.id = %s;
                """,
                (waybill_id,)
            )
            waybill = cursor.fetchone()
            if not waybill:
                return None

            cursor.execute(
                """
                SELECT wi.id, wi.waybill_id, wi.ingredient_id, i.name AS ingredient_name,
                       i.unit, wi.quantity, wi.unit_price, wi.line_total
                FROM waybill_items wi
                JOIN ingredients i ON wi.ingredient_id = i.id
                WHERE wi.waybill_id = %s
                ORDER BY wi.id ASC;
                """,
                (waybill_id,)
            )
            items = cursor.fetchall()

        wb_dict = dict(waybill)
        wb_dict["items"] = items
        return wb_dict

    def get_printable(self, waybill_id: int) -> dict[str, Any] | None:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT w.id, w.waybill_number, w.supplier_id, s.name AS supplier_name,
                       s.voen AS supplier_voen, s.phone AS supplier_phone,
                       s.address AS supplier_address, s.email AS supplier_email,
                       w.subtotal, w.edv_rate, w.edv_amount, w.total,
                       w.currency, w.exchange_rate, w.notes, w.created_at
                FROM waybills w
                JOIN suppliers s ON w.supplier_id = s.id
                WHERE w.id = %s;
                """,
                (waybill_id,)
            )
            waybill = cursor.fetchone()
            if not waybill:
                return None

            cursor.execute(
                """
                SELECT wi.id, wi.waybill_id, wi.ingredient_id, i.name AS ingredient_name,
                       i.unit, wi.quantity, wi.unit_price, wi.line_total
                FROM waybill_items wi
                JOIN ingredients i ON wi.ingredient_id = i.id
                WHERE wi.waybill_id = %s
                ORDER BY wi.id ASC;
                """,
                (waybill_id,)
            )
            items = cursor.fetchall()

        wb_dict = dict(waybill)
        wb_dict["items"] = items
        if wb_dict["created_at"]:
            wb_dict["formatted_date"] = wb_dict["created_at"].strftime("%d.%m.%Y %H:%M")
        else:
            wb_dict["formatted_date"] = ""
        return wb_dict

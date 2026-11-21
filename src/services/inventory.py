from decimal import Decimal
from typing import Any
from ..database import DatabaseManager

class InsufficientStockError(Exception):
    def __init__(
        self,
        ingredient_id: int,
        ingredient_name: str,
        available: Decimal,
        requested: Decimal,
        details: list[dict[str, Any]] | None = None
    ) -> None:
        self.ingredient_id = ingredient_id
        self.ingredient_name = ingredient_name
        self.available = available
        self.requested = requested
        self.details = details or [{
            "ingredient_id": ingredient_id,
            "ingredient_name": ingredient_name,
            "available": str(available),
            "requested": str(requested)
        }]
        super().__init__(
            f"Insufficient stock for ingredient '{ingredient_name}' (ID: {ingredient_id}): "
            f"available {available}, requested {requested}"
        )

class InventoryService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_all(self) -> list[dict[str, Any]]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT i.id, i.name, i.unit, i.quantity, i.min_stock, i.unit_price,
                       i.supplier_id, s.name AS supplier_name, i.created_at, i.updated_at
                FROM ingredients i
                LEFT JOIN suppliers s ON i.supplier_id = s.id
                ORDER BY i.name ASC;
                """
            )
            return cursor.fetchall()

    def get_by_id(self, ingredient_id: int) -> dict[str, Any] | None:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT i.id, i.name, i.unit, i.quantity, i.min_stock, i.unit_price,
                       i.supplier_id, s.name AS supplier_name, i.created_at, i.updated_at
                FROM ingredients i
                LEFT JOIN suppliers s ON i.supplier_id = s.id
                WHERE i.id = %s;
                """
                , (ingredient_id,)
            )
            return cursor.fetchone()

    def create(
        self,
        name: str,
        unit: str,
        quantity: Decimal,
        min_stock: Decimal,
        unit_price: Decimal,
        supplier_id: int | None
    ) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO ingredients (name, unit, quantity, min_stock, unit_price, supplier_id, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, name, unit, quantity, min_stock, unit_price, supplier_id, created_at, updated_at;
                """,
                (name, unit, quantity, min_stock, unit_price, supplier_id)
            )
            row = cursor.fetchone()

            supplier_name = None
            if supplier_id:
                cursor.execute("SELECT name FROM suppliers WHERE id = %s;", (supplier_id,))
                s_row = cursor.fetchone()
                if s_row:
                    supplier_name = s_row["name"]

            row["supplier_name"] = supplier_name
            return row

    def update(self, ingredient_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "unit", "quantity", "min_stock", "unit_price", "supplier_id"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_by_id(ingredient_id)

        set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
        params = list(updates.values())
        params.extend([ingredient_id])

        with self.db.get_connection() as (_, cursor):
            query = f"""
                UPDATE ingredients
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, tuple(params))
            if not cursor.fetchone():
                return None

        return self.get_by_id(ingredient_id)

    def delete(self, ingredient_id: int) -> bool:
        with self.db.get_connection() as (_, cursor):
            cursor.execute("DELETE FROM ingredients WHERE id = %s RETURNING id;", (ingredient_id,))
            return cursor.fetchone() is not None

    def adjust_stock(self, ingredient_id: int, delta: Decimal) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT id, name, unit, quantity, min_stock, unit_price, supplier_id
                FROM ingredients
                WHERE id = %s
                FOR UPDATE;
                """,
                (ingredient_id,)
            )
            ingredient = cursor.fetchone()
            if not ingredient:
                raise ValueError(f"Ingredient with ID {ingredient_id} not found.")

            current_qty = Decimal(str(ingredient["quantity"]))
            new_qty = current_qty + delta
            if new_qty < 0:
                raise InsufficientStockError(
                    ingredient_id=ingredient_id,
                    ingredient_name=ingredient["name"],
                    available=current_qty,
                    requested=abs(delta)
                )

            cursor.execute(
                """
                UPDATE ingredients
                SET quantity = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id;
                """,
                (new_qty, ingredient_id)
            )

        return self.get_by_id(ingredient_id)  # type: ignore

    def get_low_stock(self) -> list[dict[str, Any]]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT i.id, i.name, i.unit, i.quantity, i.min_stock, i.unit_price,
                       i.supplier_id, s.name AS supplier_name, i.created_at, i.updated_at
                FROM ingredients i
                LEFT JOIN suppliers s ON i.supplier_id = s.id
                WHERE i.quantity <= i.min_stock
                ORDER BY (i.min_stock - i.quantity) DESC;
                """
            )
            return cursor.fetchall()

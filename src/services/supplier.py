from typing import Any
from ..database import DatabaseManager

class SupplierService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_all(self) -> list[dict[str, Any]]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT id, name, voen, phone, email, address, created_at
                FROM suppliers
                ORDER BY name ASC;
                """
            )
            return cursor.fetchall()

    def get_by_id(self, supplier_id: int) -> dict[str, Any] | None:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT id, name, voen, phone, email, address, created_at
                FROM suppliers
                WHERE id = %s;
                """,
                (supplier_id,)
            )
            return cursor.fetchone()

    def create(
        self,
        name: str,
        voen: str,
        phone: str,
        email: str | None = None,
        address: str | None = None
    ) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO suppliers (name, voen, phone, email, address, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id, name, voen, phone, email, address, created_at;
                """,
                (name, voen, phone, email, address)
            )
            return cursor.fetchone()

    def update(self, supplier_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "voen", "phone", "email", "address"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_by_id(supplier_id)

        set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
        params = list(updates.values())
        params.append(supplier_id)

        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                f"UPDATE suppliers SET {set_clause} WHERE id = %s RETURNING id;",
                tuple(params)
            )
            if not cursor.fetchone():
                return None

        return self.get_by_id(supplier_id)

    def delete(self, supplier_id: int) -> bool:
        with self.db.get_connection() as (_, cursor):
            cursor.execute("DELETE FROM suppliers WHERE id = %s RETURNING id;", (supplier_id,))
            return cursor.fetchone() is not None

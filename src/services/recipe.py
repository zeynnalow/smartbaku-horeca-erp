from decimal import Decimal
from typing import Any
from ..database import DatabaseManager
from ..models import RecipeItemInput
from .inventory import InsufficientStockError

class RecipeEngine:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_all(self) -> list[dict[str, Any]]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT id, name, category, selling_price, is_active, created_at
                FROM recipes
                ORDER BY id ASC;
                """
            )
            recipes = cursor.fetchall()
            if not recipes:
                return []

            cursor.execute(
                """
                SELECT ri.id, ri.recipe_id, ri.ingredient_id, i.name AS ingredient_name,
                       i.unit, ri.quantity_needed, i.unit_price
                FROM recipe_items ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                ORDER BY ri.recipe_id, ri.ingredient_id ASC;
                """
            )
            all_items = cursor.fetchall()

        items_by_recipe: dict[int, list[dict[str, Any]]] = {}
        for it in all_items:
            items_by_recipe.setdefault(it["recipe_id"], []).append(it)

        result: list[dict[str, Any]] = []
        for r in recipes:
            items = items_by_recipe.get(r["id"], [])
            cost = sum(
                (Decimal(str(it["quantity_needed"])) * Decimal(str(it["unit_price"] or 0)))
                for it in items
            )
            selling = Decimal(str(r["selling_price"]))
            margin = Decimal("0.00")
            if selling > 0:
                margin = round(((selling - cost) / selling) * Decimal("100"), 2)

            r_dict = dict(r)
            r_dict["cost_per_serving"] = round(cost, 2)
            r_dict["margin_percent"] = margin
            r_dict["items"] = items
            result.append(r_dict)

        return result

    def get_by_id(self, recipe_id: int) -> dict[str, Any] | None:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT id, name, category, selling_price, is_active, created_at
                FROM recipes
                WHERE id = %s;
                """,
                (recipe_id,)
            )
            recipe = cursor.fetchone()
            if not recipe:
                return None

            cursor.execute(
                """
                SELECT ri.id, ri.recipe_id, ri.ingredient_id, i.name AS ingredient_name,
                       i.unit, ri.quantity_needed, i.unit_price
                FROM recipe_items ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = %s
                ORDER BY ri.ingredient_id ASC;
                """,
                (recipe_id,)
            )
            items = cursor.fetchall()

        cost = sum(
            (Decimal(str(it["quantity_needed"])) * Decimal(str(it["unit_price"] or 0)))
            for it in items
        )
        selling = Decimal(str(recipe["selling_price"]))
        margin = Decimal("0.00")
        if selling > 0:
            margin = round(((selling - cost) / selling) * Decimal("100"), 2)

        r_dict = dict(recipe)
        r_dict["cost_per_serving"] = round(cost, 2)
        r_dict["margin_percent"] = margin
        r_dict["items"] = items
        return r_dict

    def create(
        self,
        name: str,
        category: str,
        selling_price: Decimal,
        items: list[RecipeItemInput]
    ) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO recipes (name, category, selling_price)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (name, category, selling_price)
            )
            recipe_id = cursor.fetchone()["id"]

            for item in items:
                cursor.execute(
                    """
                    INSERT INTO recipe_items (recipe_id, ingredient_id, quantity_needed)
                    VALUES (%s, %s, %s);
                    """,
                    (recipe_id, item.ingredient_id, item.quantity_needed)
                )

        return self.get_by_id(recipe_id)  # type: ignore

    def update(
        self,
        recipe_id: int,
        name: str | None = None,
        category: str | None = None,
        selling_price: Decimal | None = None,
        is_active: bool | None = None,
        items: list[RecipeItemInput] | None = None
    ) -> dict[str, Any] | None:
        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if category is not None:
            updates["category"] = category
        if selling_price is not None:
            updates["selling_price"] = selling_price
        if is_active is not None:
            updates["is_active"] = is_active

        with self.db.get_connection() as (_, cursor):
            if updates:
                set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
                params = list(updates.values())
                params.append(recipe_id)
                cursor.execute(
                    f"UPDATE recipes SET {set_clause} WHERE id = %s RETURNING id;",
                    tuple(params)
                )
                if not cursor.fetchone():
                    return None

            if items is not None:
                cursor.execute("DELETE FROM recipe_items WHERE recipe_id = %s;", (recipe_id,))
                for it in items:
                    cursor.execute(
                        """
                        INSERT INTO recipe_items (recipe_id, ingredient_id, quantity_needed)
                        VALUES (%s, %s, %s);
                        """,
                        (recipe_id, it.ingredient_id, it.quantity_needed)
                    )

        return self.get_by_id(recipe_id)

    def delete(self, recipe_id: int) -> bool:
        with self.db.get_connection() as (_, cursor):
            cursor.execute("DELETE FROM recipes WHERE id = %s RETURNING id;", (recipe_id,))
            return cursor.fetchone() is not None

    def check_availability(self, recipe_id: int, servings: int = 1) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute("SELECT id, name FROM recipes WHERE id = %s;", (recipe_id,))
            recipe = cursor.fetchone()
            if not recipe:
                raise ValueError(f"Recipe with ID {recipe_id} not found.")

            cursor.execute(
                """
                SELECT ri.ingredient_id, i.name AS ingredient_name, i.unit,
                       ri.quantity_needed, i.quantity
                FROM recipe_items ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = %s
                ORDER BY ri.ingredient_id ASC;
                """,
                (recipe_id,)
            )
            items = cursor.fetchall()

        servings_dec = Decimal(str(servings))
        check_items = []
        can_cook = True

        for it in items:
            required = round(Decimal(str(it["quantity_needed"])) * servings_dec, 4)
            available = Decimal(str(it["quantity"]))
            sufficient = available >= required
            if not sufficient:
                can_cook = False
            check_items.append({
                "ingredient_id": it["ingredient_id"],
                "ingredient_name": it["ingredient_name"],
                "unit": it["unit"],
                "required": required,
                "available": available,
                "sufficient": sufficient
            })

        return {
            "can_cook": can_cook,
            "items": check_items
        }

    def cook(self, recipe_id: int, servings: int = 1) -> dict[str, Any]:
        """
        Atomic Cook Operation:
        Locks ingredients ordered by ingredient_id ASC to prevent deadlocks.
        Validates that available >= needed for ALL items before deducting anything.
        """
        if servings <= 0:
            raise ValueError("Servings must be at least 1.")

        servings_dec = Decimal(str(servings))

        with self.db.get_connection() as (_, cursor):
            cursor.execute("SELECT id, name FROM recipes WHERE id = %s;", (recipe_id,))
            recipe = cursor.fetchone()
            if not recipe:
                raise ValueError(f"Recipe with ID {recipe_id} not found.")

            cursor.execute(
                """
                SELECT ri.ingredient_id, i.name AS ingredient_name, i.unit,
                       ri.quantity_needed, i.quantity
                FROM recipe_items ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = %s
                ORDER BY i.id ASC
                FOR UPDATE OF i;
                """,
                (recipe_id,)
            )
            items = cursor.fetchall()
            if not items:
                raise ValueError(f"Recipe '{recipe['name']}' has no ingredients configured.")

            shortages: list[dict[str, Any]] = []
            planned_deductions = []

            for it in items:
                needed = round(Decimal(str(it["quantity_needed"])) * servings_dec, 4)
                available = Decimal(str(it["quantity"]))
                if available < needed:
                    shortages.append({
                        "ingredient_id": it["ingredient_id"],
                        "ingredient_name": it["ingredient_name"],
                        "available": str(available),
                        "requested": str(needed)
                    })
                else:
                    planned_deductions.append((it, needed))

            if shortages:
                first = shortages[0]
                raise InsufficientStockError(
                    ingredient_id=first["ingredient_id"],
                    ingredient_name=first["ingredient_name"],
                    available=Decimal(first["available"]),
                    requested=Decimal(first["requested"]),
                    details=shortages
                )

            deductions = []
            for it, needed in planned_deductions:
                cursor.execute(
                    """
                    UPDATE ingredients
                    SET quantity = quantity - %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING quantity;
                    """,
                    (needed, it["ingredient_id"])
                )
                remaining = cursor.fetchone()["quantity"]
                deductions.append({
                    "ingredient_id": it["ingredient_id"],
                    "ingredient_name": it["ingredient_name"],
                    "unit": it["unit"],
                    "deducted": needed,
                    "remaining": remaining
                })

            return {
                "recipe_id": recipe_id,
                "recipe_name": recipe["name"],
                "servings": servings,
                "deductions": deductions
            }

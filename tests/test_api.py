import uuid
from decimal import Decimal
import pytest
from starlette.testclient import TestClient
from src.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

# ============================================================================
# 1. INVENTORY CRUD & STOCK ADJUST TESTS
# ============================================================================
def test_inventory_crud_and_adjust(client):
    unique_name = f"Test Yağ {uuid.uuid4().hex[:6]}"
    create_payload = {
        "name": unique_name,
        "unit": "litr",
        "quantity": "15.00",
        "min_stock": "5.00",
        "unit_price": "14.50",
        "supplier_id": 1
    }
    res = client.post("/api/ingredients", json=create_payload)
    assert res.status_code == 201
    created = res.json()
    ing_id = created["id"]
    assert created["name"] == unique_name
    assert Decimal(str(created["quantity"])) == Decimal("15.00")

    # Read single ingredient
    res = client.get(f"/api/ingredients/{ing_id}")
    assert res.status_code == 200
    assert res.json()["id"] == ing_id

    # Update ingredient
    update_payload = {"unit_price": "16.00"}
    res = client.put(f"/api/ingredients/{ing_id}", json=update_payload)
    assert res.status_code == 200
    assert Decimal(str(res.json()["unit_price"])) == Decimal("16.00")

    # Adjust stock positively (+5.00 -> 20.00)
    res = client.post(f"/api/ingredients/{ing_id}/adjust-stock", json={"delta": "5.00"})
    assert res.status_code == 200
    assert Decimal(str(res.json()["quantity"])) == Decimal("20.00")

    # Adjust stock negatively within available range (-10.00 -> 10.00)
    res = client.post(f"/api/ingredients/{ing_id}/adjust-stock", json={"delta": "-10.00"})
    assert res.status_code == 200
    assert Decimal(str(res.json()["quantity"])) == Decimal("10.00")

    # Adjust stock negatively beyond available range (must fail with 409)
    res = client.post(f"/api/ingredients/{ing_id}/adjust-stock", json={"delta": "-50.00"})
    assert res.status_code == 409
    err_body = res.json()
    assert err_body["code"] == "INSUFFICIENT_STOCK"

    # Check low stock endpoint
    res = client.get("/api/ingredients/low-stock")
    assert res.status_code == 200
    assert "items" in res.json()

    # Delete test ingredient
    res = client.delete(f"/api/ingredients/{ing_id}")
    assert res.status_code == 204

    # Verify deleted
    res = client.get(f"/api/ingredients/{ing_id}")
    assert res.status_code == 404

# ============================================================================
# 2. ATOMIC RECIPE COOKING & INSUFFICIENT STOCK ROLLBACK
# ============================================================================
def test_atomic_recipe_cook_and_insufficient_stock(client):
    unique_ing_name = f"Test Quzu {uuid.uuid4().hex[:6]}"
    unique_rec_name = f"Test Basdırma {uuid.uuid4().hex[:6]}"

    # 1. Create a dedicated test ingredient with 10.00 kg
    ing_res = client.post("/api/ingredients", json={
        "name": unique_ing_name,
        "unit": "kq",
        "quantity": "10.00",
        "min_stock": "2.00",
        "unit_price": "18.00"
    })
    assert ing_res.status_code == 201
    test_ing_id = ing_res.json()["id"]

    # 2. Create a test recipe requiring 2.00 kg per serving
    rec_res = client.post("/api/recipes", json={
        "name": unique_rec_name,
        "category": "Əsas yemək",
        "selling_price": "25.00",
        "items": [
            {"ingredient_id": test_ing_id, "quantity_needed": "2.0000"}
        ]
    })
    assert rec_res.status_code == 201
    rec_id = rec_res.json()["id"]

    # 3. Check availability for 2 servings (requires 4.00 kg, has 10.00 kg)
    chk_res = client.post(f"/api/recipes/{rec_id}/check", json={"servings": 2})
    assert chk_res.status_code == 200
    assert chk_res.json()["can_cook"] is True

    # 4. Cook 2 servings (deducts 4.00 kg -> 6.00 kg remaining)
    cook_res = client.post(f"/api/recipes/{rec_id}/cook", json={"servings": 2})
    assert cook_res.status_code == 200
    assert cook_res.json()["servings"] == 2
    deductions = cook_res.json()["deductions"]
    assert len(deductions) == 1
    assert Decimal(str(deductions[0]["deducted"])) == Decimal("4.0000")
    assert Decimal(str(deductions[0]["remaining"])) == Decimal("6.00")

    # Verify ingredient stock in database reflects the atomic deduction
    ing_check = client.get(f"/api/ingredients/{test_ing_id}").json()
    assert Decimal(str(ing_check["quantity"])) == Decimal("6.00")

    # 5. Cook excessive servings: try to cook 10 servings (requires 20 kg, has 6 kg)
    # MUST return 409 Conflict with INSUFFICIENT_STOCK
    fail_cook = client.post(f"/api/recipes/{rec_id}/cook", json={"servings": 10})
    assert fail_cook.status_code == 409
    err = fail_cook.json()
    assert err["code"] == "INSUFFICIENT_STOCK"
    assert "details" in err

    # 6. Verify ATOMIC ROLLBACK: stock must remain exactly 6.00 kg!
    ing_after_rollback = client.get(f"/api/ingredients/{test_ing_id}").json()
    assert Decimal(str(ing_after_rollback["quantity"])) == Decimal("6.00")

    # Cleanup
    client.delete(f"/api/recipes/{rec_id}")
    client.delete(f"/api/ingredients/{test_ing_id}")

# ============================================================================
# 3. SUPPLIER VÖEN VALIDATION TESTS
# ============================================================================
def test_supplier_voen_crud_and_uniqueness(client):
    unique_voen = f"99{uuid.uuid4().int % 100000000:08d}"
    payload = {
        "name": f"Test MMC {uuid.uuid4().hex[:6]}",
        "voen": unique_voen,
        "phone": "+994 50 123 45 67",
        "email": "info@test.az",
        "address": "Bakı şəhəri"
    }
    res = client.post("/api/suppliers", json=payload)
    assert res.status_code == 201
    sup_id = res.json()["id"]
    assert res.json()["voen"] == unique_voen

    # Duplicate VÖEN must fail with 409 CONFLICT
    duplicate_res = client.post("/api/suppliers", json={
        "name": "Duplicate MMC",
        "voen": unique_voen,
        "phone": "+994 12 000 00 00"
    })
    assert duplicate_res.status_code == 409

    # Cleanup
    client.delete(f"/api/suppliers/{sup_id}")

# ============================================================================
# 4. WAYBILL 18% ƏDV (VAT) CALCULATION & STOCK RECEIPT
# ============================================================================
def test_waybill_edv_calculation_and_stock_receipt(client):
    unique_ing_name = f"Test Qaymaq {uuid.uuid4().hex[:6]}"
    ing_res = client.post("/api/ingredients", json={
        "name": unique_ing_name,
        "unit": "litr",
        "quantity": "5.00",
        "min_stock": "2.00",
        "unit_price": "6.00"
    })
    assert ing_res.status_code == 201
    ing = ing_res.json()
    ing_id = ing["id"]

    # Create waybill for 20 liters at 10.00 AZN per liter
    # Subtotal: 20 * 10 = 200.00 AZN
    # ƏDV (18%): 200 * 0.18 = 36.00 AZN
    # Total: 200 + 36 = 236.00 AZN
    wb_payload = {
        "supplier_id": 1,
        "currency": "AZN",
        "exchange_rate": "1.000000",
        "notes": "Test ƏDV Qaiməsi",
        "items": [
            {"ingredient_id": ing_id, "quantity": "20.00", "unit_price": "10.00"}
        ]
    }
    wb_res = client.post("/api/waybills", json=wb_payload)
    assert wb_res.status_code == 201
    wb = wb_res.json()
    wb_id = wb["id"]

    # Verify calculation
    assert Decimal(str(wb["subtotal"])) == Decimal("200.00")
    assert Decimal(str(wb["edv_rate"])) == Decimal("18.00")
    assert Decimal(str(wb["edv_amount"])) == Decimal("36.00")
    assert Decimal(str(wb["total"])) == Decimal("236.00")
    assert wb["waybill_number"].startswith("WB-")

    # Verify stock increased: 5.00 + 20.00 = 25.00
    updated_ing = client.get(f"/api/ingredients/{ing_id}").json()
    assert Decimal(str(updated_ing["quantity"])) == Decimal("25.00")
    assert Decimal(str(updated_ing["unit_price"])) == Decimal("10.00")

    # Verify Print View route
    print_res = client.get(f"/waybills/{wb_id}/print")
    assert print_res.status_code == 200
    assert "Təhvil-Təslim Qaiməsi" in print_res.text
    assert wb["waybill_number"] in print_res.text

# ============================================================================
# 5. CBAR CURRENCY SYNC & OFFLINE FALLBACK
# ============================================================================
def test_currency_rates_and_sync(client):
    # Fetch latest rates
    rates_res = client.get("/api/currency/rates")
    assert rates_res.status_code == 200
    rates_data = rates_res.json()
    assert "rates" in rates_data
    assert "USD" in rates_data["rates"]
    assert "EUR" in rates_data["rates"]

    # Trigger sync (returns live cbar.az rates or cached fallback)
    sync_res = client.post("/api/currency/sync")
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["source"] in ("cbar.az", "cache")
    assert Decimal(str(sync_data["rates"]["USD"])) > 0

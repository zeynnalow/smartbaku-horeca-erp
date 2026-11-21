from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

# --- Global Error Envelope ---
class ErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)

# --- Ingredient Schemas ---
class IngredientBase(BaseModel):
    name: str
    unit: str
    quantity: Decimal = Decimal("0.00")
    min_stock: Decimal = Decimal("0.00")
    unit_price: Decimal = Decimal("0.00")
    supplier_id: int | None = None

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    min_stock: Decimal | None = None
    unit_price: Decimal | None = None
    supplier_id: int | None = None

class IngredientResponse(IngredientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class IngredientListResponse(BaseModel):
    items: list[IngredientResponse]

class StockAdjustRequest(BaseModel):
    delta: Decimal

# --- Recipe Schemas ---
class RecipeItemInput(BaseModel):
    ingredient_id: int
    quantity_needed: Decimal

class RecipeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    recipe_id: int | None = None
    ingredient_id: int
    ingredient_name: str | None = None
    unit: str | None = None
    quantity_needed: Decimal
    unit_price: Decimal | None = None

class RecipeCreate(BaseModel):
    name: str
    category: str
    selling_price: Decimal
    items: list[RecipeItemInput] = []

class RecipeUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    selling_price: Decimal | None = None
    is_active: bool | None = None
    items: list[RecipeItemInput] | None = None

class RecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    selling_price: Decimal
    is_active: bool = True
    cost_per_serving: Decimal | None = None
    margin_percent: Decimal | None = None
    items: list[RecipeItemResponse] = []
    created_at: datetime | None = None

class RecipeListResponse(BaseModel):
    items: list[RecipeResponse]

class RecipeCheckRequest(BaseModel):
    servings: int = 1

class RecipeCheckItem(BaseModel):
    ingredient_id: int
    ingredient_name: str
    unit: str
    required: Decimal
    available: Decimal
    sufficient: bool

class RecipeCheckResponse(BaseModel):
    can_cook: bool
    items: list[RecipeCheckItem]

class RecipeCookRequest(BaseModel):
    servings: int = 1

class CookDeduction(BaseModel):
    ingredient_id: int
    ingredient_name: str
    unit: str
    deducted: Decimal
    remaining: Decimal

class RecipeCookResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    servings: int
    deductions: list[CookDeduction]

# --- Supplier Schemas ---
class SupplierCreate(BaseModel):
    name: str
    voen: str
    phone: str
    email: str | None = None
    address: str | None = None

class SupplierUpdate(BaseModel):
    name: str | None = None
    voen: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None

class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    voen: str
    phone: str
    email: str | None = None
    address: str | None = None
    created_at: datetime | None = None

class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]

# --- Waybill Schemas ---
class WaybillItemInput(BaseModel):
    ingredient_id: int
    quantity: Decimal
    unit_price: Decimal

class WaybillItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    waybill_id: int | None = None
    ingredient_id: int
    ingredient_name: str | None = None
    unit: str | None = None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

class WaybillCreate(BaseModel):
    supplier_id: int
    currency: str = "AZN"
    exchange_rate: Decimal = Decimal("1.000000")
    notes: str | None = ""
    items: list[WaybillItemInput]

class WaybillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    waybill_number: str
    supplier_id: int
    supplier_name: str | None = None
    subtotal: Decimal
    edv_rate: Decimal = Decimal("18.00")
    edv_amount: Decimal
    total: Decimal
    currency: str = "AZN"
    exchange_rate: Decimal = Decimal("1.000000")
    notes: str | None = None
    created_at: datetime | None = None
    items: list[WaybillItemResponse] = []

class WaybillListResponse(BaseModel):
    items: list[WaybillResponse]

# --- Currency Schemas ---
class CurrencyRatesResponse(BaseModel):
    rates: dict[str, Decimal]
    source: str
    fetched_at: str | None = None

class CurrencySyncResponse(BaseModel):
    rates: dict[str, Decimal]
    source: str
    cached_at: str | None = None

from fastapi import APIRouter, Depends, HTTPException, status
import psycopg2.errors
from ..dependencies import get_inventory_service
from ..services.inventory import InventoryService, InsufficientStockError
from ..models import (
    IngredientCreate,
    IngredientUpdate,
    IngredientResponse,
    IngredientListResponse,
    StockAdjustRequest
)

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

@router.get("", response_model=IngredientListResponse)
def list_ingredients(service: InventoryService = Depends(get_inventory_service)):
    items = service.list_all()
    return {"items": items}

@router.get("/low-stock", response_model=IngredientListResponse)
def get_low_stock(service: InventoryService = Depends(get_inventory_service)):
    items = service.get_low_stock()
    return {"items": items}

@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: int, service: InventoryService = Depends(get_inventory_service)):
    item = service.get_by_id(ingredient_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Ingredient with ID {ingredient_id} not found", "code": "NOT_FOUND"}
        )
    return item

@router.post("", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: IngredientCreate, service: InventoryService = Depends(get_inventory_service)):
    try:
        item = service.create(
            name=payload.name,
            unit=payload.unit,
            quantity=payload.quantity,
            min_stock=payload.min_stock,
            unit_price=payload.unit_price,
            supplier_id=payload.supplier_id
        )
        return item
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Ingredient with name '{payload.name}' already exists", "code": "CONFLICT"}
        )
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Supplier with ID {payload.supplier_id} does not exist", "code": "VALIDATION_ERROR"}
        )

@router.put("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        updated = service.update(
            ingredient_id=ingredient_id,
            name=payload.name,
            unit=payload.unit,
            quantity=payload.quantity,
            min_stock=payload.min_stock,
            unit_price=payload.unit_price,
            supplier_id=payload.supplier_id
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Ingredient with ID {ingredient_id} not found", "code": "NOT_FOUND"}
            )
        return updated
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Ingredient name '{payload.name}' is already taken", "code": "CONFLICT"}
        )
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Supplier with ID {payload.supplier_id} does not exist", "code": "VALIDATION_ERROR"}
        )

@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, service: InventoryService = Depends(get_inventory_service)):
    try:
        deleted = service.delete(ingredient_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Ingredient with ID {ingredient_id} not found", "code": "NOT_FOUND"}
            )
        return None
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": f"Cannot delete ingredient ID {ingredient_id}: it is referenced in recipes or waybills",
                "code": "CONFLICT"
            }
        )

@router.post("/{ingredient_id}/adjust-stock", response_model=IngredientResponse)
def adjust_stock(
    ingredient_id: int,
    payload: StockAdjustRequest,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        updated = service.adjust_stock(ingredient_id, payload.delta)
        return updated
    except InsufficientStockError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": str(err),
                "code": "INSUFFICIENT_STOCK",
                "details": err.details
            }
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": str(err), "code": "NOT_FOUND"}
        )

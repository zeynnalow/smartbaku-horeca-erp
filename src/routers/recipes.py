from fastapi import APIRouter, Depends, HTTPException, status
import psycopg2.errors
from ..dependencies import get_recipe_engine
from ..services.recipe import RecipeEngine
from ..services.inventory import InsufficientStockError
from ..models import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeListResponse,
    RecipeCheckRequest,
    RecipeCheckResponse,
    RecipeCookRequest,
    RecipeCookResponse
)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

@router.get("", response_model=RecipeListResponse)
def list_recipes(engine: RecipeEngine = Depends(get_recipe_engine)):
    items = engine.list_all()
    return {"items": items}

@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, engine: RecipeEngine = Depends(get_recipe_engine)):
    item = engine.get_by_id(recipe_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Recipe with ID {recipe_id} not found", "code": "NOT_FOUND"}
        )
    return item

@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(payload: RecipeCreate, engine: RecipeEngine = Depends(get_recipe_engine)):
    try:
        item = engine.create(
            name=payload.name,
            category=payload.category,
            selling_price=payload.selling_price,
            items=payload.items
        )
        return item
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Recipe with name '{payload.name}' already exists", "code": "CONFLICT"}
        )
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "One or more ingredients do not exist", "code": "VALIDATION_ERROR"}
        )

@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    engine: RecipeEngine = Depends(get_recipe_engine)
):
    try:
        updated = engine.update(
            recipe_id=recipe_id,
            name=payload.name,
            category=payload.category,
            selling_price=payload.selling_price,
            is_active=payload.is_active,
            items=payload.items
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Recipe with ID {recipe_id} not found", "code": "NOT_FOUND"}
            )
        return updated
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Recipe name '{payload.name}' is already taken", "code": "CONFLICT"}
        )
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "One or more ingredients do not exist", "code": "VALIDATION_ERROR"}
        )

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, engine: RecipeEngine = Depends(get_recipe_engine)):
    deleted = engine.delete(recipe_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Recipe with ID {recipe_id} not found", "code": "NOT_FOUND"}
        )
    return None

@router.post("/{recipe_id}/check", response_model=RecipeCheckResponse)
def check_recipe_availability(
    recipe_id: int,
    payload: RecipeCheckRequest,
    engine: RecipeEngine = Depends(get_recipe_engine)
):
    try:
        result = engine.check_availability(recipe_id, servings=payload.servings)
        return result
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": str(err), "code": "NOT_FOUND"}
        )

@router.post("/{recipe_id}/cook", response_model=RecipeCookResponse)
def cook_recipe(
    recipe_id: int,
    payload: RecipeCookRequest,
    engine: RecipeEngine = Depends(get_recipe_engine)
):
    try:
        result = engine.cook(recipe_id, servings=payload.servings)
        return result
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(err), "code": "BAD_REQUEST"}
        )

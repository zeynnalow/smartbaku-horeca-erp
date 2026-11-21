from fastapi import Request
from .config import settings
from .database import DatabaseManager
from .services.inventory import InventoryService
from .services.recipe import RecipeEngine
from .services.waybill import WaybillGenerator
from .services.currency import CurrencySyncService
from .services.supplier import SupplierService

def get_db(request: Request) -> DatabaseManager:
    return request.app.state.db

def get_inventory_service(request: Request) -> InventoryService:
    return InventoryService(request.app.state.db)

def get_recipe_engine(request: Request) -> RecipeEngine:
    return RecipeEngine(request.app.state.db)

def get_waybill_generator(request: Request) -> WaybillGenerator:
    return WaybillGenerator(request.app.state.db)

def get_currency_service(request: Request) -> CurrencySyncService:
    return CurrencySyncService(request.app.state.db, settings)

def get_supplier_service(request: Request) -> SupplierService:
    return SupplierService(request.app.state.db)

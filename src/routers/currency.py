from fastapi import APIRouter, Depends
from ..dependencies import get_currency_service
from ..services.currency import CurrencySyncService
from ..models import (
    CurrencyRatesResponse,
    CurrencySyncResponse
)

router = APIRouter(prefix="/api/currency", tags=["currency"])

@router.get("/rates", response_model=CurrencyRatesResponse)
def get_rates(service: CurrencySyncService = Depends(get_currency_service)):
    data = service.get_latest_rates()
    return data

@router.post("/sync", response_model=CurrencySyncResponse)
def sync_rates(service: CurrencySyncService = Depends(get_currency_service)):
    data = service.sync()
    return data

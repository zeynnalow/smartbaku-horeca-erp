from fastapi import APIRouter, Depends, HTTPException, status
import psycopg2.errors
from ..dependencies import get_supplier_service
from ..services.supplier import SupplierService
from ..models import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

@router.get("", response_model=SupplierListResponse)
def list_suppliers(service: SupplierService = Depends(get_supplier_service)):
    items = service.list_all()
    return {"items": items}

@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, service: SupplierService = Depends(get_supplier_service)):
    item = service.get_by_id(supplier_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Supplier with ID {supplier_id} not found", "code": "NOT_FOUND"}
        )
    return item

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, service: SupplierService = Depends(get_supplier_service)):
    try:
        item = service.create(
            name=payload.name,
            voen=payload.voen,
            phone=payload.phone,
            email=payload.email,
            address=payload.address
        )
        return item
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Supplier with VÖEN '{payload.voen}' already exists", "code": "CONFLICT"}
        )

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    service: SupplierService = Depends(get_supplier_service)
):
    try:
        updated = service.update(
            supplier_id=supplier_id,
            name=payload.name,
            voen=payload.voen,
            phone=payload.phone,
            email=payload.email,
            address=payload.address
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Supplier with ID {supplier_id} not found", "code": "NOT_FOUND"}
            )
        return updated
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": f"Supplier VÖEN '{payload.voen}' is already used by another supplier", "code": "CONFLICT"}
        )

@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, service: SupplierService = Depends(get_supplier_service)):
    try:
        deleted = service.delete(supplier_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Supplier with ID {supplier_id} not found", "code": "NOT_FOUND"}
            )
        return None
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": f"Cannot delete supplier ID {supplier_id}: it is referenced in waybills or ingredients",
                "code": "CONFLICT"
            }
        )

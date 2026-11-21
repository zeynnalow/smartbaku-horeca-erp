from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Calculate templates path relative to this file or root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["pages"])

@router.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_tab": "dashboard"
    })

@router.get("/inventory", response_class=HTMLResponse)
async def page_inventory(request: Request):
    return templates.TemplateResponse("inventory.html", {
        "request": request,
        "active_tab": "inventory"
    })

@router.get("/recipes", response_class=HTMLResponse)
async def page_recipes(request: Request):
    return templates.TemplateResponse("recipes.html", {
        "request": request,
        "active_tab": "recipes"
    })

@router.get("/suppliers", response_class=HTMLResponse)
async def page_suppliers(request: Request):
    return templates.TemplateResponse("suppliers.html", {
        "request": request,
        "active_tab": "suppliers"
    })

@router.get("/waybills", response_class=HTMLResponse)
async def page_waybills(request: Request):
    return templates.TemplateResponse("waybills.html", {
        "request": request,
        "active_tab": "waybills"
    })

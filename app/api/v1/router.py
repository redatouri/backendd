from fastapi import APIRouter

from app.api.v1 import admin, auth, categories, cross_sells, orders, products

api_router = APIRouter()
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(cross_sells.router)
api_router.include_router(orders.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)

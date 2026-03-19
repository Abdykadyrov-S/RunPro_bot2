from aiogram import Dispatcher

from handlers import start, loads
from services import admin
from handlers.gross import router as gross_router
from db.export import export_router

def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(loads.router)
    dp.include_router(admin.router)
    dp.include_router(gross_router)
    dp.include_router(export_router)
    return dp

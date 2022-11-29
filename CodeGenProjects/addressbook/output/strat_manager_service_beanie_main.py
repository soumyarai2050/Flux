import os
from fastapi import FastAPI
from strat_manager_service_beanie_routes import strat_manager_service_API_router
from strat_manager_service_beanie_model import OrderLimits, PortfolioLimits, PortfolioStatus, PairStrat, StratCollection, UILayout
from strat_manager_service_beanie_database import init_db


strat_manager_service_app = FastAPI(title='CRUD API of strat_manager_service')


async def init_max_id_handler(document):
    max_val = await document.find_all().max("_id")
    document.init_max_id(int(max_val) if max_val is not None else 0)


@strat_manager_service_app.on_event("startup")
async def connect():
    await init_db()
    await init_max_id_handler(OrderLimits)
    await init_max_id_handler(PortfolioLimits)
    await init_max_id_handler(PortfolioStatus)
    await init_max_id_handler(PairStrat)
    await init_max_id_handler(StratCollection)
    await init_max_id_handler(UILayout)


if os.getenv('DEBUG'):
    from fastapi.middleware.cors import CORSMiddleware

    origins = ['*']
    strat_manager_service_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

strat_manager_service_app.include_router(strat_manager_service_API_router, prefix="/addressbook")
from fastapi.staticfiles import StaticFiles

strat_manager_service_app.mount('/static', StaticFiles(directory='static'), name='static')


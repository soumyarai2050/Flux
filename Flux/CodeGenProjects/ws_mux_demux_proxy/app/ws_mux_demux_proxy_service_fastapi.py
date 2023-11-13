import os
from fastapi import FastAPI
# from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
# from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_beanie_database import init_db
#
# # Below imports are to initialize routes before launching server
# from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import *
from Flux.CodeGenProjects.ws_mux_demux_proxy.app.ws_mux_demux_proxy_service_ws_routes import *


ui_proxy_service_app = FastAPI(title='CRUD API of UI Proxy')


# async def init_max_id_handler(document):
#     max_val = await document.find_all().max("_id")
#     document.init_max_id(int(max_val) if max_val is not None else 0)


# @strat_executor_service_app.on_event("startup")
# async def connect():
#     await init_db()
#     await init_max_id_handler(OrderJournal)
#     await init_max_id_handler(OrderSnapshot)
#     await init_max_id_handler(SymbolSideSnapshot)
#     await init_max_id_handler(FillsJournal)
#     await init_max_id_handler(StratBrief)
#     await init_max_id_handler(StratStatus)
#     await init_max_id_handler(StratLimits)
#     await init_max_id_handler(NewOrder)
#     await init_max_id_handler(CancelOrder)
#     await init_max_id_handler(UILayout)
#     await init_max_id_handler(SymbolOverview)
#     await init_max_id_handler(CommandNControl)
#     await init_max_id_handler(TopOfBook)
#     await init_max_id_handler(MarketDepth)
#     await init_max_id_handler(LastTrade)
#     port = os.getenv("PORT")
#     if port is None or len(port) == 0:
#         err_str = "Can not find PORT env var for fastapi db init"
#         logging.exception(err_str)
#         raise Exception(err_str)
#     os.environ[f"strat_executor_{port}"] = "1"  # indicator flag to tell callback override that service is up


# host = os.environ.get("HOST")
# if host is None or len(host) == 0:
#     err_str = "Couldn't find 'HOST' key in data/config.yaml of current project"
#     logging.error(err_str)
#     raise Exception(err_str)
#
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
#
# cors_dict: Dict[str, Any] = dict()
# cors_dict["allow_methods"] = ["*"]
# cors_dict["allow_headers"] = ["*"]
# if os.getenv('DEBUG'):
#     cors_dict["allow_origins"] = ["*"]
#     cors_dict["allow_credentials"] = True
# else:
#     host_pattern = host.replace(".", "\.")
#     allow_origin_patten = rf"https?://{host_pattern}(:\d+)?"
#     cors_dict["allow_origin_regex"] = allow_origin_patten
# strat_executor_service_app.add_middleware(
#     CORSMiddleware,
#      **cors_dict)
#
ui_proxy_service_app.include_router(ui_proxy_service_API_router, prefix="/ui_proxy")
# strat_executor_service_app.mount('/static', StaticFiles(directory=f'{host}/static'), name='static')


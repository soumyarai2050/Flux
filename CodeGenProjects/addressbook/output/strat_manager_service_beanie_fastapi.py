import os
import uvicorn


if __name__ == "__main__":
    if reload_env := os.getenv("RELOAD"):
        reload_status: bool = True if reload_env.lower() == "true" else False
    else:
        reload_status: bool = False
    uvicorn.run(reload=reload_status, app="strat_manager_service_beanie_main:strat_manager_service_app")

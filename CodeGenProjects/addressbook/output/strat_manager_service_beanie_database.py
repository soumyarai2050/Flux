from beanie import init_beanie
import motor
import motor.motor_asyncio
from strat_manager_service_beanie_model import OrderLimits, PortfolioLimits, PortfolioStatus, PairStrat, StratCollection, UILayout


async def init_db():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
              database=client.addressbook,
              document_models=[OrderLimits, PortfolioLimits, PortfolioStatus, PairStrat, StratCollection, UILayout]
              )

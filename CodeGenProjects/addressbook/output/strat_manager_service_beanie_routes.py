from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
import logging
from typing import List
from strat_manager_service_beanie_model import OrderLimits, PortfolioLimits, PortfolioStatus, PairStrat, StratCollection, UILayout
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from beanie import PydanticObjectId


id_not_found = DefaultWebResponse(brief="Id not Found")
del_success = DefaultWebResponse(brief="Deletion Successful")
no_match_found = DefaultWebResponse(brief="No Match Found")

strat_manager_service_API_router = APIRouter()


@strat_manager_service_API_router.get("/get-all-order_limits/", response_model=List[OrderLimits], status_code=200)
async def get_all_order_limits() -> List[OrderLimits]:
    """
    Get All OrderLimits
    """
    try:
        order_limits_list = await OrderLimits.find_all().to_list()
        return order_limits_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-order_limits", response_model=OrderLimits, status_code=201)
async def create_order_limits(order_limits: OrderLimits) -> OrderLimits:
    """
    Create Doc for OrderLimits
    """
    try:
        await order_limits.create()
        return order_limits
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-order_limits/{order_limits_id}", response_model=OrderLimits, status_code=200)
async def read_order_limits(order_limits_id: int) -> OrderLimits:
    """
    Read Doc for OrderLimits
    """
    try:
        fetched_order_limits = await OrderLimits.get(order_limits_id)
        if not fetched_order_limits:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_order_limits
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-order_limits/", response_model=OrderLimits, status_code=200)
async def update_order_limits(order_limits_updated: OrderLimits) -> OrderLimits:
    """
    Update Doc for OrderLimits
    """
    try:
        req_dict_without_none_val = {k: v for k, v in order_limits_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await OrderLimits.get(order_limits_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-order_limits/{order_limits_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_order_limits(order_limits_id: int) -> DefaultWebResponse:
    """
    Delete Doc for OrderLimits
    """
    try:
        record = await OrderLimits.get(order_limits_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-all-portfolio_limits/", response_model=List[PortfolioLimits], status_code=200)
async def get_all_portfolio_limits() -> List[PortfolioLimits]:
    """
    Get All PortfolioLimits
    """
    try:
        portfolio_limits_list = await PortfolioLimits.find_all().to_list()
        return portfolio_limits_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-portfolio_limits", response_model=PortfolioLimits, status_code=201)
async def create_portfolio_limits(portfolio_limits: PortfolioLimits) -> PortfolioLimits:
    """
    Create Doc for PortfolioLimits
    """
    try:
        await portfolio_limits.create()
        return portfolio_limits
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-portfolio_limits/{portfolio_limits_id}", response_model=PortfolioLimits, status_code=200)
async def read_portfolio_limits(portfolio_limits_id: int) -> PortfolioLimits:
    """
    Read Doc for PortfolioLimits
    """
    try:
        fetched_portfolio_limits = await PortfolioLimits.get(portfolio_limits_id)
        if not fetched_portfolio_limits:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_portfolio_limits
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-portfolio_limits/", response_model=PortfolioLimits, status_code=200)
async def update_portfolio_limits(portfolio_limits_updated: PortfolioLimits) -> PortfolioLimits:
    """
    Update Doc for PortfolioLimits
    """
    try:
        req_dict_without_none_val = {k: v for k, v in portfolio_limits_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await PortfolioLimits.get(portfolio_limits_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-portfolio_limits/{portfolio_limits_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_portfolio_limits(portfolio_limits_id: int) -> DefaultWebResponse:
    """
    Delete Doc for PortfolioLimits
    """
    try:
        record = await PortfolioLimits.get(portfolio_limits_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-all-portfolio_status/", response_model=List[PortfolioStatus], status_code=200)
async def get_all_portfolio_status() -> List[PortfolioStatus]:
    """
    Get All PortfolioStatus
    """
    try:
        portfolio_status_list = await PortfolioStatus.find_all().to_list()
        return portfolio_status_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-portfolio_status", response_model=PortfolioStatus, status_code=201)
async def create_portfolio_status(portfolio_status: PortfolioStatus) -> PortfolioStatus:
    """
    Create Doc for PortfolioStatus
    """
    try:
        await portfolio_status.create()
        return portfolio_status
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-portfolio_status/{portfolio_status_id}", response_model=PortfolioStatus, status_code=200)
async def read_portfolio_status(portfolio_status_id: int) -> PortfolioStatus:
    """
    Read Doc for PortfolioStatus
    """
    try:
        fetched_portfolio_status = await PortfolioStatus.get(portfolio_status_id)
        if not fetched_portfolio_status:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_portfolio_status
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-portfolio_status/", response_model=PortfolioStatus, status_code=200)
async def update_portfolio_status(portfolio_status_updated: PortfolioStatus) -> PortfolioStatus:
    """
    Update Doc for PortfolioStatus
    """
    try:
        req_dict_without_none_val = {k: v for k, v in portfolio_status_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await PortfolioStatus.get(portfolio_status_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-portfolio_status/{portfolio_status_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_portfolio_status(portfolio_status_id: int) -> DefaultWebResponse:
    """
    Delete Doc for PortfolioStatus
    """
    try:
        record = await PortfolioStatus.get(portfolio_status_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-all-pair_strat/", response_model=List[PairStrat], status_code=200)
async def get_all_pair_strat() -> List[PairStrat]:
    """
    Get All PairStrat
    """
    try:
        pair_strat_list = await PairStrat.find_all().to_list()
        return pair_strat_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-pair_strat", response_model=PairStrat, status_code=201)
async def create_pair_strat(pair_strat: PairStrat) -> PairStrat:
    """
    Create Doc for PairStrat
    """
    try:
        await pair_strat.create()
        return pair_strat
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-pair_strat/{pair_strat_id}", response_model=PairStrat, status_code=200)
async def read_pair_strat(pair_strat_id: int) -> PairStrat:
    """
    Read Doc for PairStrat
    """
    try:
        fetched_pair_strat = await PairStrat.get(pair_strat_id)
        if not fetched_pair_strat:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_pair_strat
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-pair_strat/", response_model=PairStrat, status_code=200)
async def update_pair_strat(pair_strat_updated: PairStrat) -> PairStrat:
    """
    Update Doc for PairStrat
    """
    try:
        req_dict_without_none_val = {k: v for k, v in pair_strat_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await PairStrat.get(pair_strat_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-pair_strat/{pair_strat_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_pair_strat(pair_strat_id: int) -> DefaultWebResponse:
    """
    Delete Doc for PairStrat
    """
    try:
        record = await PairStrat.get(pair_strat_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-all-strat_collection/", response_model=List[StratCollection], status_code=200)
async def get_all_strat_collection() -> List[StratCollection]:
    """
    Get All StratCollection
    """
    try:
        strat_collection_list = await StratCollection.find_all().to_list()
        return strat_collection_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-strat_collection", response_model=StratCollection, status_code=201)
async def create_strat_collection(strat_collection: StratCollection) -> StratCollection:
    """
    Create Doc for StratCollection
    """
    try:
        await strat_collection.create()
        return strat_collection
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-strat_collection/{strat_collection_id}", response_model=StratCollection, status_code=200)
async def read_strat_collection(strat_collection_id: int) -> StratCollection:
    """
    Read Doc for StratCollection
    """
    try:
        fetched_strat_collection = await StratCollection.get(strat_collection_id)
        if not fetched_strat_collection:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_strat_collection
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-strat_collection/", response_model=StratCollection, status_code=200)
async def update_strat_collection(strat_collection_updated: StratCollection) -> StratCollection:
    """
    Update Doc for StratCollection
    """
    try:
        req_dict_without_none_val = {k: v for k, v in strat_collection_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await StratCollection.get(strat_collection_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-strat_collection/{strat_collection_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_strat_collection(strat_collection_id: int) -> DefaultWebResponse:
    """
    Delete Doc for StratCollection
    """
    try:
        record = await StratCollection.get(strat_collection_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-all-ui_layout/", response_model=List[UILayout], status_code=200)
async def get_all_ui_layout() -> List[UILayout]:
    """
    Get All UILayout
    """
    try:
        ui_layout_list = await UILayout.find_all().to_list()
        return ui_layout_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.post("/create-ui_layout", response_model=UILayout, status_code=201)
async def create_ui_layout(ui_layout: UILayout) -> UILayout:
    """
    Create Doc for UILayout
    """
    try:
        await ui_layout.create()
        return ui_layout
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-ui_layout/{ui_layout_id}", response_model=UILayout, status_code=200)
async def read_ui_layout(ui_layout_id: int) -> UILayout:
    """
    Read Doc for UILayout
    """
    try:
        fetched_ui_layout = await UILayout.get(ui_layout_id)
        if not fetched_ui_layout:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            return fetched_ui_layout
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.put("/put-ui_layout/", response_model=UILayout, status_code=200)
async def update_ui_layout(ui_layout_updated: UILayout) -> UILayout:
    """
    Update Doc for UILayout
    """
    try:
        req_dict_without_none_val = {k: v for k, v in ui_layout_updated.dict().items() if v is not None}
        update_query = {"$set": req_dict_without_none_val.items()}
        review = await UILayout.get(ui_layout_updated.id)
        if not review:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await review.update(update_query)
            return review
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.delete("/delete-ui_layout/{ui_layout_id}", response_model=DefaultWebResponse, status_code=200)
async def delete_ui_layout(ui_layout_id: int) -> DefaultWebResponse:
    """
    Delete Doc for UILayout
    """
    try:
        record = await UILayout.get(ui_layout_id)
        if not record:
            logging.exception(id_not_found.brief)
            raise HTTPException(status_code=404, detail=id_not_found.brief)
        else:
            await record.delete()
            return del_success
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@strat_manager_service_API_router.get("/get-ui_layout-from-profile_id/{profile_id}", response_model=List[UILayout], status_code=200)
async def get_ui_layout_from_profile_id(profile_id: str) -> List[UILayout]:
    try:
        fetched_ui_layout_list = await UILayout.find(UILayout.profile_id == profile_id).to_list()
        if not fetched_ui_layout_list:
            logging.exception(no_match_found.brief)
            raise HTTPException(status_code=404, detail=no_match_found.brief)
        else:
            return fetched_ui_layout_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


templates = Jinja2Templates(directory='templates')

@strat_manager_service_API_router.get('/')
async def serve_spa(request: Request):
    return templates.TemplateResponse('static/index.html', {'request': request})

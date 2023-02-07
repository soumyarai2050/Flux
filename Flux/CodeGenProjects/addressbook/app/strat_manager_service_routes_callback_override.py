# system imports
from typing import List, Type

# third-party package imports
import logging
from pendulum import DateTime
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import \
    StratOrderJournal, StratOrderSnapshot, StratOrderSnapshotOptional, PairStrat, StratFillsJournal, TestSample, \
    PairStratOptional, StratStatus, PortfolioLimits, StratState, \
    StratLimits, Side, OrderEventType, PortfolioStatusOptional, OrderStatusType
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback


class StratManagerServiceRoutesCallbackOverride(StratManagerServiceRoutesCallback):

    def __init__(self):
        super().__init__()

    # Example 0 of 5: pre- and post-launch server
    def app_launch_pre(self):
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def _update_portfolio_status_from_order_journal(self, strat_order_journal_obj: StratOrderJournal,
                                                          strat_order_snapshot_obj: StratOrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_http, underlying_partial_update_portfolio_status_http

        portfolio_status_objs = await underlying_read_portfolio_status_http()
        if len(portfolio_status_objs) == 1:
            portfolio_status_obj = portfolio_status_objs[0]
            match strat_order_journal_obj.order.side:
                case Side.BUY:
                    match strat_order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            portfolio_status_obj.overall_buy_notional += \
                                strat_order_journal_obj.order.px * strat_order_journal_obj.order.qty
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty
                            portfolio_status_obj.overall_buy_notional -= \
                                (strat_order_snapshot_obj.order_brief.px * total_buy_unfilled_qty)
                case Side.SELL:
                    match strat_order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            portfolio_status_obj.overall_sell_notional += \
                                strat_order_journal_obj.order.px * strat_order_journal_obj.order.qty
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty
                            portfolio_status_obj.overall_sell_notional -= \
                                (strat_order_snapshot_obj.order_brief.px * total_sell_unfilled_qty)
                case other:
                    err_str = f"Unsupported Side Type {other} received in order journal {strat_order_journal_obj} " \
                              f"while updating strat_status"
                    logging.exception(err_str)
                    raise Exception(err_str)
            updated_portfolio_status = PortfolioStatusOptional(
                _id=portfolio_status_obj.id,
                overall_buy_notional=portfolio_status_obj.overall_buy_notional,
                overall_sell_notional=portfolio_status_obj.overall_sell_notional
            )
            await underlying_partial_update_portfolio_status_http(updated_portfolio_status)

        else:
            if len(portfolio_status_objs) > 1:
                err_str = f"Portfolio Status collection should have only one document, received {portfolio_status_objs}"
                logging.exception(err_str)
                raise Exception(err_str)
            else:
                err_str = f"Received Empty Portfolio Status from db while updating order journal relate fields"
                logging.exception(err_str)
                raise Exception(err_str)

    async def _update_portfolio_status_from_fill_journal(self, strat_order_snapshot_obj: StratOrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_http, underlying_partial_update_portfolio_status_http

        portfolio_status_objs = await underlying_read_portfolio_status_http()
        if len(portfolio_status_objs) == 1:
            portfolio_status_obj = portfolio_status_objs[0]
            match strat_order_snapshot_obj.order_brief.side:
                case Side.BUY:
                    portfolio_status_obj.overall_buy_fill_notional += \
                        strat_order_snapshot_obj.last_update_fill_px * strat_order_snapshot_obj.last_update_fill_qty
                case Side.SELL:
                    portfolio_status_obj.overall_sell_fill_notional += \
                        strat_order_snapshot_obj.last_update_fill_px * strat_order_snapshot_obj.last_update_fill_qty
                case other:
                    err_str = f"Unsupported Side Type {other} received in order snapshot {strat_order_snapshot_obj} " \
                              f"while updating strat_status"
                    logging.exception(err_str)
                    raise Exception(err_str)
            updated_portfolio_status = PortfolioStatusOptional(
                _id=portfolio_status_obj.id,
                overall_buy_fill_notional=portfolio_status_obj.overall_buy_fill_notional,
                overall_sell_fill_notional=portfolio_status_obj.overall_sell_fill_notional
            )
            await underlying_partial_update_portfolio_status_http(updated_portfolio_status)
        else:
            if len(portfolio_status_objs) > 1:
                err_str = f"Portfolio Status collection should have only one document, received {portfolio_status_objs}"
                logging.exception(err_str)
                raise Exception(err_str)
            else:
                err_str = f"Received Empty Portfolio Status from db while updating order journal relate fields"
                logging.exception(err_str)
                raise Exception(err_str)

    async def _update_pair_strat_from_order_journal(self, strat_order_journal_obj: StratOrderJournal,
                                                    strat_order_snapshot: StratOrderSnapshot):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http, underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
        pair_strat_objs = await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json
                                                                (strat_order_journal_obj.order.security.sec_id))
        if len(pair_strat_objs) == 1:
            updated_strat_status_obj = pair_strat_objs[0].strat_status
            match strat_order_journal_obj.order.side:
                case Side.BUY:
                    match strat_order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            updated_strat_status_obj.total_buy_qty += strat_order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_buy_qty += strat_order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_buy_notional += \
                                strat_order_journal_obj.order.qty * strat_order_snapshot.order_brief.px
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = \
                                strat_order_snapshot.order_brief.qty - strat_order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_buy_qty -= total_buy_unfilled_qty
                            updated_strat_status_obj.total_open_buy_notional -= \
                                (total_buy_unfilled_qty * strat_order_snapshot.order_brief.px)
                            updated_strat_status_obj.total_cxl_buy_qty += strat_order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_buy_notional += \
                                strat_order_snapshot.cxled_qty * strat_order_snapshot.order_brief.px
                            updated_strat_status_obj.avg_cxl_buy_px = \
                                updated_strat_status_obj.total_cxl_buy_notional / updated_strat_status_obj.total_cxl_buy_qty
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - updated_strat_status_obj.total_cxl_sell_notional
                        case other:
                            err_str = f"Unsupported Order Event type {other}"
                            logging.exception(err_str)
                            raise Exception(err_str)
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_buy_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            updated_strat_status_obj.total_open_buy_notional / updated_strat_status_obj.total_open_buy_qty
                case Side.SELL:
                    match strat_order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            updated_strat_status_obj.total_sell_qty += strat_order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_qty += strat_order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_notional += \
                                strat_order_journal_obj.order.qty * strat_order_journal_obj.order.px
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                strat_order_snapshot.order_brief.qty - strat_order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_sell_qty -= total_sell_unfilled_qty
                            updated_strat_status_obj.total_open_sell_notional -= \
                                (total_sell_unfilled_qty * strat_order_snapshot.order_brief.px)
                            updated_strat_status_obj.total_cxl_sell_qty += strat_order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_sell_notional += \
                                strat_order_snapshot.cxled_qty * strat_order_snapshot.order_brief.px
                            updated_strat_status_obj.avg_cxl_sell_px = \
                                updated_strat_status_obj.total_cxl_sell_notional / updated_strat_status_obj.total_cxl_sell_qty
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - updated_strat_status_obj.total_cxl_sell_notional
                        case other:
                            err_str = f"Unsupported Order Event type {other}"
                            logging.exception(err_str)
                            raise Exception(err_str)
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            updated_strat_status_obj.total_open_sell_notional / updated_strat_status_obj.total_open_sell_qty
                case other:
                    err_str = f"Unsupported Side Type {other} received in order journal {strat_order_journal_obj} " \
                              f"while updating strat_status"
                    logging.exception(err_str)
                    raise Exception(err_str)
            updated_strat_status_obj.total_order_qty = \
                updated_strat_status_obj.total_buy_qty + updated_strat_status_obj.total_sell_qty
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_objs[0].id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            err_str = "Pair_strat can't have more than one obj with same symbol in pair_strat_params, " \
                      f"received - {pair_strat_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _check_state_and_get_order_snapshot_obj(self, strat_order_journal_obj: StratOrderJournal, # NOQA
                                                      expected_status_list: List[str],
                                                      received_journal_event: str) -> StratOrderSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json
        strat_order_snapshot_objs = \
            await underlying_read_strat_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                strat_order_journal_obj.order.order_id))
        if len(strat_order_snapshot_objs) == 1:
            strat_order_snapshot_obj = strat_order_snapshot_objs[0]
            if strat_order_snapshot_obj.order_status in expected_status_list:
                return strat_order_snapshot_obj
            else:
                err_str = f"strat_order_journal - {strat_order_journal_obj} received to update status of " \
                          f"strat_order_snapshot - {strat_order_snapshot_obj}, but strat_order_snapshot " \
                          f"doesn't contain any order_status of list {expected_status_list}"
                logging.exception(err_str)
                raise Exception(err_str)
        elif len(strat_order_snapshot_objs) == 0:
            err_str = f"Could not find any order for {received_journal_event} status - {strat_order_journal_obj}"
            logging.exception(err_str)
            raise Exception(err_str)
        else:
            err_str = f"Match should return list of only one strat_order_snapshot obj, " \
                      f"returned {strat_order_snapshot_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _update_cxl_fields_in_snapshot(self, strat_order_snapshot: StratOrderSnapshot) -> StratOrderSnapshot:
        """
        Updated cxl fields of order snapshot
        """
        strat_order_snapshot.cxled_qty = strat_order_snapshot.order_brief.qty - strat_order_snapshot.filled_qty
        strat_order_snapshot.cxled_notional = strat_order_snapshot.cxled_qty * strat_order_snapshot.order_brief.px
        strat_order_snapshot.avg_cxled_px = strat_order_snapshot.cxled_notional / strat_order_snapshot.cxled_qty
        return strat_order_snapshot

    async def _update_order_journal_in_snapshot(self, strat_order_journal_obj: StratOrderJournal):
        match strat_order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    create_strat_order_snapshot_http
                strat_order_snapshot_obj = StratOrderSnapshot(_id=StratOrderSnapshot.next_id(),
                                                              order_brief=strat_order_journal_obj.order,
                                                              filled_qty=0, avg_fill_px=0,
                                                              fill_notional=0,
                                                              cxled_qty=0,
                                                              avg_cxled_px=0,
                                                              cxled_notional=0,
                                                              last_update_fill_qty=0,
                                                              last_update_fill_px=0,
                                                              last_update_date_time=
                                                              strat_order_journal_obj.order_event_date_time,
                                                              order_status=OrderStatusType.OE_UNACK)
                await create_strat_order_snapshot_http(strat_order_snapshot_obj)
                await self._update_pair_strat_from_order_journal(strat_order_journal_obj, strat_order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    strat_order_journal_obj, strat_order_snapshot_obj)

            case OrderEventType.OE_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_strat_order_snapshot_http
                strat_order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(strat_order_journal_obj,
                                                                       [OrderStatusType.OE_UNACK],
                                                                       OrderEventType.OE_ACK)
                await underlying_partial_update_strat_order_snapshot_http(
                    StratOrderSnapshotOptional(_id=strat_order_snapshot_obj.id,
                                               last_update_date_time=strat_order_journal_obj.order_event_date_time,
                                               order_status=OrderStatusType.OE_ACKED))
            case OrderEventType.OE_CXL:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_strat_order_snapshot_http
                strat_order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        strat_order_journal_obj, [OrderStatusType.OE_ACKED], OrderEventType.OE_CXL)
                await underlying_partial_update_strat_order_snapshot_http(
                    StratOrderSnapshotOptional(_id=strat_order_snapshot_obj.id,
                                               last_update_date_time=strat_order_journal_obj.order_event_date_time,
                                               order_status=OrderStatusType.OE_CXL_UNACK))
            case OrderEventType.OE_CXL_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_strat_order_snapshot_http
                strat_order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        strat_order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED],
                        OrderEventType.OE_CXL_ACK)
                if strat_order_journal_obj.order.text:
                    updated_order_brief = \
                        strat_order_snapshot_obj.order_brief.text.extend(strat_order_journal_obj.order.text)
                else:
                    # If no text received then sending same list of text present in snapshot
                    updated_order_brief = strat_order_snapshot_obj.order_brief.text
                cxled_qty = strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty
                cxled_notional = strat_order_snapshot_obj.cxled_qty * strat_order_snapshot_obj.order_brief.px
                avg_cxled_px = cxled_notional / cxled_qty
                strat_order_snapshot_obj = await underlying_partial_update_strat_order_snapshot_http(
                    StratOrderSnapshotOptional(_id=strat_order_snapshot_obj.id,
                                               order_brief=updated_order_brief,
                                               cxled_qty=cxled_qty,
                                               cxled_notional=cxled_notional,
                                               avg_cxled_px=avg_cxled_px,
                                               last_update_date_time=strat_order_journal_obj.order_event_date_time,
                                               order_status=OrderStatusType.OE_DOD))
                await self._update_pair_strat_from_order_journal(
                    strat_order_journal_obj, strat_order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    strat_order_journal_obj, strat_order_snapshot_obj)
            case OrderEventType.OE_CXL_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_strat_order_snapshot_http
                strat_order_snapshot_obj = await self._check_state_and_get_order_snapshot_obj(
                    strat_order_journal_obj, [OrderStatusType.OE_CXL_UNACK], OrderEventType.OE_CXL_REJ)
                if strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty > 0:
                    order_status = OrderStatusType.OE_ACKED
                elif strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty > 0:
                    order_status = OrderStatusType.OE_OVER_FILLED
                else:
                    order_status = OrderStatusType.OE_FILLED
                await underlying_partial_update_strat_order_snapshot_http(
                    StratOrderSnapshotOptional(_id=strat_order_snapshot_obj.id,
                                               last_update_date_time=strat_order_journal_obj.order_event_date_time,
                                               order_status=order_status))
            case OrderEventType.OE_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_strat_order_snapshot_http
                strat_order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        strat_order_journal_obj, [OrderStatusType.OE_ACKED], OrderEventType.OE_REJ)
                updated_order_brief = \
                    strat_order_snapshot_obj.order_brief.text.extend(strat_order_journal_obj.order.text)
                cxled_qty = strat_order_snapshot_obj.order_brief.qty - strat_order_snapshot_obj.filled_qty
                cxled_notional = strat_order_snapshot_obj.cxled_qty * strat_order_snapshot_obj.order_brief.px
                avg_cxled_px = cxled_notional / cxled_qty
                strat_order_snapshot_obj = await underlying_partial_update_strat_order_snapshot_http(
                    StratOrderSnapshotOptional(
                        _id=strat_order_snapshot_obj.id,
                        order_brief=updated_order_brief,
                        cxled_qty=cxled_qty,
                        cxled_notional=cxled_notional,
                        avg_cxled_px=avg_cxled_px,
                        last_update_date_time=strat_order_journal_obj.order_event_date_time,
                        order_status=OrderStatusType.OE_DOD))
                await self._update_pair_strat_from_order_journal(
                    strat_order_journal_obj, strat_order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    strat_order_journal_obj, strat_order_snapshot_obj)
            case other:
                err_str = f"Unsupported Order event - {other} in strat_order_journal object - {strat_order_journal_obj}"
                logging.exception(err_str)
                raise Exception(err_str)

    async def create_strat_order_journal_pre(self, strat_order_journal_obj: StratOrderJournal):
        # updating order notional in order journal obj
        strat_order_journal_obj.order.order_notional = strat_order_journal_obj.order.px * strat_order_journal_obj.order.qty

    async def create_strat_order_journal_post(self, strat_order_journal_obj: StratOrderJournal):
        with StratOrderSnapshot.reentrant_lock:
            with PairStrat.reentrant_lock:
                await self._update_order_journal_in_snapshot(strat_order_journal_obj)

    async def _update_pair_strat_from_fill_journal(self, strat_order_snapshot_obj: StratOrderSnapshot):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http, underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
        pair_strat_objs = await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json
                                                                (strat_order_snapshot_obj.order_brief.security.sec_id))
        if len(pair_strat_objs) == 1:
            updated_strat_status_obj = pair_strat_objs[0].strat_status
            match strat_order_snapshot_obj.order_brief.side:
                case Side.BUY:
                    updated_strat_status_obj.total_open_buy_qty -= strat_order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_open_buy_notional -= \
                        strat_order_snapshot_obj.last_update_fill_qty * strat_order_snapshot_obj.order_brief.px
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            updated_strat_status_obj.total_open_buy_notional / updated_strat_status_obj.total_open_buy_qty
                    updated_strat_status_obj.total_fill_buy_qty += strat_order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_buy_notional += \
                        strat_order_snapshot_obj.last_update_fill_qty * strat_order_snapshot_obj.last_update_fill_px
                    updated_strat_status_obj.avg_fill_buy_px = \
                        updated_strat_status_obj.total_fill_buy_notional / updated_strat_status_obj.total_fill_buy_qty
                case Side.SELL:
                    updated_strat_status_obj.total_open_sell_qty -= strat_order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_open_sell_notional -= \
                        (strat_order_snapshot_obj.last_update_fill_qty * strat_order_snapshot_obj.last_update_fill_px)
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            updated_strat_status_obj.total_open_sell_notional / updated_strat_status_obj.total_open_sell_qty
                    updated_strat_status_obj.total_fill_sell_qty += strat_order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_sell_notional += \
                        strat_order_snapshot_obj.last_update_fill_qty * strat_order_snapshot_obj.last_update_fill_px
                    updated_strat_status_obj.avg_fill_sell_px = \
                        updated_strat_status_obj.total_fill_sell_notional / updated_strat_status_obj.total_fill_sell_qty
                case other:
                    err_str = f"Unsupported Side Type {other} received in order snapshot {strat_order_snapshot_obj} " \
                              f"while updating strat_status"
                    logging.exception(err_str)
                    raise Exception(err_str)
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional
            updated_strat_status_obj.total_fill_exposure = \
                updated_strat_status_obj.total_fill_buy_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_objs[0].id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            err_str = "Pair_strat can't have more than one obj with same symbol in pair_strat_params, " \
                      f"received - {pair_strat_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _update_fill_update_in_snapshot(self, strat_fills_journal_obj: StratFillsJournal):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_order_snapshot_http, underlying_partial_update_strat_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json
        strat_order_snapshot_objs = \
            await underlying_read_strat_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                strat_fills_journal_obj.order_id))
        if len(strat_order_snapshot_objs) == 1:
            strat_order_snapshot_obj = strat_order_snapshot_objs[0]
            if strat_order_snapshot_obj.order_status != OrderStatusType.OE_DOD:
                if (last_filled_qty := strat_order_snapshot_obj.filled_qty) is not None:
                    updated_filled_qty = last_filled_qty + strat_fills_journal_obj.fill_qty
                else:
                    updated_filled_qty = strat_fills_journal_obj.fill_qty
                if (last_filled_notional := strat_order_snapshot_obj.fill_notional) is not None:
                    updated_fill_notional = last_filled_notional + strat_fills_journal_obj.fill_notional
                else:
                    updated_fill_notional = strat_fills_journal_obj.fill_notional
                updated_avg_fill_px = updated_fill_notional / updated_filled_qty
                last_update_fill_qty = strat_fills_journal_obj.fill_qty
                last_update_fill_px = strat_fills_journal_obj.fill_px

                strat_order_snapshot_obj = \
                    await underlying_partial_update_strat_order_snapshot_http(StratOrderSnapshotOptional(
                    _id=strat_order_snapshot_obj.id, filled_qty=updated_filled_qty, avg_fill_px=updated_avg_fill_px,
                    fill_notional=updated_fill_notional, last_update_fill_qty=last_update_fill_qty,
                    last_update_fill_px=last_update_fill_px, last_update_date_time=DateTime.utcnow()))

                await self._update_pair_strat_from_fill_journal(strat_order_snapshot_obj)
                await self._update_portfolio_status_from_fill_journal(strat_order_snapshot_obj)
            else:
                err_str = f"Fill received for snapshot having status OE_DOD - received: " \
                          f"fill_journal - {strat_fills_journal_obj}, snapshot - {strat_order_snapshot_obj}"
                logging.exception(err_str)
                raise Exception(err_str)

        elif len(strat_order_snapshot_objs) == 0:
            err_str = f"Could not find any order snapshot with order-id {strat_fills_journal_obj.order_id} in " \
                      f"{strat_order_snapshot_objs}"
            logging.exception(err_str)
            raise Exception(err_str)
        else:
            err_str = f"Match should return list of only one strat_order_snapshot obj, " \
                      f"returned {strat_order_snapshot_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def create_strat_fills_journal_pre(self, strat_fills_journal_obj: StratFillsJournal):
        # Updating notional field in fills journal
        strat_fills_journal_obj.fill_notional = strat_fills_journal_obj.fill_px * strat_fills_journal_obj.fill_qty

    async def create_strat_fills_journal_post(self, strat_fills_journal_obj: StratFillsJournal):
        with StratOrderSnapshot.reentrant_lock:
            with PairStrat.reentrant_lock:
                await self._update_fill_update_in_snapshot(strat_fills_journal_obj)

    # Example: Soft API Query Interfaces

    async def read_by_id_test_sample_query_pre(self, test_sample_class_type: Type[TestSample]):
        max_date_time = await test_sample_class_type.find_all().max('date')
        if max_date_time is not None:
            max_date_obj = await test_sample_class_type.find(
                test_sample_class_type.date == max_date_time).first_or_none()
            return max_date_obj
        else:
            raise HTTPException(status_code=404, detail="No Data available for query in TestSample")

    def _add_pair_strat_status(self, pair_strat_obj: PairStrat):  # NOQA
        if pair_strat_obj.strat_status is None:
            pair_strat_obj.strat_status = StratStatus(strat_state=StratState.StratState_READY,
                                                      total_buy_qty=0,
                                                      total_sell_qty=0,
                                                      total_order_qty=0,
                                                      total_open_buy_qty=0,
                                                      total_open_sell_qty=0,
                                                      avg_open_buy_px=0.0,
                                                      avg_open_sell_px=0.0,
                                                      total_open_buy_notional=0.0,
                                                      total_open_sell_notional=0.0,
                                                      total_open_exposure=0.0,
                                                      total_fill_buy_qty=0,
                                                      total_fill_sell_qty=0,
                                                      avg_fill_buy_px=0.0,
                                                      avg_fill_sell_px=0.0,
                                                      total_fill_buy_notional=0.0,
                                                      total_fill_sell_notional=0.0,
                                                      total_fill_exposure=0.0,
                                                      total_cxl_buy_qty=0.0,
                                                      total_cxl_sell_qty=0.0,
                                                      avg_cxl_buy_px=0.0,
                                                      avg_cxl_sell_px=0.0,
                                                      total_cxl_buy_notional=0.0,
                                                      total_cxl_sell_notional=0.0,
                                                      total_cxl_exposure=0.0,
                                                      average_premium=0.0,
                                                      balance_notional=0.0,
                                                      strat_alerts=[]
                                                      )
        else:
            raise Exception(f"error: create_pair_strat_pre called with pre-set strat_status! "
                            f"pair_strat_obj: {pair_strat_obj}")

    def set_new_strat_limit(self, pair_strat_obj: PairStrat):  # NOQA
        pair_strat_obj.strat_limits = StratLimits(max_open_orders_per_side=0,
                                                  max_cb_notional=0.0,
                                                  max_open_cb_notional=0.0,
                                                  max_net_filled_notional=0,
                                                  max_concentration=0.0,
                                                  limit_up_down_volume_participation_rate=0.0,
                                                  eligible_brokers=[]
                                                  )

    def _set_derived_side(self, pair_strat_obj: PairStrat):  # NOQA
        raise_error = False
        if pair_strat_obj.pair_strat_params.strat_leg2.side is None:
            if pair_strat_obj.pair_strat_params.strat_leg1.side == Side.BUY:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.SELL
            elif pair_strat_obj.pair_strat_params.strat_leg1.side == Side.SELL:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.BUY
            else:
                raise_error = True
        elif pair_strat_obj.pair_strat_params.strat_leg1.side is None:
            raise_error = True
        # else not required, all good
        if raise_error:
            # handles pair_strat_obj.pair_strat_params.strat_leg1.side == None and all other unsupported values
            raise Exception(f"error: _set_derived_side called with unsupported side combo on legs, leg1: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg1.side} leg2: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg2.side} in pair strat: {pair_strat_obj}")

    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if pair_strat_obj.strat_status is not None:
            raise Exception("error: create_pair_strat_pre called with pre-set strat_status, "
                            f"pair_strat_obj: {pair_strat_obj}")
        if pair_strat_obj.strat_limits is not None:
            raise Exception(
                f"error: create_pair_strat_pre called with pre-set strat_limits, pair_strat_obj{pair_strat_obj}")
        self._add_pair_strat_status(pair_strat_obj)
        self.set_new_strat_limit(pair_strat_obj)
        if pair_strat_obj.pair_strat_params.strat_leg2 is not None:
            self._set_derived_side(pair_strat_obj)

        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("pos_disable", False), ("br_disable", False),
                                          ("security.sec_id", pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                                           pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id)]}
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_limits_http

        filtered_portfolio_limits: List[PortfolioLimits] = await underlying_read_portfolio_limits_http(
            dismiss_filter_agg_pipeline)
        if len(filtered_portfolio_limits) == 1:
            pair_strat_obj.strat_limits.eligible_brokers = [eligible_broker for eligible_broker in
                                                            filtered_portfolio_limits[0].eligible_brokers if
                                                            len(eligible_broker.sec_positions) != 0]
        elif len(filtered_portfolio_limits) > 1:
            raise Exception(f"filtered_portfolio_limits expected: 1, found: {str(len(filtered_portfolio_limits))}, for "
                            f"filter: {dismiss_filter_agg_pipeline}, filtered_portfolio_limits: "
                            f"{filtered_portfolio_limits}; "
                            "use SWAGGER UI to check / fix and re-try")
        else:
            logging.warning(f"No filtered_portfolio_limits found for pair-strat: {pair_strat_obj}")
        pair_strat_obj.frequency = 1
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

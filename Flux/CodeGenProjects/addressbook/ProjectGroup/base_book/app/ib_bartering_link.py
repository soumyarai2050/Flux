# File: ib_bartering_link.py

import asyncio
import logging
from typing import List, ClassVar, Dict, Tuple, Callable, Any, Optional
from decimal import Decimal

from pendulum import DateTime
import pendulum

# Corrected import for ChoreStatus
from ib_insync import IB, Stock, Future, Option, Forex, Contract, Chore as IBChore, Barter, Fill, ChoreState, Execution, ChoreStatus as IBChoreStatus # MODIFIED LINE [1]

import os
os.environ["ModelType"] = "msgspec"
from Flux.CodeGenProjects.AddressBook.ORMModel.barter_core_msgspec_model import InstrumentType
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    Security, Side)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    ChoreBrief, ChoreLedger, ChoreEventType, ChoreStatusType, DealsLedger, SecurityIdSource, ChoreSnapshot)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import \
    YAMLConfigurationManager, host
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    EmailBookServiceHttpClient, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link_base import BarteringLinkBase, add_to_texts


class IBBarteringLink(BarteringLinkBase):
    _ib_instance: ClassVar[Optional[IB]] = None
    _ib_connected: ClassVar[bool] = False
    _kill_switch_active: ClassVar[bool] = False
    _active_chores_cache: ClassVar[Dict[int, Barter]] = {}
    _client_id_counter: ClassVar[int] = 100
    _connection_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _chore_update_lock = asyncio.Lock()     # todo: not ideal design with lock - think about cache as atomicity reduces perf
    _init_in_progress = False

    IB_HOST: ClassVar[str] = '127.0.0.1'
    IB_PORT_PAPER: ClassVar[int] = 7497
    IB_PORT_LIVE: ClassVar[int] = 7496
    IB_PORT_GATEWAY_PAPER: ClassVar[int] = 4002
    IB_PORT_GATEWAY_LIVE: ClassVar[int] = 4001
    DEFAULT_CURRENCY: ClassVar[str] = 'USD'
    CONNECTION_TIMEOUT: ClassVar[int] = 10

    def __init__(self):
        super().__init__("IB")
        if BarteringLinkBase.asyncio_loop is None:
            try:
                BarteringLinkBase.asyncio_loop = asyncio.get_running_loop()
            except RuntimeError:
                logging.warning("No running asyncio loop found during IBBarteringLink init.")

    @classmethod
    async def _ensure_connected(cls, client_id_offset: int = 0) -> bool:
        async with cls._connection_lock:
            if cls._ib_instance and cls._ib_instance.isConnected():
                return True
            if cls._ib_instance:
                logging.info("IB instance exists but is not connected. Cleaning up.")
                try:
                    cls._ib_instance.disconnect()
                except Exception:
                    pass
                cls._ib_instance = None

            cls._ib_instance = IB()
            cls._assign_event_handlers()

            current_client_id = cls._client_id_counter + client_id_offset
            try:
                logging.info(
                    f"Attempting to connect to IB TWS/Gateway on {cls.IB_HOST}:{cls.IB_PORT_PAPER} with clientId {current_client_id}")
                await asyncio.wait_for(
                    cls._ib_instance.connectAsync(host=cls.IB_HOST, port=cls.IB_PORT_PAPER, clientId=current_client_id,
                                                  timeout=cls.CONNECTION_TIMEOUT),
                    timeout=cls.CONNECTION_TIMEOUT + 2
                )
                if cls._ib_instance.isConnected():
                    logging.info(
                        f"Successfully connected to IB. Server version: {cls._ib_instance.client.serverVersion()}")
                    cls._ib_connected = True
                    cls._client_id_counter += 1
                    # REMOVED: cls.asyncio_loop = cls._ib_instance.loop
                    # The IB object will use the current running asyncio loop.
                    # You can get the loop if needed using asyncio.get_running_loop()
                    # For example, if you assigned BarteringLinkBase.asyncio_loop elsewhere using _get_loop()
                    if BarteringLinkBase.asyncio_loop is None:  # Ensure base class loop is set if not already
                        BarteringLinkBase.asyncio_loop = cls._get_loop()
                    return True
                else:
                    logging.error("IB connectAsync call finished but not connected.")
                    cls._ib_instance = None
                    cls._ib_connected = False
                    return False
            except asyncio.TimeoutError:
                logging.error(f"Connection to IB timed out after {cls.CONNECTION_TIMEOUT}s.")
                if cls._ib_instance: cls._ib_instance.disconnect()
                cls._ib_instance = None
                cls._ib_connected = False
                return False
            except ConnectionRefusedError:
                logging.error(f"Connection to IB was refused. Ensure TWS/Gateway is running and API is enabled.")
                cls._ib_instance = None
                cls._ib_connected = False
                return False
            except Exception as e:  # This will now catch the AttributeError if it were to happen elsewhere
                logging.error(f"An error occurred during IB connection phase: {e}", exc_info=True)
                if cls._ib_instance and hasattr(cls._ib_instance, 'disconnect'):  # Check before calling disconnect
                    cls._ib_instance.disconnect()
                cls._ib_instance = None
                cls._ib_connected = False
                return False

    @classmethod
    def _assign_event_handlers(cls):
        if not cls._ib_instance:
            return
        cls._ib_instance.choreStatusEvent -= cls._on_chore_status_update
        cls._ib_instance.execDetailsEvent -= cls._on_execution_details
        cls._ib_instance.openChoreEvent -= cls._on_open_chore
        cls._ib_instance.errorEvent -= cls._on_error
        cls._ib_instance.disconnectedEvent -= cls._on_disconnected

        cls._ib_instance.choreStatusEvent += cls._on_chore_status_update
        cls._ib_instance.execDetailsEvent += cls._on_execution_details
        cls._ib_instance.openChoreEvent += cls._on_open_chore
        cls._ib_instance.errorEvent += cls._on_error
        cls._ib_instance.disconnectedEvent += cls._on_disconnected
        logging.info("IB event handlers assigned.")

    @classmethod
    async def disconnect_ib(cls):
        async with cls._connection_lock:
            if cls._ib_instance and cls._ib_instance.isConnected():  # [1]
                logging.info("Disconnecting from IB.")
                cls._ib_instance.disconnect()  # [1]
                cls._ib_connected = False
                cls._ib_instance = None
                logging.info("Disconnected from IB.")
            else:
                logging.info("No active IB connection to disconnect or already disconnected.")

    @classmethod
    def _get_loop(cls):
        if cls.asyncio_loop and cls.asyncio_loop.is_running():
            return cls.asyncio_loop
        try:
            loop = asyncio.get_running_loop()
            cls.asyncio_loop = loop
            return loop
        except RuntimeError:
            logging.warning("No running asyncio loop. Trying to get/create one.")
            loop = asyncio.get_event_loop_policy().get_event_loop()
            cls.asyncio_loop = loop
            return loop

    @classmethod
    async def recover_cache(cls, **kwargs):
        """
        Comprehensive cache recovery with state reconciliation between IB and database

        Expected kwargs:
        - chore_snapshots: List[ChoreSnapshot] - Chores from database
        - chore_ledger_create_callable: Callable - Function to create chore ledgers
        - chore_snapshot_patch_callable: Callable - Function to update chore snapshots
        - deals_ledger_create_callable: Callable - Function to create deals ledgers
        """

        recovery_start_time = DateTime.utcnow()
        logging.info("Starting comprehensive cache recovery process")

        recovery_stats = {
            'ib_barters_count': 0,
            'db_chore_snapshots_count': 0,
            'new_chores_created': 0,
            'chore_ledgers_created': 0,
            'deals_ledgers_created': 0,
            'chore_snapshots_updated': 0,
            'discrepancies_found': 0,
            'db_only_chores_cancelled': 0
        }

        try:
            cls._init_in_progress = True

            if not await cls._ensure_connected():
                logging.error("Cannot recover cache: IB connection failed")
                return False

            # Extract parameters from kwargs
            chore_snapshots = kwargs.get('chore_snapshots', [])
            chore_ledger_create_callable = kwargs.get('chore_ledger_create_callable')
            chore_snapshot_patch_callable = kwargs.get('chore_snapshot_patch_callable')
            deals_ledger_create_callable = kwargs.get('deals_ledger_create_callable')

            # Validate required callables
            if not chore_ledger_create_callable:
                logging.error("chore_ledger_create_callable is required for recovery")
                return False

            logging.info(f"Recovery parameters: {len(chore_snapshots)} chore snapshots from DB")

            # Step 1: Fetch current state from IB
            ib_barters = await cls._fetch_ib_barters()
            recovery_stats['ib_barters_count'] = len(ib_barters)
            recovery_stats['db_chore_snapshots_count'] = len(chore_snapshots)

            logging.info(f"Fetched {len(ib_barters)} barters from IB and {len(chore_snapshots)} chore snapshots from DB")

            # Step 2: Create lookup dictionaries for comparison
            ib_barters_dict = {str(barter.chore.choreId): barter for barter in ib_barters if barter.chore.choreId}
            chore_snapshots_dict = {str(snapshot.chore_brief.chore_id): snapshot for snapshot in chore_snapshots}

            # Step 3: Handle case 1.1 - IB barters found more than chore snapshots
            ib_only_chore_ids = set(ib_barters_dict.keys()) - set(chore_snapshots_dict.keys())
            if ib_only_chore_ids:
                logging.info(f"Found {len(ib_only_chore_ids)} chores in IB that are not in DB")
                for chore_id in ib_only_chore_ids:
                    barter = ib_barters_dict[chore_id]
                    stats = await cls._process_ib_only_barter(
                        barter, chore_ledger_create_callable, deals_ledger_create_callable
                    )
                    recovery_stats['new_chores_created'] += 1
                    recovery_stats['chore_ledgers_created'] += stats['chore_ledgers_created']
                    recovery_stats['deals_ledgers_created'] += stats['deals_created']

            # Step 4: Handle case 1.2 - Chore snapshots found more than IB barters
            # Create cancellation ledgers for chores that exist in DB but not in IB
            db_only_chore_ids = set(chore_snapshots_dict.keys()) - set(ib_barters_dict.keys())
            if db_only_chore_ids:
                logging.info(
                    f"Found {len(db_only_chore_ids)} chores in DB that are not in IB - creating cancellation ledgers")
                for chore_id in db_only_chore_ids:
                    snapshot = chore_snapshots_dict[chore_id]

                    # Only create cancellation for active chores (not already terminal)
                    if cls._should_cancel_db_only_chore(snapshot):
                        cancel_ledger = cls._create_cancel_ledger_from_snapshot(snapshot)
                        if cancel_ledger:
                            await chore_ledger_create_callable(cancel_ledger)
                            recovery_stats['chore_ledgers_created'] += 1
                            logging.info(f"Created cancellation ledger for DB-only chore: {chore_id}")
                    else:
                        logging.info(
                            f"DB-only chore {chore_id} already in terminal state: {snapshot.chore_status}, skipping cancellation")

                    # Log details for monitoring
                    logging.info(f"DB-only chore: {chore_id}, Status: {snapshot.chore_status}, "
                                 f"Symbol: {snapshot.chore_brief.security.sec_id}, "
                                 f"Qty: {snapshot.chore_brief.qty}, "
                                 f"Filled: {snapshot.filled_qty or 0}")

                recovery_stats['db_only_chores_cancelled'] = len([
                    chore_id for chore_id in db_only_chore_ids
                    if cls._should_cancel_db_only_chore(chore_snapshots_dict[chore_id])
                ])

            # Step 5: Handle case 2 - Compare matching chores for discrepancies
            common_chore_ids = set(ib_barters_dict.keys()) & set(chore_snapshots_dict.keys())
            if common_chore_ids:
                logging.info(f"Comparing {len(common_chore_ids)} chores that exist in both IB and DB")
                for chore_id in common_chore_ids:
                    barter = ib_barters_dict[chore_id]
                    snapshot = chore_snapshots_dict[chore_id]

                    discrepancies = await cls._compare_barter_with_snapshot(barter, snapshot)
                    if discrepancies:
                        recovery_stats['discrepancies_found'] += 1
                        if chore_snapshot_patch_callable:
                            await cls._update_snapshot_from_barter(
                                barter, snapshot, discrepancies, chore_snapshot_patch_callable
                            )
                            recovery_stats['chore_snapshots_updated'] += 1

                    # Update cache with current IB state
                    async with cls._chore_update_lock:
                        cls._active_chores_cache[int(chore_id)] = barter

            # Step 6: Generate recovery report
            recovery_report = cls._generate_recovery_report(recovery_stats, recovery_start_time)
            logging.info(f"Cache recovery completed: {recovery_report}")

            return True

        except Exception as e:
            logging.error(f"Error during cache recovery: {e}", exc_info=True)
            return False

        finally:
            cls._init_in_progress = False
            recovery_end_time = DateTime.utcnow()
            duration = (recovery_end_time - recovery_start_time).total_seconds()
            logging.info(f"Cache recovery process completed in {duration:.2f}s")

    @classmethod
    async def _fetch_ib_barters(cls) -> List[Barter]:
        """Fetch all current barters from IB"""

        try:
            logging.info("Fetching all barters from IB...")

            # Get initial barters snapshot
            initial_barters = cls._ib_instance.barters()
            initial_count = len(initial_barters)
            logging.debug(f"Initial barters count: {initial_count}")

            # Request fresh state from IB to ensure we have the latest information
            # This is important for recovery as the IB instance might have stale data
            logging.debug("Requesting all open chores to refresh IB state...")
            await cls._ib_instance.reqAllOpenChoresAsync()

            # Brief pause to allow IB to process the request and update internal state
            # IB API is asynchronous and updates happen via events
            await asyncio.sleep(0.5)

            # Get updated barters list after refresh
            updated_barters = cls._ib_instance.barters()
            updated_count = len(updated_barters)

            # Log the difference for debugging/monitoring
            if updated_count != initial_count:
                logging.info(f"Barter count changed after refresh: {initial_count} -> {updated_count}")
            else:
                logging.debug(f"Barter count unchanged after refresh: {updated_count}")

            logging.info(f"Successfully fetched {updated_count} barters from IB")
            return updated_barters

        except Exception as e:
            logging.error(f"Error fetching barters from IB: {e}")
            raise

    @classmethod
    async def _process_ib_only_barter(cls, barter: Barter, chore_ledger_create_callable: Callable,
                                     deals_ledger_create_callable: Optional[Callable]) -> Dict:
        """
        Process a barter that exists in IB but not in DB
        Creates OE_NEW, then subsequent events based on current status, and deals if any
        """

        stats = {'chore_ledgers_created': 0, 'deals_created': 0}
        chore_id = str(barter.chore.choreId)

        try:
            logging.info(f"Processing IB-only barter: ChoreID {chore_id}, Status: {barter.choreStatus.status}")

            # Step 1: Create OE_NEW ledger entry
            new_chore_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_NEW)
            if new_chore_ledger:
                await chore_ledger_create_callable(new_chore_ledger)
                stats['chore_ledgers_created'] += 1
                logging.info(f"Created OE_NEW ledger for chore {chore_id}")

            # Step 2: Create subsequent ledger entries based on current status
            # The chore is: OE_NEW -> OE_ACK -> [FILLS] -> [TERMINAL_STATES]
            current_status = barter.choreStatus.status
            filled_qty = int(barter.choreStatus.filled) if barter.choreStatus.filled else 0

            if current_status in [IBChoreStatus.PreSubmitted, IBChoreStatus.Submitted]:
                # Chore is acknowledged and active
                ack_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_ACK)
                if ack_ledger:
                    await chore_ledger_create_callable(ack_ledger)
                    stats['chore_ledgers_created'] += 1
                    logging.info(f"Created OE_ACK ledger for chore {chore_id}")

                # Create deals if any (for partially filled active chores)
                if filled_qty > 0 and deals_ledger_create_callable:
                    fill_ledger = cls._create_fill_ledger_from_barter(barter, filled_qty)
                    if fill_ledger:
                        await deals_ledger_create_callable(fill_ledger)
                        stats['deals_created'] += 1
                        logging.info(f"Created fill ledger for active chore {chore_id}, filled qty: {filled_qty}")

            elif current_status in [IBChoreStatus.Cancelled, IBChoreStatus.ApiCancelled]:
                # Chore was acknowledged, possibly filled, then cancelled
                ack_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_ACK)
                if ack_ledger:
                    await chore_ledger_create_callable(ack_ledger)
                    stats['chore_ledgers_created'] += 1

                # Create deals if any (before cancellation)
                if filled_qty > 0 and deals_ledger_create_callable:
                    fill_ledger = cls._create_fill_ledger_from_barter(barter, filled_qty)
                    if fill_ledger:
                        await deals_ledger_create_callable(fill_ledger)
                        stats['deals_created'] += 1
                        logging.info(f"Created fill ledger for cancelled chore {chore_id}, filled qty: {filled_qty}")

                # Then create cancellation ledger
                cancel_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_CXL_ACK)
                if cancel_ledger:
                    await chore_ledger_create_callable(cancel_ledger)
                    stats['chore_ledgers_created'] += 1
                    logging.info(f"Created OE_ACK and OE_CXL_ACK ledgers for chore {chore_id}")

            elif current_status == IBChoreStatus.Filled:
                # Chore was acknowledged then fully filled
                ack_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_ACK)
                if ack_ledger:
                    await chore_ledger_create_callable(ack_ledger)
                    stats['chore_ledgers_created'] += 1

                # Create deals (must be after ACK)
                if filled_qty > 0 and deals_ledger_create_callable:
                    fill_ledger = cls._create_fill_ledger_from_barter(barter, filled_qty)
                    if fill_ledger:
                        await deals_ledger_create_callable(fill_ledger)
                        stats['deals_created'] += 1
                        logging.info(f"Created fill ledger for filled chore {chore_id}, filled qty: {filled_qty}")

                logging.info(f"Created OE_ACK and fill ledgers for fully filled chore {chore_id}")

            elif current_status == IBChoreStatus.Inactive:
                # Chore was acknowledged, possibly filled, then rejected/lapsed
                ack_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_ACK)
                if ack_ledger:
                    await chore_ledger_create_callable(ack_ledger)
                    stats['chore_ledgers_created'] += 1

                # Create deals if any (before lapse - though rare for inactive chores)
                if filled_qty > 0 and deals_ledger_create_callable:
                    fill_ledger = cls._create_fill_ledger_from_barter(barter, filled_qty)
                    if fill_ledger:
                        await deals_ledger_create_callable(fill_ledger)
                        stats['deals_created'] += 1
                        logging.info(f"Created fill ledger for lapsed chore {chore_id}, filled qty: {filled_qty}")

                # Then create lapse ledger
                lapse_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_LAPSE)
                if lapse_ledger:
                    await chore_ledger_create_callable(lapse_ledger)
                    stats['chore_ledgers_created'] += 1
                    logging.info(f"Created OE_ACK and OE_LAPSE ledgers for chore {chore_id}")

            else:
                # Handle any other status (including partially filled chores that don't have a specific status)
                # In IB, partially filled chores usually show as "Submitted" with filled > 0
                logging.info(
                    f"Chore {chore_id} has status '{current_status}' with {filled_qty} filled, treating as acknowledged")
                ack_ledger = cls._create_chore_ledger_from_barter(barter, ChoreEventType.OE_ACK)
                if ack_ledger:
                    await chore_ledger_create_callable(ack_ledger)
                    stats['chore_ledgers_created'] += 1

                # Create deals if any
                if filled_qty > 0 and deals_ledger_create_callable:
                    fill_ledger = cls._create_fill_ledger_from_barter(barter, filled_qty)
                    if fill_ledger:
                        await deals_ledger_create_callable(fill_ledger)
                        stats['deals_created'] += 1
                        logging.info(
                            f"Created fill ledger for chore {chore_id} with status {current_status}, filled qty: {filled_qty}")

            # Add to cache
            async with cls._chore_update_lock:
                cls._active_chores_cache[barter.chore.choreId] = barter

            return stats

        except Exception as e:
            logging.error(f"Error processing IB-only barter {chore_id}: {e}", exc_info=True)
            return stats

    @classmethod
    def _create_chore_ledger_from_barter(cls, barter: Barter, event_type: ChoreEventType) -> Optional[ChoreLedger]:
        """Create an ChoreLedger from a Barter object with specified event type"""

        try:
            ib_chore_id = barter.chore.choreId
            ib_status_str = barter.choreStatus.status
            perm_id = barter.chore.permId
            why_held = barter.choreStatus.whyHeld

            # Create security objects
            system_security = Security(
                sec_id=barter.contract.localSymbol if barter.contract.localSymbol else barter.contract.symbol,
                sec_id_source=SecurityIdSource.TICKER,
                inst_type=cls._map_ib_sec_type_to_instrument_type(barter.contract.secType)
            )

            # Map chore side
            chore_action_map = {'BUY': Side.BUY, 'SELL': Side.SELL, 'SSHORT': Side.SS}
            chore_side = chore_action_map.get(barter.chore.action.upper())
            if not chore_side:
                logging.error(f"Could not map IB action '{barter.chore.action}' to Side for chore {ib_chore_id}")
                return None

            # Create chore brief
            chore_brief = ChoreBrief(
                chore_id=str(ib_chore_id),
                security=system_security,
                bartering_security=Security(
                    sec_id=barter.contract.localSymbol or barter.contract.symbol,
                    inst_type=system_security.inst_type
                ),
                side=chore_side,
                px=barter.chore.lmtPrice if barter.chore.choreType == "LMT" else barter.chore.auxPrice if barter.chore.choreType in [
                    "STP", "STP LMT"] else None,
                qty=int(barter.chore.totalQuantity),
                chore_notional=(float(barter.chore.lmtPrice) * int(
                    barter.chore.totalQuantity)) if barter.chore.lmtPrice and barter.chore.totalQuantity else None,
                underlying_account=barter.chore.account,
                exchange=barter.contract.exchange,
                text=[f"RECOVERY: {event_type.value}. IB Status: {ib_status_str}. PermId: {perm_id}." + (
                    f" WhyHeld: {why_held}" if why_held else "")],
                user_data=barter.chore.choreRef
            )

            # Create chore ledger
            chore_ledger = ChoreLedger(
                chore=chore_brief,
                chore_event_date_time=DateTime.utcnow(),
                chore_event=event_type
            )

            return chore_ledger

        except Exception as e:
            logging.error(f"Error creating chore ledger from barter: {e}", exc_info=True)
            return None

    @classmethod
    def _create_fill_ledger_from_barter(cls, barter: Barter, filled_qty: int) -> Optional[DealsLedger]:
        """Create a DealsLedger from a Barter object representing cumulative deals"""

        try:
            chore_id = str(barter.chore.choreId)
            avg_fill_price = barter.choreStatus.avgFillPrice or 0.0

            # Map fill side
            fill_side_map = {'BUY': Side.BUY, 'SELL': Side.SELL, 'SSHORT': Side.SS}
            fill_side = fill_side_map.get(barter.chore.action.upper())
            if not fill_side:
                logging.error(f"Could not map IB action '{barter.chore.action}' to Side for fill {chore_id}")
                return None

            # Create fill ledger (representing cumulative fill during recovery)
            fill_ledger = DealsLedger(
                chore_id=chore_id,
                fill_px=avg_fill_price,
                fill_qty=filled_qty,
                fill_notional=avg_fill_price * filled_qty,
                fill_symbol=barter.contract.localSymbol or barter.contract.symbol,
                fill_bartering_symbol=barter.contract.localSymbol or barter.contract.symbol,
                fill_side=fill_side,
                underlying_account=barter.chore.account,
                fill_date_time=DateTime.utcnow(),  # Using current time since we don't have exact fill time
                fill_id=f"RECOVERY_FILL_{chore_id}_{DateTime.utcnow().timestamp()}",
                underlying_account_cumulative_fill_qty=filled_qty,
                user_data=barter.chore.choreRef
            )

            return fill_ledger

        except Exception as e:
            logging.error(f"Error creating fill ledger from barter: {e}", exc_info=True)
            return None

    @classmethod
    async def _update_snapshot_from_barter(cls, barter: Barter, snapshot, discrepancies: Dict,
                                          chore_snapshot_update_callable: Callable):
        """Update chore snapshot with values from IB barter"""

        chore_id = str(barter.chore.choreId)

        try:
            update_fields = {}

            # Update fields based on discrepancies found
            if 'chore_status' in discrepancies:
                update_fields['chore_status'] = discrepancies['chore_status']['ib_value']

            if 'filled_qty' in discrepancies:
                update_fields['filled_qty'] = discrepancies['filled_qty']['ib_value']

            if 'avg_fill_px' in discrepancies:
                update_fields['avg_fill_px'] = discrepancies['avg_fill_px']['ib_value']

            if 'qty' in discrepancies:
                # Update the chore brief qty (this might require updating the nested object)
                update_fields['chore_brief'] = {}
                update_fields['chore_brief']['qty'] = discrepancies['qty']['ib_value']

            if 'px' in discrepancies:
                # Update the chore brief px (this might require updating the nested object)
                if update_fields.get('chore_brief') is None:
                    update_fields['chore_brief'] = {}
                update_fields['chore_brief']['px'] = discrepancies['px']['ib_value']

            # Update cancellation-related fields
            if 'cxled_qty' in discrepancies:
                update_fields['cxled_qty'] = discrepancies['cxled_qty']['ib_value']

            if 'fill_notional' in discrepancies:
                update_fields['fill_notional'] = discrepancies['fill_notional']['ib_value']

            if 'cxled_notional' in discrepancies:
                update_fields['cxled_notional'] = discrepancies['cxled_notional']['ib_value']

            if 'avg_cxled_px' in discrepancies:
                update_fields['avg_cxled_px'] = discrepancies['avg_cxled_px']['ib_value']

            # Calculate derived fields that might need updating

            # Update fill notional if we have both fill qty and price
            if 'filled_qty' in update_fields and 'avg_fill_px' in update_fields:
                update_fields['fill_notional'] = update_fields['filled_qty'] * update_fields['avg_fill_px']
            elif 'filled_qty' in update_fields and snapshot.avg_fill_px:
                update_fields['fill_notional'] = update_fields['filled_qty'] * snapshot.avg_fill_px
            elif 'avg_fill_px' in update_fields and snapshot.filled_qty:
                update_fields['fill_notional'] = snapshot.filled_qty * update_fields['avg_fill_px']

            # Update cancelled notional if we have cancelled qty and price
            if 'cxled_qty' in update_fields and barter.chore.choreType == "LMT":
                update_fields['cxled_notional'] = update_fields['cxled_qty'] * barter.chore.lmtPrice
                # Also set avg cancelled price for limit chores
                if update_fields['cxled_qty'] > 0:
                    update_fields['avg_cxled_px'] = barter.chore.lmtPrice

            # Update last update time
            update_fields['last_update_date_time'] = DateTime.utcnow()

            update_fields['_id'] = snapshot.id

            # Call the update function
            await chore_snapshot_update_callable(update_fields)

            logging.info(f"Updated chore snapshot for chore {chore_id} with fields: {list(update_fields.keys())}")

        except Exception as e:
            logging.error(f"Error updating snapshot for chore {chore_id}: {e}", exc_info=True)

    @classmethod
    async def _compare_barter_with_snapshot(cls, barter: Barter, snapshot) -> Optional[Dict]:
        """Compare IB barter with database chore snapshot to find discrepancies"""

        discrepancies = {}
        chore_id = str(barter.chore.choreId)

        try:
            # Compare chore status
            ib_status = cls._map_ib_status_to_chore_status_type(barter.choreStatus.status)
            if snapshot.chore_status != ib_status:
                discrepancies['chore_status'] = {
                    'db_value': snapshot.chore_status,
                    'ib_value': ib_status,
                    'ib_raw_status': barter.choreStatus.status
                }

            # Compare filled quantity
            ib_filled_qty = int(barter.choreStatus.filled) if barter.choreStatus.filled else 0
            db_filled_qty = snapshot.filled_qty or 0
            if db_filled_qty != ib_filled_qty:
                discrepancies['filled_qty'] = {
                    'db_value': db_filled_qty,
                    'ib_value': ib_filled_qty
                }

            # Compare average fill price
            ib_avg_fill_px = barter.choreStatus.avgFillPrice or 0.0
            db_avg_fill_px = snapshot.avg_fill_px or 0.0
            if abs(db_avg_fill_px - ib_avg_fill_px) > 0.0001:  # Small tolerance for float comparison
                discrepancies['avg_fill_px'] = {
                    'db_value': db_avg_fill_px,
                    'ib_value': ib_avg_fill_px
                }

            # Compare quantities (original chore qty)
            ib_qty = int(barter.chore.totalQuantity)
            db_qty = snapshot.chore_brief.qty
            if db_qty != ib_qty:
                discrepancies['qty'] = {
                    'db_value': db_qty,
                    'ib_value': ib_qty
                }

            # Compare prices (for limit chores)
            if barter.chore.choreType == "LMT":
                ib_px = barter.chore.lmtPrice
                db_px = snapshot.chore_brief.px
                if db_px and abs(db_px - ib_px) > 0.0001:
                    discrepancies['px'] = {
                        'db_value': db_px,
                        'ib_value': ib_px
                    }

            # Compare cancellation-related fields
            # Calculate IB cancelled quantity: Total - Remaining - Filled = Cancelled
            ib_remaining_qty = int(barter.choreStatus.remaining) if barter.choreStatus.remaining else 0
            ib_total_qty = int(barter.chore.totalQuantity)
            ib_filled_qty = int(barter.choreStatus.filled) if barter.choreStatus.filled else 0

            # For IB: Cancelled = Total - Remaining - Filled
            # This works for all statuses (active chores will have cxled_qty = 0)
            ib_cxled_qty = max(0, ib_total_qty - ib_remaining_qty - ib_filled_qty)
            db_cxled_qty = snapshot.cxled_qty or 0

            if db_cxled_qty != ib_cxled_qty:
                discrepancies['cxled_qty'] = {
                    'db_value': db_cxled_qty,
                    'ib_value': ib_cxled_qty
                }

            # Compare fill notional (always check if deals exist)
            if ib_filled_qty > 0 and ib_avg_fill_px > 0:
                ib_fill_notional = ib_filled_qty * ib_avg_fill_px
                db_fill_notional = snapshot.fill_notional or 0.0

                if abs(db_fill_notional - ib_fill_notional) > 0.01:  # Tolerance for currency rounding
                    discrepancies['fill_notional'] = {
                        'db_value': db_fill_notional,
                        'ib_value': ib_fill_notional
                    }

            # Compare cancelled notional (always check if there are cancellations)
            if ib_cxled_qty > 0:
                # Calculate cancelled notional: (cancelled qty * limit price) for limit chores
                if barter.chore.choreType == "LMT":
                    ib_cxled_notional = ib_cxled_qty * barter.chore.lmtPrice
                    db_cxled_notional = snapshot.cxled_notional or 0.0

                    if abs(db_cxled_notional - ib_cxled_notional) > 0.01:
                        discrepancies['cxled_notional'] = {
                            'db_value': db_cxled_notional,
                            'ib_value': ib_cxled_notional
                        }

            # Compare average cancelled price (always check if cancellations exist)
            if ib_cxled_qty > 0:
                # For limit chores, cancelled price is typically the limit price
                if barter.chore.choreType == "LMT":
                    ib_avg_cxled_px = barter.chore.lmtPrice
                    db_avg_cxled_px = snapshot.avg_cxled_px or 0.0

                    if db_avg_cxled_px > 0 and abs(db_avg_cxled_px - ib_avg_cxled_px) > 0.0001:
                        discrepancies['avg_cxled_px'] = {
                            'db_value': db_avg_cxled_px,
                            'ib_value': ib_avg_cxled_px
                        }
                    elif db_avg_cxled_px == 0.0 and ib_avg_cxled_px > 0:
                        # DB has no cancelled price but IB indicates cancellations
                        discrepancies['avg_cxled_px'] = {
                            'db_value': db_avg_cxled_px,
                            'ib_value': ib_avg_cxled_px
                        }

            # Special case: Check if DB shows cancellations but IB doesn't
            elif db_cxled_qty > 0 and ib_cxled_qty == 0:
                # This might indicate the chore was partially cancelled in DB but is still fully active in IB
                # Or it could be stale cancellation data that needs to be cleared
                logging.info(f"Chore {chore_id}: DB shows {db_cxled_qty} cancelled, but IB shows 0 cancelled")

                # Clear cancelled quantities if IB shows no cancellations
                if snapshot.cxled_notional:
                    discrepancies['cxled_notional'] = {
                        'db_value': snapshot.cxled_notional,
                        'ib_value': 0.0
                    }

                if snapshot.avg_cxled_px:
                    discrepancies['avg_cxled_px'] = {
                        'db_value': snapshot.avg_cxled_px,
                        'ib_value': 0.0
                    }

            if discrepancies:
                logging.info(f"Found discrepancies for chore {chore_id}: {discrepancies}")

            return discrepancies if discrepancies else None

        except Exception as e:
            logging.error(f"Error comparing barter with snapshot for chore {chore_id}: {e}", exc_info=True)
            return None

    @classmethod
    def _should_cancel_db_only_chore(cls, snapshot) -> bool:
        """
        Determine if a DB-only chore should be cancelled

        Only cancel chores that are in active states. Chores already in terminal states
        (filled, cancelled, lapsed) should not be cancelled again.
        """

        active_statuses = {
            ChoreStatusType.OE_UNACK,  # Unacknowledged chores
            ChoreStatusType.OE_ACKED,  # Acknowledged and active chores
            ChoreStatusType.OE_CXL_UNACK,  # Cancel pending chores
            ChoreStatusType.OE_AMD_DN_UNACKED,  # Amendment pending chores
            ChoreStatusType.OE_AMD_UP_UNACKED  # Amendment pending chores
        }

        return snapshot.chore_status in active_statuses

    @classmethod
    def _create_cancel_ledger_from_snapshot(cls, snapshot) -> Optional[ChoreLedger]:
        """
        Create a cancellation ChoreLedger from an ChoreSnapshot

        This is used for DB-only chores that need to be cancelled during recovery
        """

        try:
            # Create a copy of the chore brief with cancellation context
            chore_brief = ChoreBrief(
                chore_id=snapshot.chore_brief.chore_id,
                security=snapshot.chore_brief.security,
                bartering_security=snapshot.chore_brief.bartering_security,
                side=snapshot.chore_brief.side,
                px=snapshot.chore_brief.px,
                qty=snapshot.chore_brief.qty,
                chore_notional=snapshot.chore_brief.chore_notional,
                underlying_account=snapshot.chore_brief.underlying_account,
                exchange=snapshot.chore_brief.exchange,
                text=(snapshot.chore_brief.text or []) + [
                    f"RECOVERY_CANCEL: Chore not found in IB, presumed cancelled/expired"],
                user_data=snapshot.chore_brief.user_data
            )

            # Create cancellation ledger entry
            cancel_ledger = ChoreLedger(
                chore=chore_brief,
                chore_event_date_time=DateTime.utcnow(),
                chore_event=ChoreEventType.OE_CXL_ACK  # Mark as cancelled
            )

            return cancel_ledger

        except Exception as e:
            logging.error(f"Error creating cancel ledger from snapshot: {e}", exc_info=True)
            return None

    @classmethod
    def _generate_recovery_report(cls, stats: Dict, start_time: DateTime) -> str:
        """Generate a comprehensive recovery report"""

        duration = (DateTime.utcnow() - start_time).total_seconds()

        report = f"Recovery completed in {duration:.2f}s. "
        report += f"IB Barters: {stats['ib_barters_count']}, "
        report += f"DB Snapshots: {stats['db_chore_snapshots_count']}, "
        report += f"New Chores: {stats['new_chores_created']}, "
        report += f"Chore Ledgers: {stats['chore_ledgers_created']}, "
        report += f"Fill Ledgers: {stats['deals_ledgers_created']}, "
        report += f"Snapshots Updated: {stats['chore_snapshots_updated']}, "
        report += f"Discrepancies: {stats['discrepancies_found']}"

        return report

    @classmethod
    async def _on_open_chore(cls, barter: Barter):  # [1]
        if not barter or not barter.chore or not barter.choreStatus:
            return

        async with cls._chore_update_lock:  # Protect cache modification
            logging.info(f"IB Event - OpenChore: ID {barter.chore.choreId}, Status {barter.choreStatus.status}, "  # [1]
                         f"Symbol {barter.contract.symbol}, Filled {barter.choreStatus.filled}, "  # [1]
                         f"Remaining {barter.choreStatus.remaining}, ClientId {barter.chore.clientId}")  # [1]
            cls._active_chores_cache[barter.chore.choreId] = barter  # [1]

    @classmethod
    def get_chore_ledger_obj_from_barter(cls, barter: Barter, force_ret: bool = False) -> ChoreLedger | None:
        ib_chore_id = barter.chore.choreId
        ib_status_str = barter.choreStatus.status  # This is a string like 'Filled', 'Submitted'
        perm_id = barter.chore.permId
        why_held = barter.choreStatus.whyHeld

        event_type: ChoreEventType
        msg_parts = [f"IB Status: {ib_status_str}"]
        if why_held:
            msg_parts.append(f"WhyHeld: {why_held}")

        # The ChoreStatus class itself has attributes for each status string,
        # e.g., IBChoreStatus.Filled == 'Filled'. So comparisons are direct with the string.
        if ib_status_str in [IBChoreStatus.ApiPending, IBChoreStatus.PendingSubmit]:  # [1]
            event_type = ChoreEventType.OE_NEW
        elif ib_status_str == IBChoreStatus.PendingCancel:  # If a cancel is pending
            event_type = ChoreEventType.OE_CXL  # A cancel request has been made
        elif ib_status_str == IBChoreStatus.ApiCancelled or ib_status_str == IBChoreStatus.Cancelled:  # If actually cancelled by API or TWS
            event_type = ChoreEventType.OE_CXL_ACK  # Confirmed cancel
        elif ib_status_str in [IBChoreStatus.PreSubmitted, IBChoreStatus.Submitted]:
            event_type = ChoreEventType.OE_ACK  # Chore is live
        elif ib_status_str == IBChoreStatus.Filled:
            if not force_ret:
                return None # Deals are handled by _on_execution_details, no chore update required for this case
            else:
                # if force_ret then returning obj with OE_NEW - used only when new_chore is placed with immediate deals
                event_type = ChoreEventType.OE_NEW
        elif ib_status_str == IBChoreStatus.Inactive:
            event_type = ChoreEventType.OE_LAPSE
            msg_parts.append("Chore Inactive")
        else:
            logging.warning(
                f"Unhandled IB chore status '{ib_status_str}' for chore {ib_chore_id}. Treating as generic update.")
            event_type = ChoreEventType.OE_ACK
            msg_parts.append(f"Status: {ib_status_str}")

        system_security = Security(
            sec_id=barter.contract.localSymbol if barter.contract.localSymbol else barter.contract.symbol,  # [1]
            sec_id_source=SecurityIdSource.TICKER,
            inst_type=cls._map_ib_sec_type_to_instrument_type(barter.contract.secType)  # [1]
        )
        chore_action_map = {'BUY': Side.BUY, 'SELL': Side.SELL, 'SSHORT': Side.SS}
        chore_side = chore_action_map.get(barter.chore.action.upper())  # [1]
        if not chore_side:
            logging.error(f"Could not map IB action '{barter.chore.action}' to Side for chore {ib_chore_id}")  # [1]
            return None

        chore_brief = ChoreBrief(
            chore_id=str(ib_chore_id),
            security=system_security,
            bartering_security=Security(sec_id=barter.contract.localSymbol or barter.contract.symbol,
                                      inst_type=system_security.inst_type),  # [1]
            side=chore_side,
            px=barter.chore.lmtPrice if barter.chore.choreType == "LMT" else barter.chore.auxPrice if barter.chore.choreType in [
                "STP", "STP LMT"] else None,  # [1]
            qty=int(barter.chore.totalQuantity),  # [1]
            chore_notional=(float(barter.chore.lmtPrice) * int(
                barter.chore.totalQuantity)) if barter.chore.lmtPrice and barter.chore.totalQuantity else None,  # [1]
            underlying_account=barter.chore.account,  # [1]
            exchange=barter.contract.exchange,  # [1]
            text=[f"IB Event: {event_type.value}. Status: {ib_status_str}. PermId: {perm_id}. " + (
                f"WhyHeld: {why_held}" if why_held else "")],
            user_data=barter.chore.choreRef  # [1]
        )

        chore_ledger_entry = ChoreLedger(
            chore=chore_brief,
            chore_event_date_time=DateTime.utcnow(),
            chore_event=event_type,
        )
        return chore_ledger_entry

    @classmethod
    async def _on_chore_status_update(cls, barter: Barter):
        if cls._init_in_progress:  # CHECK THE FLAG
            logging.debug(
                f"IB Event during init - ChoreStatus: ID {barter.chore.choreId}, Status {barter.choreStatus.status}. Ledger creation deferred.")
            # Still update the cache as recover_cache might rely on the latest state from connection events
            if barter and barter.chore:
                async with cls._chore_update_lock:
                    cls._active_chores_cache[barter.chore.choreId] = barter
            return  # IMPORTANT: Return early to prevent ledger creation

        async with IBBarteringLink._chore_update_lock:
            if not barter or not barter.chore or not barter.choreStatus:
                return

            ib_chore_id = barter.chore.choreId
            ib_status_str = barter.choreStatus.status  # This is a string like 'Filled', 'Submitted'
            filled_qty = int(barter.choreStatus.filled)
            remaining_qty = int(barter.choreStatus.remaining)
            avg_fill_price = barter.choreStatus.avgFillPrice
            perm_id = barter.chore.permId
            client_id = barter.chore.clientId
            why_held = barter.choreStatus.whyHeld

            logging.info(f"IB Event - ChoreStatus: ID {ib_chore_id} (PermId: {perm_id}), Status: {ib_status_str}, "
                        f"Filled: {filled_qty}, Remaining: {remaining_qty}, AvgPx: {avg_fill_price}, "
                        f"Symbol: {barter.contract.symbol}, Account: {barter.chore.account}, ClientId: {client_id}, WhyHeld: {why_held}")

            cls._active_chores_cache[ib_chore_id] = barter

            if not cls.chore_create_async_callable:
                logging.warning("chore_create_async_callable not set. Cannot send ChoreLedger update.")
                return

            chore_ledger_entry = cls.get_chore_ledger_obj_from_barter(barter)

            if chore_ledger_entry:
                # persisting chore update as ledger
                await IBBarteringLink.handle_chore_ledger_create(chore_ledger_entry)
            # else not required: if something went wrong, logged error internally, else all good

            # Check if the chore is done and remove from cache
            # No need to be added in fill side since even if chore is fully filled update is provided here
            if barter.isDone():
                logging.info(
                    f"Chore {ib_chore_id} is done (Status: {ib_status_str}). Removing from active_chores_cache.")
                # Optional: Short delay if there's any concern about ultra-rare trailing events, but generally not needed.
                # await asyncio.sleep(0.1)
                if ib_chore_id in cls._active_chores_cache:
                    del cls._active_chores_cache[ib_chore_id]
            # else not required: if something went wrong, logged error internally, else all good

    @classmethod
    async def handle_chore_ledger_create(cls, chore_ledger: ChoreLedger):
        try:
            if asyncio.iscoroutinefunction(cls.chore_create_async_callable):
                await cls.chore_create_async_callable(chore_ledger)
            else:
                cls.chore_create_async_callable(chore_ledger)
        except Exception as e:
            logging.error(f"Error calling chore_create_async_callable: {e}", exc_info=True)

    @classmethod
    async def _on_execution_details(cls, barter: Barter, fill: Fill):  # [1]
        if cls._init_in_progress:  # CHECK THE FLAG
            logging.debug(
                f"IB Event during init - ChoreStatus: ID {barter.chore.choreId}, Status {barter.choreStatus.status}. Ledger creation deferred.")
            # Still update the cache as recover_cache might rely on the latest state from connection events
            if barter and barter.chore:
                async with cls._chore_update_lock:
                    cls._active_chores_cache[barter.chore.choreId] = barter
            return  # IMPORTANT: Return early to prevent ledger creation

        async with IBBarteringLink._chore_update_lock:
            exec_detail = fill.execution  # [1]
            commission_report = fill.commissionReport  # [1]

            logging.info(f"IB Event - Execution: ChoreID {exec_detail.choreId}, ExecID {exec_detail.execId}, "  # [1]
                        f"Symbol {barter.contract.symbol}, Qty {exec_detail.shares}, Px {exec_detail.price}, "  # [1]
                        f"Time {exec_detail.time}, Account: {exec_detail.acctNumber}, "  # [1]
                        f"Commission: {commission_report.commission} {commission_report.currency}")  # [1]

            cls._active_chores_cache[barter.chore.choreId] = barter  # [1]

            if not cls.fill_create_async_callable:
                logging.warning("fill_create_async_callable not set. Cannot send DealsLedger update.")
                return

            ib_chore_id_str = str(exec_detail.choreId)  # [1]
            fill_qty_val = int(exec_detail.shares)  # [1]
            fill_px_val = float(exec_detail.price)  # [1]
            fill_side_map = {'BOT': Side.BUY, 'SLD': Side.SELL}
            actual_fill_side = fill_side_map.get(exec_detail.side)  # [1]

            if not actual_fill_side:
                logging.error(
                    f"Could not map IB execution side '{exec_detail.side}' to Side for fill {exec_detail.execId}")  # [1]
                return

            cumulative_fill_for_chore = int(barter.choreStatus.filled)  # [1]
            fill_datetime_obj = fill.time  # [1]
            if fill_datetime_obj:
                if fill_datetime_obj.tzinfo is None:
                    fill_pendulum_dt = pendulum.instance(fill_datetime_obj, tz=pendulum.now().timezone.name).in_timezone(
                        'UTC')
                else:
                    fill_pendulum_dt = pendulum.instance(fill_datetime_obj).in_timezone('UTC')
            else:
                fill_pendulum_dt = DateTime.utcnow()

            deals_ledger_entry = DealsLedger(
                chore_id=ib_chore_id_str,
                fill_px=fill_px_val,
                fill_qty=fill_qty_val,
                fill_notional=fill_px_val * fill_qty_val,
                fill_symbol=barter.contract.localSymbol or barter.contract.symbol,  # [1]
                fill_bartering_symbol=barter.contract.localSymbol or barter.contract.symbol,  # [1]
                fill_side=actual_fill_side,
                underlying_account=exec_detail.acctNumber,  # [1]
                fill_date_time=fill_pendulum_dt,
                fill_id=exec_detail.execId,  # [1]
                underlying_account_cumulative_fill_qty=cumulative_fill_for_chore,
                user_data=barter.chore.choreRef  # [1]
            )

            try:
                if asyncio.iscoroutinefunction(cls.fill_create_async_callable):
                    await cls.fill_create_async_callable(deals_ledger_entry)
                else:
                    cls.fill_create_async_callable(deals_ledger_entry)
            except Exception as e:
                logging.error(f"Error calling fill_create_async_callable: {e}", exc_info=True)

    @classmethod
    async def _on_error(cls, reqId: int, errorCode: int, errorString: str, contract: Optional[Contract] = None):
        # Filter for common informational messages from TWS
        # Codes 2100-2108, 2110, 2119, 2137, 2150, 2152, 2157, 2158 are often informational or warnings
        informational_codes = list(range(2100, 2109)) + [2110, 2119, 2137, 2150, 2152, 2157, 2158]
        # Add other known warning/info codes specific to your needs

        chore_cxled_code = 202       # handling is already in _on_chore_status_update - just logging as info here

        log_message = (f"IB Info/Warning: ReqId/ChoreId: {reqId}, Code: {errorCode}, Message: {errorString}" +
                       (f", Contract: {contract.symbol}" if contract else ""))

        if errorCode in informational_codes or errorCode == chore_cxled_code:
            logging.info(log_message)  # Log as INFO instead of ERROR
        elif 300 <= errorCode < 400:  # Typically warning messages
            logging.warning(log_message)
        else:  # Actual errors
            logging.error(f"IB Error: ReqId/ChoreId: {reqId}, Code: {errorCode}, Message: {errorString}" +
                         (f", Contract: {contract.symbol}" if contract else ""))

        # Existing logic to process chore-related errors for ChoreLedger
        if (reqId > 0 and cls.chore_create_async_callable and
                errorCode not in informational_codes and errorCode != chore_cxled_code):

            async with cls._chore_update_lock:  # Protect cache modification
                # Only process as an chore state change if it's likely a real error impacting an chore
                barter = cls._active_chores_cache.get(reqId)
                if barter and barter.chore:
                    # ... (rest of your existing error to ChoreLedger logic) ...
                    chore_brief = ChoreBrief(
                        chore_id=str(reqId),
                        security=Security(sec_id=barter.contract.localSymbol or barter.contract.symbol,
                                          inst_type=cls._map_ib_sec_type_to_instrument_type(barter.contract.secType)),
                        side=Side.BUY if barter.chore.action == "BUY" else Side.SELL,  # Simplified
                        underlying_account=barter.chore.account,
                        text=[f"IB Error Code {errorCode}: {errorString}"]
                    )
                    event_type = ChoreEventType.OE_BRK_REJ  # Default to broker reject for unhandled errors
                    # You can map specific IB error codes to your ChoreEventType more granularly here
                    # Example:
                    # if errorCode == 201: # "Chore rejected - Reason..."
                    #     event_type = ChoreEventType.OE_EXH_REJ # Or a more specific rejection type
                    # elif errorCode == 161: # "Cancel attempted when chore is not in a cancellable state"
                    #     event_type = ChoreEventType.OE_CXL_REJ # Or however you map this

                    logging.info(f"Attempting to create ChoreLedger entry for error on chore {reqId}")
                    chore_ledger_entry = ChoreLedger(
                        chore=chore_brief,
                        chore_event_date_time=DateTime.utcnow(),
                        chore_event=event_type
                    )
                    try:
                        await cls.chore_create_async_callable(chore_ledger_entry)
                    except Exception as e:
                        logging.error(f"Error calling chore_create_async_callable from _on_error: {e}", exc_info=True)

                else:
                    # If reqId > 0 but not in cache, it might be an error related to a request not an chore (e.g., market data)
                    logging.warning(
                        f"Error with reqId {reqId} (possibly not an choreId or chore not cached) - not creating ChoreLedger entry from _on_error.")

    @classmethod
    async def _on_disconnected(cls):
        logging.warning("Disconnected from IB TWS/Gateway.")
        cls._ib_connected = False

    @classmethod
    async def _get_ib_contract(cls, system_sec_id: str, symbol_type: str,
                               exchange: Optional[str] = "SMART",
                               currency: Optional[str] = None) -> Optional[Contract]:
        if not await cls._ensure_connected():
            logging.error(f"Cannot get IB contract for {system_sec_id}: Not connected.")
            return None
        if currency is None:
            currency = cls.DEFAULT_CURRENCY

        contract_to_qualify: Optional[Contract] = None
        if symbol_type.upper() == "STK":
            contract_to_qualify = Stock(system_sec_id, exchange, currency)
        elif symbol_type.upper() == "FUT":
            logging.warning(
                f"Future contract creation for {system_sec_id} is basic. May need more details (expiry, multiplier).")
            # For futures, you typically need an expiry (lastBarterDateOrContractMonth)
            # Example: contract_to_qualify = Future(system_sec_id, 'YYYYMM', exchange, currency=currency)
            # This will likely fail to qualify if system_sec_id isn't a localSymbol that implies expiry.
            contract_to_qualify = Future(symbol=system_sec_id, exchange=exchange, currency=currency)
        elif symbol_type.upper() == "OPT":
            logging.error(
                f"Option contract creation for {system_sec_id} is not fully implemented and needs right, strike, expiry.")
            return None  # Options require more details (right, strike, expiry)
        elif symbol_type.upper() == "FX" or symbol_type.upper() == "CASH":
            # Forex pairs are like 'EURUSD'. Currency is the quote currency.
            contract_to_qualify = Forex(system_sec_id, exchange="IDEALPRO",
                                        currency=currency.split('.')[-1] if '.' in currency else currency)
        else:
            logging.error(f"Unsupported symbol_type: {symbol_type} for IB contract creation.")
            return None

        if not contract_to_qualify:
            logging.error(f"Contract object failed to be created for {system_sec_id}")
            return None

        try:
            logging.info(f"Attempting to qualify contract: {contract_to_qualify} for sec_id {system_sec_id}")
            # Add a timeout for the qualifyContractsAsync call
            qualified_contracts = await asyncio.wait_for(
                cls._ib_instance.qualifyContractsAsync(contract_to_qualify),
                timeout=15.0  # 15-second timeout, adjust as needed
            )
            if qualified_contracts:
                logging.info(f"Successfully qualified contract: {qualified_contracts[0]}")
                return qualified_contracts[0]
            else:
                logging.error(
                    f"Could not qualify contract for {system_sec_id} ({symbol_type}) on {exchange} (returned empty list).")
                return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout (15s) occurred while qualifying contract {system_sec_id} for {contract_to_qualify}.",
                         exc_info=True)
            return None
        except Exception as e:
            logging.error(f"Exception qualifying contract {system_sec_id} for {contract_to_qualify}: {e}", exc_info=True)
            return None

    @classmethod
    def _map_ib_sec_type_to_instrument_type(cls, ib_sec_type: str) -> InstrumentType:  # [1]
        mapping = {
            "STK": InstrumentType.EQT,  # [1]
            "OPT": InstrumentType.OPT,  # [1]
            "FUT": InstrumentType.FUT,  # [1]
            "BOND": InstrumentType.BOND,  # [1]
            "CASH": InstrumentType.INDEX,  # [1]
            "IND": InstrumentType.INDEX,  # [1]
        }
        return mapping.get(ib_sec_type.upper(), InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED)  # [1]

    @classmethod
    def _map_side_to_ib_action(cls, side: Side) -> str:  # [1]
        if side == Side.BUY: return "BUY"  # [1]
        if side == Side.SELL: return "SELL"  # [1]
        if side == Side.SS: return "SELL"  # [1]
        raise ValueError(f"Unsupported side for IB mapping: {side}")

    @classmethod
    def _map_ib_status_to_chore_status_type(cls, ib_status: str) -> ChoreStatusType:
        # Based on street_book_n_post_book_n_basket_book_core_msgspec_model.ChoreStatusType
        if ib_status in [IBChoreStatus.PendingSubmit, IBChoreStatus.ApiPending]:  # [1]
            return ChoreStatusType.OE_UNACK
        elif ib_status in [IBChoreStatus.PreSubmitted, IBChoreStatus.Submitted]:  # [1]
            return ChoreStatusType.OE_ACKED
        elif ib_status == IBChoreStatus.PendingCancel:  # [1] # Explicitly a cancel request is unacked
            return ChoreStatusType.OE_CXL_UNACK
        elif ib_status == IBChoreStatus.ApiCancelled or ib_status == IBChoreStatus.Cancelled:  # [1] # Fully cancelled
            return ChoreStatusType.OE_DOD  # "Done for Day" can mean cancelled and off books
        elif ib_status == IBChoreStatus.Filled:  # [1]
            return ChoreStatusType.OE_FILLED
        elif ib_status == IBChoreStatus.Inactive:  # Often means rejected or lapsed, effectively DOD
            return ChoreStatusType.OE_DOD
        logging.warning(f"IB status '{ib_status}' has a basic mapping. Review for OE_OVER_FILLED etc.")
        # Default for other active (but not final) states
        return ChoreStatusType.OE_ACKED  # Default to ACKED for other live statuses not explicitly DOD/Filled/Unack

    @classmethod
    async def is_kill_switch_enabled(cls) -> bool:
        return cls._kill_switch_active

    @classmethod
    async def trigger_kill_switch(cls) -> bool:
        if not await cls._ensure_connected():
            logging.error("Cannot trigger kill switch: Not connected to IB.")
            return False
        cls._kill_switch_active = True
        logging.warning("Kill switch activated. New chores will be blocked. Attempting to cancel all open chores.")
        cancelled_count = 0
        failed_cxl_count = 0
        try:
            open_chores = await cls._ib_instance.reqOpenChoresAsync()  # [1]
            if not open_chores:
                logging.info("No open chores found to cancel.")
            else:
                logging.info(f"Found {len(open_chores)} open chores to cancel.")
            async with IBBarteringLink._chore_update_lock:
                for chore_obj in open_chores:  # Renamed to avoid conflict with Chore type
                    logging.info(
                        f"Attempting to cancel open chore ID: {chore_obj.chore.choreId}, Symbol: {chore_obj.contract.symbol}")  # [1]
                    barter_obj = cls._ib_instance.cancelChore(chore_obj.chore)  # [1] # Use chore_obj.chore
                    if barter_obj:
                        logging.info(
                            f"Cancel request sent for chore ID: {chore_obj.chore.choreId}. Status: {barter_obj.choreStatus.status}")  # [1]
                        cancelled_count += 1
                    else:
                        logging.error(f"Failed to send cancel request for chore ID: {chore_obj.chore.choreId}")  # [1]
                        failed_cxl_count += 1
            if failed_cxl_count > 0:
                logging.error(f"{failed_cxl_count} chores failed to initiate cancellation.")
            logging.info(f"Kill switch: {cancelled_count} cancel requests initiated.")
            return True
        except Exception as e:
            logging.error(f"Error during kill switch's chore cancellation process: {e}", exc_info=True)
            return True

    @classmethod
    async def revoke_kill_switch_n_resume_bartering(cls) -> bool:
        cls._kill_switch_active = False
        logging.info("Kill switch revoked. Bartering can resume.")
        return True

    @classmethod
    async def place_new_chore(cls, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
                              bartering_sec_type: str, account: str, exchange: str | None = None,
                              text: List[str] | None = None, client_ord_id: str | None = None,
                              **kwargs) -> Tuple[bool, str]:

        if cls._kill_switch_active:
            logging.warning("Kill switch is active. New chore placement blocked.")
            return False, "Kill switch active"
        if not await cls._ensure_connected():
            return False, "Not connected to IB"

        ib_contract = await cls._get_ib_contract(system_sec_id, bartering_sec_type, exchange)
        if not ib_contract:
            err_msg = f"Failed to get/qualify IB contract for {system_sec_id}"
            logging.error(err_msg)
            return False, err_msg

        ib_chore_obj = IBChore()  # Renamed to avoid conflict
        ib_chore_obj.action = cls._map_side_to_ib_action(side)
        chore_type = kwargs.get("chore_type", "LMT")
        ib_chore_obj.choreType = chore_type.upper()
        ib_chore_obj.totalQuantity = abs(int(qty))
        if ib_chore_obj.choreType == "LMT":
            if px is None or px <= 0:
                return False, "Limit price (px) must be positive for LMT chores."
            ib_chore_obj.lmtPrice = float(px)
        elif ib_chore_obj.choreType == "MKT":
            pass
        else:
            return False, f"Unsupported IB chore type: {ib_chore_obj.choreType}"

        tif = kwargs.get("tif", "GTC")
        ib_chore_obj.tif = tif.upper()
        ib_chore_obj.account = account
        ib_chore_obj.transmit = True
        outside_rth = kwargs.get("outside_rth", False)
        ib_chore_obj.outsideRth = outside_rth

        if client_ord_id:
            ib_chore_obj.choreRef = client_ord_id
        elif text:
            ib_chore_obj.choreRef = text[0] if isinstance(text, list) and text else str(text)

        try:
            logging.info(
                f"Placing IB Chore: {ib_chore_obj.action} {ib_chore_obj.totalQuantity} {ib_contract.symbol} "  # [1]
                f"@{ib_chore_obj.lmtPrice if ib_chore_obj.choreType == 'LMT' else 'MKT'}, "
                f"Type: {ib_chore_obj.choreType}, TIF: {ib_chore_obj.tif}, Account: {ib_chore_obj.account}, "
                f"ChoreRef: {ib_chore_obj.choreRef}")

            async with IBBarteringLink._chore_update_lock:
                barter_obj = cls._ib_instance.placeChore(ib_contract, ib_chore_obj)  # [1]
                if barter_obj and barter_obj.chore:  # [1]
                    await asyncio.sleep(0.5)
                    ib_assigned_chore_id = barter_obj.chore.choreId  # [1]
                    if ib_assigned_chore_id == 0 and barter_obj.chore.permId:  # [1]
                        logging.warning(
                            f"IB choreId is 0, using permId {barter_obj.chore.permId} as temporary reference.")  # [1]

                    if ib_assigned_chore_id != 0:
                        info_ = f"IB Chore placed. IB ChoreID: {ib_assigned_chore_id}, PermId: {barter_obj.chore.permId}, Status: {barter_obj.choreStatus.status}"
                        logging.info(info_)  # [1]
                        cls._active_chores_cache[ib_assigned_chore_id] = barter_obj  # [1]

                        chore_ledger_entry: ChoreLedger = cls.get_chore_ledger_obj_from_barter(barter_obj, force_ret=True)

                        if chore_ledger_entry:
                            # persisting chore update as ledger - creating new chore with event type OE_NEW
                            chore_ledger_entry.chore_event = ChoreEventType.OE_NEW
                            await IBBarteringLink.handle_chore_ledger_create(chore_ledger_entry)
                            sync_check = kwargs.get("sync_check")
                            if sync_check:
                                return True, f"{info_}---{str(ib_assigned_chore_id)}"
                            else:
                                return True, str(ib_assigned_chore_id)
                        else:
                            return False, (f"Something went wrong while creating chore ledger object from barter object - "
                                           f"chore placed but couldn't persist in db;;; {barter_obj=}")
                    elif barter_obj.choreStatus.status == 'Error':  # [1]
                        err_msg = f"IB chore placement resulted in error status. Check TWS logs. ChoreRef: {ib_chore_obj.choreRef}"
                        logging.error(err_msg)
                        return False, err_msg
                    else:
                        warn_msg = f"IB chore submitted but IB ChoreID not immediately available. ChoreRef: {ib_chore_obj.choreRef}. Status: {barter_obj.choreStatus.status}. Monitor events."  # [1]
                        logging.warning(warn_msg)
                        if barter_obj.chore.permId:  # [1]
                            chore_ledger_entry = cls.get_chore_ledger_obj_from_barter(barter_obj, force_ret=True)

                            if chore_ledger_entry:
                                # persisting chore update as ledger - creating new chore with event type OE_NEW
                                chore_ledger_entry.chore_event = ChoreEventType.OE_NEW
                                await IBBarteringLink.handle_chore_ledger_create(chore_ledger_entry)
                                sync_check = kwargs.get("sync_check")
                                if sync_check:
                                    return True, f"{warn_msg}---{str(ib_assigned_chore_id)}"
                                else:
                                    return True, str(ib_assigned_chore_id)
                            else:
                                return False, (
                                    f"Something went wrong while creating chore ledger object from barter object - "
                                    f"chore placed but couldn't persist in db;;; {barter_obj=}")
                        return False, "IB ChoreID not available after placement."
                else:
                    err_msg = "IB placeChore call did not return a barter object or barter.chore."
                    logging.error(err_msg)
                    return False, err_msg
        except Exception as e:
            logging.error(f"Exception placing IB chore for {system_sec_id}: {e}", exc_info=True)
            return False, str(e)

    @classmethod
    async def place_amend_chore(cls, chore_id: str, px: float | None = None, qty: int | None = None,
                                bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                bartering_sec_type: str | None = None) -> bool:
        if cls._kill_switch_active:
            logging.warning("Kill switch is active. Chore amendment blocked.")
            return False
        if not await cls._ensure_connected():
            logging.error("Cannot amend chore: Not connected to IB.")
            return False

        try:
            ib_chore_id_to_amend = int(chore_id)
        except ValueError:
            logging.error(f"Invalid chore_id format for amendment: '{chore_id}'. Must be an integer string.")
            return False

        async with cls._chore_update_lock:
            original_barter_obj = cls._active_chores_cache.get(ib_chore_id_to_amend)  # Renamed
            ib_contract_for_amend = None  # Initialize
            amended_ib_chore_obj = IBChore()  # Renamed

            if not original_barter_obj:
                logging.info(
                    f"Chore {ib_chore_id_to_amend} not in local cache. Attempting to find among open chores for amendment.")
                open_ib_chores = await cls._ib_instance.reqOpenChoresAsync()  # [1]
                found_chore_to_amend = None
                for o in open_ib_chores:
                    if o.chore.choreId == ib_chore_id_to_amend:  # [1]
                        found_chore_to_amend = o.chore  # [1]
                        ib_contract_for_amend = o.contract  # [1]
                        break
                if not found_chore_to_amend:
                    logging.error(f"Chore ID {ib_chore_id_to_amend} not found or not open for amendment.")
                    return False
                amended_ib_chore_obj.choreId = found_chore_to_amend.choreId  # [1]
                amended_ib_chore_obj.permId = found_chore_to_amend.permId  # [1]
                amended_ib_chore_obj.action = found_chore_to_amend.action  # [1]
                amended_ib_chore_obj.choreType = found_chore_to_amend.choreType  # [1]
                amended_ib_chore_obj.account = found_chore_to_amend.account  # [1]
                amended_ib_chore_obj.transmit = True
                amended_ib_chore_obj.outsideRth = found_chore_to_amend.outsideRth  # [1]
                amended_ib_chore_obj.tif = found_chore_to_amend.tif  # [1]
                amended_ib_chore_obj.lmtPrice = found_chore_to_amend.lmtPrice if found_chore_to_amend.choreType == "LMT" else None  # [1]
                amended_ib_chore_obj.totalQuantity = found_chore_to_amend.totalQuantity  # [1]
            else:
                ib_contract_for_amend = original_barter_obj.contract  # [1]
                amended_ib_chore_obj.choreId = original_barter_obj.chore.choreId  # [1]
                amended_ib_chore_obj.permId = original_barter_obj.chore.permId  # [1]
                amended_ib_chore_obj.action = original_barter_obj.chore.action  # [1]
                amended_ib_chore_obj.choreType = original_barter_obj.chore.choreType  # [1]
                amended_ib_chore_obj.totalQuantity = original_barter_obj.chore.totalQuantity  # [1]
                if amended_ib_chore_obj.choreType == "LMT":
                    amended_ib_chore_obj.lmtPrice = original_barter_obj.chore.lmtPrice  # [1]
                amended_ib_chore_obj.account = original_barter_obj.chore.account  # [1]
                amended_ib_chore_obj.transmit = True
                amended_ib_chore_obj.outsideRth = original_barter_obj.chore.outsideRth  # [1]
                amended_ib_chore_obj.tif = original_barter_obj.chore.tif  # [1]

            modified = False
            if px is not None and amended_ib_chore_obj.choreType == "LMT":
                if float(px) <= 0:
                    logging.error("Amended limit price must be positive.")
                    return False
                amended_ib_chore_obj.lmtPrice = float(px)
                modified = True
            if qty is not None:
                amended_ib_chore_obj.totalQuantity = abs(int(qty))
                modified = True

            if not modified:
                logging.info(f"No changes specified for amending chore {ib_chore_id_to_amend}.")
                return True

            try:
                logging.info(
                    f"Amending IB Chore ID: {amended_ib_chore_obj.choreId}. New Qty: {amended_ib_chore_obj.totalQuantity}, "
                    f"New Px: {amended_ib_chore_obj.lmtPrice if amended_ib_chore_obj.choreType == 'LMT' else 'N/A'}")
                barter_receipt = cls._ib_instance.placeChore(ib_contract_for_amend, amended_ib_chore_obj)  # [1]
                if barter_receipt:
                    logging.info(
                        f"Amend request for chore {ib_chore_id_to_amend} sent. New status: {barter_receipt.choreStatus.status}")  # [1]
                    cls._active_chores_cache[barter_receipt.chore.choreId] = barter_receipt  # [1]
                    return True
                else:
                    logging.error(f"IB placeChore for amendment of {ib_chore_id_to_amend} did not return a barter object.")
                    return False
            except Exception as e:
                logging.error(f"Exception amending IB chore {ib_chore_id_to_amend}: {e}", exc_info=True)
                return False

    @classmethod
    async def place_cxl_chore(cls, chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = None) -> bool:
        if not await cls._ensure_connected():
            logging.error("Cannot cancel chore: Not connected to IB.")
            return False
        try:
            ib_chore_id_to_cancel = int(chore_id)
        except ValueError:
            logging.error(f"Invalid chore_id format for cancellation: '{chore_id}'. Must be an integer string.")
            return False

        async with cls._chore_update_lock:
            target_barter_obj = cls._active_chores_cache.get(ib_chore_id_to_cancel)  # Renamed
            chore_to_cancel_ib_obj = None  # Renamed

            if target_barter_obj:
                chore_to_cancel_ib_obj = target_barter_obj.chore  # [1]
            else:
                logging.info(f"Chore {ib_chore_id_to_cancel} not in cache, querying open chores.")
                open_ib_chores = await cls._ib_instance.reqOpenChoresAsync()  # [1]
                for o_barter in open_ib_chores:
                    if o_barter.chore.choreId == ib_chore_id_to_cancel:  # [1]
                        chore_to_cancel_ib_obj = o_barter.chore  # [1]
                        break
            if not chore_to_cancel_ib_obj:
                logging.error(f"Chore ID {ib_chore_id_to_cancel} not found or not active for cancellation.")
                return False

            try:
                logging.info(f"Attempting to cancel IB Chore ID: {chore_to_cancel_ib_obj.choreId}")  # [1]
                cancelled_barter_obj = cls._ib_instance.cancelChore(chore_to_cancel_ib_obj)  # [1] Renamed
                if cancelled_barter_obj:
                    logging.info(
                        f"Cancel request for chore {chore_to_cancel_ib_obj.choreId} sent. Current reported status: {cancelled_barter_obj.choreStatus.status}")  # [1]
                    cls._active_chores_cache[cancelled_barter_obj.chore.choreId] = cancelled_barter_obj  # [1]
                    return True
                else:
                    logging.error(
                        f"IB cancelChore for {chore_to_cancel_ib_obj.choreId} did not return a barter object.")  # [1]
                    return False
            except Exception as e:
                logging.error(f"Exception cancelling IB chore {chore_to_cancel_ib_obj.choreId}: {e}", exc_info=True)  # [1]
                return False

    @classmethod
    async def is_chore_open(cls, chore_id: str) -> bool:
        if not await cls._ensure_connected():
            logging.error("Cannot check if chore is open: Not connected to IB.")
            return False
        try:
            ib_chore_id_check = int(chore_id)
        except ValueError:
            logging.error(f"Invalid chore_id format for status check: '{chore_id}'.")
            return False

        async with cls._chore_update_lock:  # Protect cache modification
            cached_barter_obj = cls._active_chores_cache.get(ib_chore_id_check)  # Renamed
        if cached_barter_obj and not cached_barter_obj.isDone():  # [1]
            logging.info(
                f"Chore {ib_chore_id_check} found in cache and is not done. Status: {cached_barter_obj.choreStatus.status}")  # [1]
            return True
        elif cached_barter_obj and cached_barter_obj.isDone():  # [1]
            logging.info(
                f"Chore {ib_chore_id_check} found in cache but is done. Status: {cached_barter_obj.choreStatus.status}")  # [1]
            return False

        try:
            logging.info(f"Chore {ib_chore_id_check} not in active cache or is done. Querying live open chores.")
            open_chores_live = await cls._ib_instance.reqOpenChoresAsync()  # [1]
            async with cls._chore_update_lock:  # Protect cache modification
                for o_barter in open_chores_live:
                    if o_barter.chore.choreId == ib_chore_id_check:  # [1]
                        cls._active_chores_cache[ib_chore_id_check] = o_barter  # [1]
                        if not o_barter.isDone():  # [1]
                            logging.info(
                                f"Chore {ib_chore_id_check} is open on IB. Status: {o_barter.choreStatus.status}")  # [1]
                            return True
                        else:
                            logging.info(
                                f"Chore {ib_chore_id_check} found in reqOpenChores but isDone(). Status: {o_barter.choreStatus.status}")  # [1]
                            return False
            logging.info(f"Chore {ib_chore_id_check} not found among live open chores.")
            return False
        except Exception as e:
            logging.error(f"Error querying open chores from IB: {e}", exc_info=True)
            return False

    @classmethod
    async def get_chore_status(
            cls, chore_id: str) -> Tuple[ChoreStatusType | None, str | None, int | None, float | None, int | None] | None:
        if not await cls._ensure_connected():
            logging.error("Cannot get chore status: Not connected to IB.")
            return None  # Return None as per base class definition for failure
        try:
            ib_chore_id_status = int(chore_id)
        except ValueError:
            logging.error(f"Invalid chore_id format for get_chore_status: '{chore_id}'.")
            # Returning a tuple with None values as a placeholder for error, though None itself is better
            return None, f"Invalid chore_id format: {chore_id}", None, None, None

        barter_obj = None
        async with cls._chore_update_lock:
            barter_obj = cls._active_chores_cache.get(ib_chore_id_status)

        if barter_obj:
            logging.info(
                f"Chore {ib_chore_id_status} found in cache. Status: {barter_obj.choreStatus.status}, Filled: {barter_obj.choreStatus.filled}")
            mapped_status = cls._map_ib_status_to_chore_status_type(barter_obj.choreStatus.status)
            chore_text = barter_obj.chore.choreRef
            filled_qty = int(barter_obj.choreStatus.filled)
            chore_px = barter_obj.chore.lmtPrice if barter_obj.chore.choreType == 'LMT' else None
            chore_qty = int(barter_obj.chore.totalQuantity)
            return mapped_status, chore_text, filled_qty, chore_px, chore_qty

        logging.info(f"Chore {ib_chore_id_status} not in cache. Requesting open chores and recent barters for status.")
        await cls._ib_instance.reqAllOpenChoresAsync()
        await asyncio.sleep(0.2)

        all_barters_from_ib = cls._ib_instance.barters()
        found_barter_obj_from_ib = None

        async with cls._chore_update_lock:
            barter_obj = cls._active_chores_cache.get(ib_chore_id_status)
            if barter_obj:
                logging.info(
                    f"Chore {ib_chore_id_status} found in cache after reqAllOpenChores. Status: {barter_obj.choreStatus.status}, Filled: {barter_obj.choreStatus.filled}")
                mapped_status = cls._map_ib_status_to_chore_status_type(barter_obj.choreStatus.status)
                chore_text = barter_obj.chore.choreRef
                filled_qty = int(barter_obj.choreStatus.filled)
                chore_px = barter_obj.chore.lmtPrice if barter_obj.chore.choreType == 'LMT' else None
                chore_qty = int(barter_obj.chore.totalQuantity)
                return mapped_status, chore_text, filled_qty, chore_px, chore_qty

            for t in all_barters_from_ib:
                if t.chore.choreId == ib_chore_id_status:
                    found_barter_obj_from_ib = t
                    cls._active_chores_cache[ib_chore_id_status] = t
                    break

        if found_barter_obj_from_ib:
            logging.info(
                f"Chore {ib_chore_id_status} found after querying IB. Status: {found_barter_obj_from_ib.choreStatus.status}, Filled: {found_barter_obj_from_ib.choreStatus.filled}")
            mapped_status = cls._map_ib_status_to_chore_status_type(found_barter_obj_from_ib.choreStatus.status)
            chore_text = found_barter_obj_from_ib.chore.choreRef
            filled_qty = int(found_barter_obj_from_ib.choreStatus.filled)
            chore_px = found_barter_obj_from_ib.chore.lmtPrice if found_barter_obj_from_ib.chore.choreType == 'LMT' else None
            chore_qty = int(found_barter_obj_from_ib.chore.totalQuantity)
            return mapped_status, chore_text, filled_qty, chore_px, chore_qty
        else:
            logging.warning(
                f"Chore ID {ib_chore_id_status} not found in active cache or after querying IB open/recent barters.")
            return None  # Chore not found

    @classmethod
    async def internal_chore_state_update(cls, chore_event: ChoreEventType, chore_id: str, side: Side | None = None,
                                          bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                          underlying_account: str | None = None, msg: str | None = None,
                                          px: float | None = None, qty: int | None = None) -> bool:
        if not cls.chore_create_async_callable:
            logging.warning("chore_create_async_callable not set. Cannot perform internal_chore_state_update.")
            return False

        sec = None
        if system_sec_id:
            inst_type_guess = InstrumentType.EQT  # [1]
            if bartering_sec_id and ("." in bartering_sec_id or len(bartering_sec_id) > 6):
                inst_type_guess = InstrumentType.FUT  # [1]
            sec = Security(sec_id=system_sec_id, inst_type=inst_type_guess)

        chore_brief = ChoreBrief(
            chore_id=chore_id,
            security=sec if sec else Security(sec_id="UNKNOWN", inst_type=InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED),
            # [1]
            bartering_security=Security(sec_id=bartering_sec_id if bartering_sec_id else "UNKNOWN",
                                      inst_type=sec.inst_type if sec else InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED) if bartering_sec_id else None,
            # [1]
            side=side if side else Side.SIDE_UNSPECIFIED,  # [1]
            px=px,
            qty=qty,
            underlying_account=underlying_account if underlying_account else "UNKNOWN",
            text=[msg] if msg else []
        )

        chore_ledger_entry = ChoreLedger(
            chore=chore_brief,
            chore_event_date_time=DateTime.utcnow(),
            chore_event=chore_event
        )

        try:
            await cls.chore_create_async_callable(chore_ledger_entry)
            logging.info(f"Internal chore state update processed for chore {chore_id}, event: {chore_event}.")
            return True
        except Exception as e:
            logging.error(f"Error during internal_chore_state_update's notification: {e}", exc_info=True)
            return False

    @classmethod
    async def process_chore_ack(cls, chore_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                                text: List[str] | None = None) -> bool:
        logging.warning(
            "process_chore_ack called on IBBarteringLink - IB handles ACKs via events. This call is likely redundant.")
        if cls.chore_create_async_callable:
            chore_brief_obj = ChoreBrief(chore_id=chore_id,
                                         security=Security(sec_id=sec_id, inst_type=InstrumentType.EQT),  # [1]
                                         side=side, px=px, qty=qty, underlying_account=underlying_account, text=text)
            ledger = ChoreLedger(chore=chore_brief_obj, chore_event_date_time=DateTime.utcnow(),
                                   chore_event=ChoreEventType.OE_ACK)
            await cls.chore_create_async_callable(ledger)
            return True
        return False

    @classmethod
    async def process_fill(cls, chore_id, px: float, qty: int, side: Side, sec_id: str,
                           underlying_account: str, fill_id: str = None,
                           fill_datetime: Optional[DateTime] = None) -> bool:
        logging.warning(
            "process_fill called on IBBarteringLink - IB handles deals via events. This call is likely redundant.")
        if cls.fill_create_async_callable:
            fill_ledger_entry = DealsLedger(
                chore_id=chore_id,
                fill_px=px,
                fill_qty=qty,
                fill_notional=px * qty,
                fill_symbol=sec_id,
                fill_bartering_symbol=sec_id,
                fill_side=side,
                underlying_account=underlying_account,
                fill_date_time=fill_datetime if fill_datetime else DateTime.utcnow(),
                fill_id=fill_id if fill_id else f"manual_fill_{DateTime.utcnow().timestamp()}",
            )
            await cls.fill_create_async_callable(fill_ledger_entry)
            return True
        return False

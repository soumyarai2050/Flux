# File: test_ib_bartering_link.py
import logging
import asyncio
import os
import pytest
import pytest_asyncio  # Ensures asyncio plugin is active
from unittest.mock import AsyncMock, MagicMock  # For mocking notification callables
from typing import Callable, Any
from pathlib import PurePath
import pendulum

# Assuming ib_bartering_link.py is in a location where it can be imported
# e.g., same directory or PYTHONPATH is set appropriately.
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.ib_bartering_link import IBBarteringLink
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link_base import BarteringLinkBase  # For type hinting if needed

# Import your own system's enums and models
from Flux.CodeGenProjects.AddressBook.ORMModel.barter_core_msgspec_model import InstrumentType, Side
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    ChoreLedger, DealsLedger, ChoreStatusType, ChoreEventType
)
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager

secrets_yaml_path = PurePath(__file__).parent.parent / "data" / "secrets.yaml"
secrets_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(secrets_yaml_path))

# --- Test Configuration ---
# IMPORTANT: Set this environment variable to your IB Paper Bartering Account ID
# PAPER_ACCOUNT_ID = os.environ.get("IB_PAPER_ACCOUNT_ID")
PAPER_ACCOUNT_ID = secrets_yaml_dict.get("PAPER_ACCOUNT_ID")
# Use a specific client ID for testing to avoid conflicts
TEST_CLIENT_ID_OFFSET = 200  # IBBarteringLink adds its own counter to this

# Skip tests if paper account ID is not configured
pytestmark = pytest.mark.skipif(not PAPER_ACCOUNT_ID, reason="IB_PAPER_ACCOUNT_ID environment variable not set")


@pytest.fixture(scope="module")
def event_loop():
    """Ensure an event loop is available for the module."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")  # Use "class" or "module" if connection is expensive
async def ib_link_setup_teardown():
    """Fixture to manage IBBarteringLink connection for tests."""
    # Mock the notification callables
    IBBarteringLink.chore_update_notification_callable = AsyncMock(spec=Callable[[ChoreLedger], Any])
    IBBarteringLink.fill_notification_callable = AsyncMock(spec=Callable[[DealsLedger], Any])

    # Use a specific client ID for testing
    connected = await IBBarteringLink._ensure_connected(client_id_offset=TEST_CLIENT_ID_OFFSET)
    if not connected:
        pytest.fail("Failed to connect to IB TWS/Gateway for testing. Ensure it's running and configured.")

    yield IBBarteringLink  # Provide the class, not an instance, as methods are classmethods

    # Teardown: Disconnect after all tests in the scope are done
    await IBBarteringLink.disconnect_ib()


@pytest.mark.usefixtures("ib_link_setup_teardown")
class TestIBBarteringLinkIntegration:

    @pytest.mark.asyncio
    async def test_connection_and_initial_kill_switch_status(self, ib_link_setup_teardown):
        link = ib_link_setup_teardown
        assert link._ib_connected is True, "IB link should be connected"
        assert await link.is_kill_switch_enabled() is False, "Kill switch should be disabled initially"

    @pytest.mark.asyncio
    async def test_place_new_limit_chore_and_status_check(self, ib_link_setup_teardown):
        link: IBBarteringLink = ib_link_setup_teardown()
        link.chore_update_notification_callable.reset_mock()

        symbol = "AAPL"  # Use a liquid stock
        px = 100.01  # Far from market to avoid immediate fill for status check
        qty = 1
        side_val = Side.BUY
        client_ord_id = f"pytest_new_{pendulum.now().timestamp()}"

        success, chore_id_str = await link.place_new_chore(
            px=px, qty=qty, side=side_val,
            bartering_sec_id=symbol, system_sec_id=symbol, symbol_type="STK",
            account=PAPER_ACCOUNT_ID, exchange="SMART",
            client_ord_id=client_ord_id,
            text=["Pytest new chore"]
        )

        assert success is True, f"Placing new chore failed: {chore_id_str}"
        assert chore_id_str is not None and "PENDING" not in chore_id_str, f"Invalid chore ID received: {chore_id_str}"
        ib_chore_id = int(chore_id_str)  # IB chore IDs are integers

        # Allow TWS some time to process
        await asyncio.sleep(2)

        is_open = await link.is_chore_open(chore_id_str)
        assert is_open is True, f"Chore {ib_chore_id} should be open"

        status, text_msg, filled_qty = await link.get_chore_status(chore_id_str)
        assert status is not None, f"Could not get status for chore {ib_chore_id}: {text_msg}"
        # Initial status could be Submitted, PreSubmitted, or Acked
        assert status in [ChoreStatusType.OE_ACKED,
                          ChoreStatusType.OE_UNACK], f"Unexpected initial chore status: {status.value}"
        assert filled_qty == 0, f"Chore {ib_chore_id} should have 0 filled quantity initially"

        # Check if chore update callback was hit (at least once for ack/submit)
        # assert link.chore_update_notification_callable.called, "Chore update callback was not called"
        # You can add more specific assertions on the callback arguments if needed

        # Cleanup: Cancel the chore
        cancel_success = await link.place_cxl_chore(chore_id_str)
        assert cancel_success is True, f"Failed to cancel chore {ib_chore_id}"
        await asyncio.sleep(1)  # Allow cancel to process
        final_status, _, _ = await link.get_chore_status(chore_id_str)
        assert final_status == ChoreStatusType.OE_DOD, f"Chore status after cancel should be DOD (Done for Day/Cancelled), got {final_status.value if final_status else 'None'}"

    @pytest.mark.asyncio
    async def test_place_market_chore_and_potential_fill(self, ib_link_setup_teardown):
        link: IBBarteringLink = ib_link_setup_teardown
        link.chore_update_notification_callable.reset_mock()
        link.fill_notification_callable.reset_mock()

        logger = logging.getLogger(__name__)  # For logging within the test
        logger.info(f"DEBUG: Type of fill_notification_callable: {type(link.fill_notification_callable)}")

        symbol = "SPY"  # Highly liquid ETF
        qty = 1
        side_val = Side.BUY
        client_ord_id = f"pytest_mkt_{pendulum.now().timestamp()}"

        success, chore_id_str = await link.place_new_chore(
            px=0,  # Not used for MKT
            qty=qty, side=side_val,
            bartering_sec_id=symbol, system_sec_id=symbol, symbol_type="STK",
            account=PAPER_ACCOUNT_ID, exchange="SMART",
            client_ord_id=client_ord_id,
            chore_type="MKT",  # Market Chore
            text=["Pytest market chore"]
        )
        assert success is True, f"Placing market chore failed: {chore_id_str}"
        assert chore_id_str is not None and "PENDING" not in chore_id_str

        # --- Use polling wait instead of wait_for_call ---
        logger.info(f"Waiting for fill notification for MKT chore {chore_id_str}...")
        max_wait_time = 15.0  # seconds for MKT fill
        poll_interval = 0.2  # seconds
        waited_time = 0.0
        fill_callback_was_called = False
        while waited_time < max_wait_time:
            if link.fill_notification_callable.called:
                fill_callback_was_called = True
                logger.info(f"Fill notification received for chore {chore_id_str}.")
                break
            await asyncio.sleep(poll_interval)
            waited_time += poll_interval

        if not fill_callback_was_called:
            logger.warning(
                f"Timeout or no fill: Fill notification_callable was not called within {max_wait_time}s for MKT chore {chore_id_str}.")
            # The test might still pass if the chore is just 'Submitted' or 'Acked' but not filled in paper bartering time
            # For a MKT chore, we ideally expect a fill. If not, TWS logs or paper bartering behavior might be why.
        # --- End of polling wait ---

        status, _, filled_qty_val = await link.get_chore_status(chore_id_str)
        if status == ChoreStatusType.OE_FILLED:
            # assert fill_callback_was_called, "fill_notification_callable should have been called for a filled MKT chore"
            assert filled_qty_val == qty, f"Filled quantity for MKT chore {chore_id_str} should be {qty}, got {filled_qty_val}"
            # You can add more detailed checks on the fill_notification_callable.call_args here
            # For example:
            # call_args_list = link.fill_notification_callable.call_args_list
            # assert len(call_args_list) > 0
            # first_call_args = call_args_list[0]
            # deals_ledger_obj = first_call_args[0][0] # Assuming it's called as callable(DealsLedger_instance)
            # assert deals_ledger_obj.fill_qty == qty
            # assert deals_ledger_obj.chore_id == chore_id_str

        elif fill_callback_was_called:  # Callback was called, but status isn't OE_FILLED yet
            logger.warning(
                f"Fill callback was called for {chore_id_str}, but final status is {status.value if status else 'None'}. "
                f"This might be due to partial deals or status update latency.")
            # Depending on strictness, you might still want to assert filled_qty_val > 0 if any fill happened
        else:  # No fill callback and not OE_FILLED
            logger.warning(
                f"MKT chore {chore_id_str} was not filled within test timeout. Final status: {status.value if status else 'None'}. "
                f"Filled Qty: {filled_qty_val}. Check paper bartering conditions or TWS logs.")
            # For a MKT chore, if it doesn't fill, it should at least be acked if markets are open.
            # If markets are closed for SPY, it might be PeningSubmit or Submitted.
            assert status in [ChoreStatusType.OE_ACKED, ChoreStatusType.OE_UNACK], \
                f"MKT chore {chore_id_str} status unexpected if not filled: {status.value if status else 'None'}"

        # No explicit cancel needed if MKT chore deals or expires.

    @pytest.mark.asyncio
    async def test_amend_and_cancel_chore(self, ib_link_setup_teardown):
        link: IBBarteringLink = ib_link_setup_teardown
        symbol = "MSFT"
        client_ord_id = f"pytest_amend_cxl_{pendulum.now().timestamp()}"

        # 1. Place an chore far from market
        success, chore_id_str = await link.place_new_chore(
            px=50.01, qty=5, side=Side.BUY, bartering_sec_id=symbol, system_sec_id=symbol,
            symbol_type="STK", account=PAPER_ACCOUNT_ID, exchange="SMART", client_ord_id=client_ord_id
        )
        assert success and chore_id_str is not None
        await asyncio.sleep(1.5)  # Let TWS process it

        # 2. Amend the chore (e.g., change price and quantity)
        amend_success = await link.place_amend_chore(chore_id=chore_id_str, px=51.01, qty=3)
        assert amend_success is True, f"Failed to amend chore {chore_id_str}"
        await asyncio.sleep(1.5)  # Let amend process

        status_after_amend, _, filled_after_amend = await link.get_chore_status(chore_id_str)
        # Note: Verifying the exact parameters of an amend via get_chore_status can be tricky
        # as it depends on how IB reports the 'current' state of an chore that has pending amends.
        # The key is that the amend request was accepted by TWS.
        # The choreStatusEvent callback would give more granular updates on the amend ack.
        assert status_after_amend != ChoreStatusType.OE_FILLED, "Chore should not be filled after amend to far price"
        # A more robust check would be to see if the chore details in TWS reflect the change,
        # or inspect the chore object in _active_chores_cache if possible.

        # 3. Cancel the chore
        cancel_success = await link.place_cxl_chore(chore_id=chore_id_str)
        assert cancel_success is True, f"Failed to cancel amended chore {chore_id_str}"
        await asyncio.sleep(1.5)

        assert await link.is_chore_open(chore_id_str) is False, "Chore should be closed after cancellation"
        final_status, _, _ = await link.get_chore_status(chore_id_str)
        assert final_status == ChoreStatusType.OE_DOD, f"Chore status after cancel should be DOD, got {final_status.value if final_status else 'None'}"

    @pytest.mark.asyncio
    async def test_kill_switch_functionality(self, ib_link_setup_teardown):
        link: IBBarteringLink = ib_link_setup_teardown

        # Ensure it's off initially (might have been set by previous test if scope is module and it failed)
        if await link.is_kill_switch_enabled():  # If leftover from a failed test
            await link.revoke_kill_switch_n_resume_bartering()
        assert await link.is_kill_switch_enabled() is False

        # Trigger kill switch
        trigger_success = await link.trigger_kill_switch()
        assert trigger_success is True
        assert await link.is_kill_switch_enabled() is True

        # Attempt to place an chore (should fail)
        success_killed, msg_killed = await link.place_new_chore(
            px=10.00, qty=1, side=Side.BUY, bartering_sec_id="GE", system_sec_id="GE",
            symbol_type="STK", account=PAPER_ACCOUNT_ID, exchange="SMART",
            client_ord_id="pytest_killed"
        )
        assert success_killed is False
        assert "Kill switch active" in msg_killed

        # Revoke kill switch
        revoke_success = await link.revoke_kill_switch_n_resume_bartering()
        assert revoke_success is True
        assert await link.is_kill_switch_enabled() is False
        await asyncio.sleep(1)  # Add a small delay (0.5 to 1 second)

        # Attempt to place an chore again (should succeed)
        # Cleanup this chore afterwards
        success_resumed, chore_id_resumed = await link.place_new_chore(
            px=10.01, qty=1, side=Side.BUY, bartering_sec_id="GE", system_sec_id="GE",
            symbol_type="STK", account=PAPER_ACCOUNT_ID, exchange="SMART",
            client_ord_id="pytest_resumed"
        )
        assert success_resumed is True
        if chore_id_resumed and "PENDING" not in chore_id_resumed:
            await asyncio.sleep(1)
            await link.place_cxl_chore(chore_id_resumed)  # Cleanup

    @pytest.mark.asyncio
    async def test_get_status_for_non_existent_chore(self, ib_link_setup_teardown):
        link: IBBarteringLink = ib_link_setup_teardown
        non_existent_chore_id = "999999999"  # Highly unlikely to exist

        is_open = await link.is_chore_open(non_existent_chore_id)
        assert is_open is False

        status, text_msg, filled_qty = await link.get_chore_status(non_existent_chore_id)
        assert status is None
        assert text_msg == "Chore not found"  # Or similar based on your implementation
        assert filled_qty is None

# Example of how to run from command line:
# IB_PAPER_ACCOUNT_ID=your_paper_id pytest -s -v test_ib_bartering_link.py
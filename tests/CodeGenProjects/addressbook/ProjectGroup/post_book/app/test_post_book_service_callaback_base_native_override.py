# standard imports
import time
from typing import List, Dict, Any
import os
from threading import Thread, Semaphore

os.environ["DBType"] = "beanie"
# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.post_book.app.post_book_service_routes_callback_base_native_override import (
    PostBookServiceRoutesCallbackBaseNativeOverride, ContainerObject, OrderJournalBaseModel,
    OrderSnapshotBaseModel, StratBriefBaseModel)


class MockContainerObject(ContainerObject):
    order_journals: List[OrderJournalBaseModel]
    order_snapshots: List[OrderSnapshotBaseModel]
    strat_brief: StratBriefBaseModel | None = None


class MockPostBookServiceRoutesCallbackBaseNativeOverride(
        PostBookServiceRoutesCallbackBaseNativeOverride):

    def __init__(self):
        super().__init__()
        self.container_model = MockContainerObject
        self.wait_semaphore = Semaphore()
        self.expected_strat_id_list: List[int] = []
        self.expected_strat_id_to_container_obj_dict: Dict[int, MockContainerObject] = {}
        self.found_strat_id_list: List[int] | None = None
        self.found_strat_id_to_container_obj_dict: Dict[int, MockContainerObject] | None = None
        self.is_strat_id_list: bool | None = None
        self.is_expected_strat_id_to_container_obj_dict: bool | None = None

    def update_strat_id_list_n_dict_from_payload(self, strat_id_list: List[int],
                                                 strat_id_to_container_obj_dict: Dict[int, MockContainerObject],
                                                 payload_dict: Dict[str, Any]):
        # delay for queue to get loaded when current fetched data is processing
        self.wait_semaphore.release()
        super().update_strat_id_list_n_dict_from_payload(strat_id_list, strat_id_to_container_obj_dict, payload_dict)

    def _get_order_journal_from_payload(self, payload_dict: Dict[str, Any]):
        order_journal: OrderJournalBaseModel | None = None
        if (order_journal_dict := payload_dict.get("order_journal")) is not None:
            order_journal = OrderJournalBaseModel(**order_journal_dict)
        # else not required: Fills update doesn't contain order_journal
        return order_journal

    def _get_order_snapshot_from_payload(self, payload_dict: Dict[str, Any]):
        order_snapshot: OrderSnapshotBaseModel | None = None
        if (order_snapshot_dict := payload_dict.get("order_snapshot")) is not None:
            order_snapshot = OrderSnapshotBaseModel(**order_snapshot_dict)
        return order_snapshot

    def _get_strat_brief_from_payload(self, payload_dict: Dict[str, Any]):
        strat_brief: StratBriefBaseModel | None = None
        if (strat_brief_dict := payload_dict.get("strat_brief")) is not None:
            strat_brief = StratBriefBaseModel(**strat_brief_dict)
        return strat_brief

    def _portfolio_limit_check_queue_handler(self, strat_id_list: List[int],
                                             strat_id_to_container_obj_dict: Dict[int, MockContainerObject]):
        self.is_strat_id_list = (strat_id_list == self.expected_strat_id_list)
        self.is_expected_strat_id_to_container_obj_dict = \
            (strat_id_to_container_obj_dict == self.expected_strat_id_to_container_obj_dict)
        self.found_strat_id_list = strat_id_list
        self.found_strat_id_to_container_obj_dict = strat_id_to_container_obj_dict


def test_queue_handling(single_strat_single_data, single_strat_multi_data,
                        multi_strat_single_data, multi_strat_multi_data):
    mock_post_book_override = MockPostBookServiceRoutesCallbackBaseNativeOverride()
    Thread(target=mock_post_book_override.portfolio_limit_check_queue_handler, daemon=True).start()

    # Checking single strat single data
    mock_post_book_override.expected_strat_id_list = [1]
    order_journal = OrderJournalBaseModel(**single_strat_single_data[0].get("order_journal"))
    order_snapshot = OrderSnapshotBaseModel(**single_strat_single_data[0].get("order_snapshot"))
    strat_brief = StratBriefBaseModel(**single_strat_single_data[0].get("strat_brief"))
    container_obj = MockContainerObject(order_journals=[order_journal],
                                        order_snapshots=[order_snapshot],
                                        strat_brief=strat_brief)
    mock_post_book_override.expected_strat_id_to_container_obj_dict = {1: container_obj}
    # updating queue
    mock_post_book_override.portfolio_limit_check_queue.put(single_strat_single_data[0])
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_strat_id_list, \
        (f"Mismatched: expected strat_id_list: {mock_post_book_override.expected_strat_id_list}, "
         f"found: {mock_post_book_override.found_strat_id_list}")
    assert mock_post_book_override.is_expected_strat_id_to_container_obj_dict, \
        (f"Mismatched: expected strat_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_strat_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_strat_id_to_container_obj_dict}")

    # Checking single strat multi data
    mock_post_book_override.expected_strat_id_list.clear()
    mock_post_book_override.expected_strat_id_to_container_obj_dict.clear()
    mock_post_book_override.is_strat_id_list = False
    mock_post_book_override.is_expected_strat_id_to_container_obj_dict = False
    mock_post_book_override.expected_strat_id_list = [1]
    order_journal_list = []
    order_snapshot_list = []
    strat_brief: StratBriefBaseModel | None = None

    for payload in single_strat_multi_data:
        order_journal_list.append(OrderJournalBaseModel(**payload.get("order_journal")))
        order_snapshot_list.append(OrderSnapshotBaseModel(**payload.get("order_snapshot")))
        strat_brief = StratBriefBaseModel(**payload.get("strat_brief"))
    container_obj = MockContainerObject(order_journals=order_journal_list,
                                        order_snapshots=order_snapshot_list,
                                        strat_brief=strat_brief)
    mock_post_book_override.expected_strat_id_to_container_obj_dict = {1: container_obj}
    # updating queue
    for payload in single_strat_multi_data:
        mock_post_book_override.portfolio_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_strat_id_list, \
        (f"Mismatched: expected strat_id_list: {mock_post_book_override.expected_strat_id_list}, "
         f"found: {mock_post_book_override.found_strat_id_list}")
    assert mock_post_book_override.is_expected_strat_id_to_container_obj_dict, \
        (f"Mismatched: expected strat_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_strat_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_strat_id_to_container_obj_dict}")

    # Checking multi strat single data
    mock_post_book_override.expected_strat_id_list.clear()
    mock_post_book_override.expected_strat_id_to_container_obj_dict.clear()
    mock_post_book_override.is_strat_id_list = False
    mock_post_book_override.is_expected_strat_id_to_container_obj_dict = False
    mock_post_book_override.expected_strat_id_list = [1, 2, 3, 4, 5]
    for payload in multi_strat_single_data:
        strat_id = payload.get("strat_id")
        order_journal = OrderJournalBaseModel(**payload.get("order_journal"))
        order_snapshot = OrderSnapshotBaseModel(**payload.get("order_snapshot"))
        strat_brief = StratBriefBaseModel(**payload.get("strat_brief"))
        container_obj = MockContainerObject(order_journals=[order_journal],
                                            order_snapshots=[order_snapshot],
                                            strat_brief=strat_brief)
        mock_post_book_override.expected_strat_id_to_container_obj_dict[strat_id] = container_obj
    # updating queue
    for payload in multi_strat_single_data:
        mock_post_book_override.portfolio_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_strat_id_list, \
        (f"Mismatched: expected strat_id_list: {mock_post_book_override.expected_strat_id_list}, "
         f"found: {mock_post_book_override.found_strat_id_list}")
    assert mock_post_book_override.is_expected_strat_id_to_container_obj_dict, \
        (f"Mismatched: expected strat_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_strat_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_strat_id_to_container_obj_dict}")

    # Checking multi strat multi data
    mock_post_book_override.expected_strat_id_list.clear()
    mock_post_book_override.expected_strat_id_to_container_obj_dict.clear()
    mock_post_book_override.is_strat_id_list = False
    mock_post_book_override.is_expected_strat_id_to_container_obj_dict = False
    mock_post_book_override.expected_strat_id_list = [1, 2, 3, 4, 5]

    for payload in multi_strat_multi_data:
        strat_id = payload.get("strat_id")
        order_journal = OrderJournalBaseModel(**payload.get("order_journal"))
        order_snapshot = OrderSnapshotBaseModel(**payload.get("order_snapshot"))
        strat_brief = StratBriefBaseModel(**payload.get("strat_brief"))

        container_obj = mock_post_book_override.expected_strat_id_to_container_obj_dict.get(strat_id)
        if container_obj is None:
            container_obj = MockContainerObject(order_journals=[order_journal],
                                                order_snapshots=[order_snapshot],
                                                strat_brief=strat_brief)
        else:
            container_obj.order_journals.append(order_journal)
            container_obj.order_snapshots.append(order_snapshot)
            container_obj.strat_brief = strat_brief
        mock_post_book_override.expected_strat_id_to_container_obj_dict[strat_id] = container_obj

    # updating queue
    for payload in multi_strat_multi_data:
        mock_post_book_override.portfolio_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_strat_id_list, \
        (f"Mismatched: expected strat_id_list: {mock_post_book_override.expected_strat_id_list}, "
         f"found: {mock_post_book_override.found_strat_id_list}")
    assert mock_post_book_override.is_expected_strat_id_to_container_obj_dict, \
        (f"Mismatched: expected strat_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_strat_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_strat_id_to_container_obj_dict}")

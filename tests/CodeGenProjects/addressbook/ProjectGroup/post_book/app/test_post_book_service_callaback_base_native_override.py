# standard imports
import time
from typing import List, Dict, Any
import os
from threading import Thread, Semaphore

os.environ["DBType"] = "beanie"
# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_routes_callback_base_native_override import (
    PostBookServiceRoutesCallbackBaseNativeOverride, ContainerObject, ChoreJournalBaseModel,
    ChoreSnapshotBaseModel, PlanBriefBaseModel)


class MockContainerObject(ContainerObject):
    chore_journals: List[ChoreJournalBaseModel]
    chore_snapshots: List[ChoreSnapshotBaseModel]
    plan_brief: PlanBriefBaseModel | None = None


class MockPostBookServiceRoutesCallbackBaseNativeOverride(
        PostBookServiceRoutesCallbackBaseNativeOverride):

    def __init__(self):
        super().__init__()
        self.container_model = MockContainerObject
        self.wait_semaphore = Semaphore()
        self.expected_plan_id_list: List[int] = []
        self.expected_plan_id_to_container_obj_dict: Dict[int, MockContainerObject] = {}
        self.found_plan_id_list: List[int] | None = None
        self.found_plan_id_to_container_obj_dict: Dict[int, MockContainerObject] | None = None
        self.is_plan_id_list: bool | None = None
        self.is_expected_plan_id_to_container_obj_dict: bool | None = None

    def update_plan_id_list_n_dict_from_payload(self, plan_id_list: List[int],
                                                 plan_id_to_container_obj_dict: Dict[int, MockContainerObject],
                                                 payload_dict: Dict[str, Any]):
        # delay for queue to get loaded when current fetched data is processing
        self.wait_semaphore.release()
        super().update_plan_id_list_n_dict_from_payload(plan_id_list, plan_id_to_container_obj_dict, payload_dict)

    def _get_chore_journal_from_payload(self, payload_dict: Dict[str, Any]):
        chore_journal: ChoreJournalBaseModel | None = None
        if (chore_journal_dict := payload_dict.get("chore_journal")) is not None:
            chore_journal = ChoreJournalBaseModel(**chore_journal_dict)
        # else not required: Fills update doesn't contain chore_journal
        return chore_journal

    def _get_chore_snapshot_from_payload(self, payload_dict: Dict[str, Any]):
        chore_snapshot: ChoreSnapshotBaseModel | None = None
        if (chore_snapshot_dict := payload_dict.get("chore_snapshot")) is not None:
            chore_snapshot = ChoreSnapshotBaseModel(**chore_snapshot_dict)
        return chore_snapshot

    def _get_plan_brief_from_payload(self, payload_dict: Dict[str, Any]):
        plan_brief: PlanBriefBaseModel | None = None
        if (plan_brief_dict := payload_dict.get("plan_brief")) is not None:
            plan_brief = PlanBriefBaseModel(**plan_brief_dict)
        return plan_brief

    def _contact_limit_check_queue_handler(self, plan_id_list: List[int],
                                             plan_id_to_container_obj_dict: Dict[int, MockContainerObject]):
        self.is_plan_id_list = (plan_id_list == self.expected_plan_id_list)
        self.is_expected_plan_id_to_container_obj_dict = \
            (plan_id_to_container_obj_dict == self.expected_plan_id_to_container_obj_dict)
        self.found_plan_id_list = plan_id_list
        self.found_plan_id_to_container_obj_dict = plan_id_to_container_obj_dict


def test_queue_handling(single_plan_single_data, single_plan_multi_data,
                        multi_plan_single_data, multi_plan_multi_data):
    mock_post_book_override = MockPostBookServiceRoutesCallbackBaseNativeOverride()
    Thread(target=mock_post_book_override.contact_limit_check_queue_handler, daemon=True).start()

    # Checking single plan single data
    mock_post_book_override.expected_plan_id_list = [1]
    chore_journal = ChoreJournalBaseModel(**single_plan_single_data[0].get("chore_journal"))
    chore_snapshot = ChoreSnapshotBaseModel(**single_plan_single_data[0].get("chore_snapshot"))
    plan_brief = PlanBriefBaseModel(**single_plan_single_data[0].get("plan_brief"))
    container_obj = MockContainerObject(chore_journals=[chore_journal],
                                        chore_snapshots=[chore_snapshot],
                                        plan_brief=plan_brief)
    mock_post_book_override.expected_plan_id_to_container_obj_dict = {1: container_obj}
    # updating queue
    mock_post_book_override.contact_limit_check_queue.put(single_plan_single_data[0])
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_plan_id_list, \
        (f"Mismatched: expected plan_id_list: {mock_post_book_override.expected_plan_id_list}, "
         f"found: {mock_post_book_override.found_plan_id_list}")
    assert mock_post_book_override.is_expected_plan_id_to_container_obj_dict, \
        (f"Mismatched: expected plan_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_plan_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_plan_id_to_container_obj_dict}")

    # Checking single plan multi data
    mock_post_book_override.expected_plan_id_list.clear()
    mock_post_book_override.expected_plan_id_to_container_obj_dict.clear()
    mock_post_book_override.is_plan_id_list = False
    mock_post_book_override.is_expected_plan_id_to_container_obj_dict = False
    mock_post_book_override.expected_plan_id_list = [1]
    chore_journal_list = []
    chore_snapshot_list = []
    plan_brief: PlanBriefBaseModel | None = None

    for payload in single_plan_multi_data:
        chore_journal_list.append(ChoreJournalBaseModel(**payload.get("chore_journal")))
        chore_snapshot_list.append(ChoreSnapshotBaseModel(**payload.get("chore_snapshot")))
        plan_brief = PlanBriefBaseModel(**payload.get("plan_brief"))
    container_obj = MockContainerObject(chore_journals=chore_journal_list,
                                        chore_snapshots=chore_snapshot_list,
                                        plan_brief=plan_brief)
    mock_post_book_override.expected_plan_id_to_container_obj_dict = {1: container_obj}
    # updating queue
    for payload in single_plan_multi_data:
        mock_post_book_override.contact_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_plan_id_list, \
        (f"Mismatched: expected plan_id_list: {mock_post_book_override.expected_plan_id_list}, "
         f"found: {mock_post_book_override.found_plan_id_list}")
    assert mock_post_book_override.is_expected_plan_id_to_container_obj_dict, \
        (f"Mismatched: expected plan_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_plan_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_plan_id_to_container_obj_dict}")

    # Checking multi plan single data
    mock_post_book_override.expected_plan_id_list.clear()
    mock_post_book_override.expected_plan_id_to_container_obj_dict.clear()
    mock_post_book_override.is_plan_id_list = False
    mock_post_book_override.is_expected_plan_id_to_container_obj_dict = False
    mock_post_book_override.expected_plan_id_list = [1, 2, 3, 4, 5]
    for payload in multi_plan_single_data:
        plan_id = payload.get("plan_id")
        chore_journal = ChoreJournalBaseModel(**payload.get("chore_journal"))
        chore_snapshot = ChoreSnapshotBaseModel(**payload.get("chore_snapshot"))
        plan_brief = PlanBriefBaseModel(**payload.get("plan_brief"))
        container_obj = MockContainerObject(chore_journals=[chore_journal],
                                            chore_snapshots=[chore_snapshot],
                                            plan_brief=plan_brief)
        mock_post_book_override.expected_plan_id_to_container_obj_dict[plan_id] = container_obj
    # updating queue
    for payload in multi_plan_single_data:
        mock_post_book_override.contact_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_plan_id_list, \
        (f"Mismatched: expected plan_id_list: {mock_post_book_override.expected_plan_id_list}, "
         f"found: {mock_post_book_override.found_plan_id_list}")
    assert mock_post_book_override.is_expected_plan_id_to_container_obj_dict, \
        (f"Mismatched: expected plan_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_plan_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_plan_id_to_container_obj_dict}")

    # Checking multi plan multi data
    mock_post_book_override.expected_plan_id_list.clear()
    mock_post_book_override.expected_plan_id_to_container_obj_dict.clear()
    mock_post_book_override.is_plan_id_list = False
    mock_post_book_override.is_expected_plan_id_to_container_obj_dict = False
    mock_post_book_override.expected_plan_id_list = [1, 2, 3, 4, 5]

    for payload in multi_plan_multi_data:
        plan_id = payload.get("plan_id")
        chore_journal = ChoreJournalBaseModel(**payload.get("chore_journal"))
        chore_snapshot = ChoreSnapshotBaseModel(**payload.get("chore_snapshot"))
        plan_brief = PlanBriefBaseModel(**payload.get("plan_brief"))

        container_obj = mock_post_book_override.expected_plan_id_to_container_obj_dict.get(plan_id)
        if container_obj is None:
            container_obj = MockContainerObject(chore_journals=[chore_journal],
                                                chore_snapshots=[chore_snapshot],
                                                plan_brief=plan_brief)
        else:
            container_obj.chore_journals.append(chore_journal)
            container_obj.chore_snapshots.append(chore_snapshot)
            container_obj.plan_brief = plan_brief
        mock_post_book_override.expected_plan_id_to_container_obj_dict[plan_id] = container_obj

    # updating queue
    for payload in multi_plan_multi_data:
        mock_post_book_override.contact_limit_check_queue.put(payload)
    mock_post_book_override.wait_semaphore.acquire()
    time.sleep(2)

    assert mock_post_book_override.is_plan_id_list, \
        (f"Mismatched: expected plan_id_list: {mock_post_book_override.expected_plan_id_list}, "
         f"found: {mock_post_book_override.found_plan_id_list}")
    assert mock_post_book_override.is_expected_plan_id_to_container_obj_dict, \
        (f"Mismatched: expected plan_id_to_container_obj_dict: "
         f"{mock_post_book_override.expected_plan_id_to_container_obj_dict}, "
         f"found: {mock_post_book_override.found_plan_id_to_container_obj_dict}")

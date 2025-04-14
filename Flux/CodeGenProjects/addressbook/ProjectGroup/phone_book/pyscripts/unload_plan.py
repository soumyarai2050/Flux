# standard imports
import logging
import datetime
import sys
import time

# project imports
from FluxPythonUtils.scripts.general_utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.pyscripts.utility_functions import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    UpdateType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import plan_view_client_call_log_str


def main():

    # read plan_id from args
    args: List[str] = sys.argv[1:]
    if len(args) > 3:   # 3rd argument can be & for background run
        err_str_ = f"Invalid number of arguments, received: {len(args)=};;;{args=}"
        logging.error(err_str_)
        raise Exception(err_str_)

    plan_id: int = int(args[0])

    datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
    configure_logger(logging.DEBUG, str(PAIR_STRAT_ENGINE_LOG_DIR), f"unload_plan_{plan_id}_{datetime_str}.log")

    force_flag: bool = False
    if len(args) >= 2 and args[1] == "--force":
        force_flag = True
    try:
        logging.warning(f"Triggered unload for {plan_id=}, {force_flag=}")
        unload_plan(plan_id, force_flag)
    except Exception as e:
        err_str_ = f"Failed to unload plan with {plan_id=}, {force_flag=}, exception: {e}"
        logging.error(err_str_)
    finally:
        # updating unload_plan field back to default state in current PlanView using log analyzer
        log_str = plan_view_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=plan_id,
                                                 unload_plan=False)
        logging.db(log_str)


if __name__ == "__main__":
    main()

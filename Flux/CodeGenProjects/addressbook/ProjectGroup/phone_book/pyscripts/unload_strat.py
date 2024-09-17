# standard imports
import logging
import datetime
import sys
import time

# project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.pyscripts.utility_functions import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)

def main():
    datetime_str: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    configure_logger(logging.DEBUG, str(PAIR_STRAT_ENGINE_LOG_DIR), f"unload_strat_{datetime_str}.log")

    # read strat_id from args
    args: List[str] = sys.argv[1:]
    if len(args) > 3:   # 3rd argument can be & for background run
        err_str_ = f"Invalid number of arguments, received: {len(args)=};;;{args=}"
        logging.error(err_str_)
        raise Exception(err_str_)

    strat_id: int = int(args[0])
    force_flag: bool = False
    if len(args) >= 2 and args[1] == "--force":
        force_flag = True
    try:
        logging.warning(f"Triggered unload for {strat_id=}, {force_flag=}")
        unload_strat(strat_id, force_flag)
    except Exception as e:
        err_str_ = f"Failed to unload strat with {strat_id=}, {force_flag=}, exception: {e}"
        logging.error(err_str_)
    finally:
        # update strat_view obj
        photo_book_service_http_client.patch_strat_view_client({'_id': strat_id, 'unload_strat': False})


if __name__ == "__main__":
    main()
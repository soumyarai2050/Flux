import logging
import datetime

from FluxPythonUtils.scripts.utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.pyscripts.utility_functions import *


def main():
    try:
        date_str: str = datetime.datetime.now().strftime("%Y%m%d")
        configure_logger(logging.DEBUG, str(PAIR_STRAT_ENGINE_LOG_DIR),
                         f"pause_all_active_strats_{date_str}.log")

        logging.info("Triggering pause all active strats")
        email_book_service_http_client.pause_all_active_strats_query_client()
    except Exception as e:
        err_str_ = f"Failed to pause all active strats, exception: {e}"
        logging.error(err_str_)
    finally:
        logging.info("Updating system control state")
        updated_system_control_obj: SystemControlBaseModel = SystemControlBaseModel(id=1, pause_all_strats=False)
        email_book_service_http_client.patch_system_control_client(
            jsonable_encoder(updated_system_control_obj, by_alias=True, exclude_none=True))


if __name__ == "__main__":
    main()

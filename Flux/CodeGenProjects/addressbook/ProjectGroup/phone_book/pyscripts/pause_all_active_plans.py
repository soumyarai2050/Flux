import logging
import datetime

from FluxPythonUtils.scripts.general_utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.pyscripts.utility_functions import *


def main():
    try:
        date_str: str = datetime.datetime.now().strftime("%Y%m%d")
        configure_logger(logging.DEBUG, str(PAIR_STRAT_ENGINE_LOG_DIR),
                         f"pause_all_active_plans_{date_str}.log")

        logging.info("Triggering pause all active plans")
        email_book_service_http_client.pause_all_active_plans_query_client()
    except Exception as e:
        err_str_ = f"Failed to pause all active plans, exception: {e}"
        logging.error(err_str_)
    finally:
        logging.info("Updating system control state")
        updated_system_control_obj: SystemControlBaseModel = SystemControlBaseModel(id=1, pause_all_plans=False)
        email_book_service_http_client.patch_system_control_client(
            updated_system_control_obj.to_dict(exclude_none=True))


if __name__ == "__main__":
    main()

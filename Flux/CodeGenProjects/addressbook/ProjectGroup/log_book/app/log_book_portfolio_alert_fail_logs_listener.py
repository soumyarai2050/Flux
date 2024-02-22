# standard import
import time
from pathlib import PurePath
import os
from threading import Thread
from typing import List, Dict

os.environ["DBType"] = "beanie"
# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.app.log_book_service_helper import (
    portfolio_alert_fail_log, simulator_portfolio_alert_fail_log)
from FluxPythonUtils.email_adapter.email_handler import EmailHandler
from FluxPythonUtils.email_adapter.email_client import EmailClient, EmailUser
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager

secret_yaml_path = PurePath(__file__).parent.parent / "data" / "secret.yaml"

if os.path.exists(secret_yaml_path):
    secret_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(secret_yaml_path))
else:
    raise Exception(f"Can't find {secret_yaml_path = } file - can't fetch email credentials")

portfolio_fail_log_path = PurePath(__file__).parent.parent / "log" / portfolio_alert_fail_log
simulator_portfolio_fail_log_path = PurePath(__file__).parent.parent / "log" / simulator_portfolio_alert_fail_log


def log_file_size_listener_and_mail_notifier(log_file_path: str, retry_wait_sec: int | None = None):
    if retry_wait_sec is None:
        retry_wait_sec = 2

    email_client: EmailClient = EmailClient("", "outlook",
                                            secret_yaml_dict["sender_email"],
                                            secret_yaml_dict["sender_pw"])

    while 1:
        if not os.path.exists(log_file_path):
            print(f"Can't find {log_file_path} - retrying in {retry_wait_sec} secs")
            time.sleep(retry_wait_sec)
            continue
        else:
            if os.path.getsize(log_file_path) > mobile_book:
                sender_obj: EmailUser = EmailUser(
                            secret_yaml_dict["sender_username"],
                            secret_yaml_dict["sender_email"])

                receiver_users: List[EmailUser] = []
                receiver_users_dict: Dict
                for receiver_users_dict in secret_yaml_dict["receiver_emails"]:
                    receiver_user = EmailUser(
                        receiver_users_dict["username"],
                        receiver_users_dict["email"])
                    receiver_users.append(receiver_user)

                mail_subject = "Portfolio Alert handling in log analyzer failed!"
                mail_body = (f"Unexpected: {log_file_path = } found some log - something that can't be handled "
                             f"within log analyzer failed, please check {log_file_path}")
                email_obj: EmailHandler = EmailHandler(sender_obj, receiver_users, subject=mail_subject,
                                                       content=mail_body)
                email_client.send_mail(email_obj)
                break


if __name__ == "__main__":
    thread_list = []
    for log_file in [portfolio_fail_log_path, simulator_portfolio_fail_log_path]:
        thread = Thread(target=log_file_size_listener_and_mail_notifier, args=(log_file,))
        thread_list.append(thread)
        thread.start()

    for thread in thread_list:
        thread.join()
    print(f"Exiting {__file__}")

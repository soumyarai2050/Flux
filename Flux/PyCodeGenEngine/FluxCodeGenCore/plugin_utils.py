from typing import List, Dict


def selective_message_per_project_dict_to_env_var_str(project_to_message_list_dict: Dict[str, List[str]]) -> str:
    env_var_msg = ""
    project_name: str
    selected_msg_list: List[str]
    for project_name, selected_msg_list in project_to_message_list_dict.items():
        selected_msg_list_str = ",".join(selected_msg_list)
        env_var_msg += f"{project_name}:{selected_msg_list_str}"

        if project_name != list(project_to_message_list_dict.keys())[-1]:
            env_var_msg += ";"
    return env_var_msg


def selective_message_per_project_env_var_val_to_dict(project_to_message_env_var: str) -> Dict[str, List[str]]:
    splited_project_file_n_msg_list_str = project_to_message_env_var.split(";")
    project_name_to_msg_list_dict: Dict[str, List[str]] = {}
    for project_name_n_msg_list in splited_project_file_n_msg_list_str:
        project_name_n_msg_name_list_str = project_name_n_msg_list.split(":")
        if len(project_name_n_msg_name_list_str) == 2:
            project_name, msg_name_list_str = project_name_n_msg_name_list_str
            msg_name_list = msg_name_list_str.split(",")
            project_name_to_msg_list_dict[project_name] = msg_name_list
        # else not required: if splited_project_file_n_msg_list_str has only project_file name and no
        # msg_name is set along with project name, then avoiding adding it to this dict as if project name is
        # not set in dict then all msg of that file will be added in handling
    return project_name_to_msg_list_dict
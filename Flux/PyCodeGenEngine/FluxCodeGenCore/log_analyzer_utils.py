# standard imports
import logging
import re


def get_service_name_from_component_path(component_path: str):
    # Pattern to match what's between ProjectGroup/ and /log
    pattern = r"ProjectGroup/([^/]*)/log"
    match = re.search(pattern, component_path)

    if match:
        extracted_name = match.group(1)
        return extracted_name
    else:
        logging.error(f"Unable to extract service name from component path, {pattern=}, {component_path=}")
        return None
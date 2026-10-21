# standard imports
from typing import Dict, Tuple, Type, List, Any
import os

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.ORMModel.contact_log_book_service_msgspec_model import (
    Severity)
from FluxPythonUtils.scripts.general_utility_functions import get_version_from_mongodb_uri
from FluxPythonUtils.scripts.model_base_utils import MsgspecBaseModel
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


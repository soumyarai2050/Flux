from protogen import Registry, File, Plugin
from typing import List, Dict


class ExtendedProtogenPlugin(Plugin):

    def __init__(
        self,
        parameter: Dict[str, str],
        files_to_generate: List[File],
        registry: Registry,
    ):
        super().__init__(parameter, files_to_generate, registry)
        # @@@ Below data-members added in extended version by T
        self.insertion_points_to_content_dict: Dict[str, Dict[str, str]] | None = None

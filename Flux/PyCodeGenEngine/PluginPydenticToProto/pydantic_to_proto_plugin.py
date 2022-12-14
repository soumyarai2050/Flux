import json
import logging
from pydantic import BaseModel
from typing import List, Type, Dict, Final


class PydanticToProtoPlugin:
    """
    Python Plugin script to convert provided pydantic model to python model
    """
    pydantic_to_proto_type: Dict[str, str] = {
        "integer": "int32",
        "number": "float",
        "string": "string",
        "object": "message",
        "boolean": "bool"
    }
    flux_fld_val_is_date_time: str = "FluxFldValIsDateTime"
    revision_id_str: str = "revision_id"
    defualt_id: str = "_id"

    def __init__(self, pydantic_model_list: List[Type[BaseModel]], imports_list: List[str], package_name: str):
        """
        :param pydantic_model_list: List of Pydantic List of classes needed to be converted into proto message
        :param imports_list: List of porto imports to be added in generated proto file
        :param package_name: package name to be added in generated proto file
        """
        self._pydantic_model_list: List[Type[BaseModel]] = pydantic_model_list
        self._imports_list: List[str] = imports_list
        self._package_name: Final[str] = package_name
        self.message_name_cache_list: List[str] = []

    def _convert_pydantic_to_json(self, basemodel_cls: Type[BaseModel], indent: int = 2):
        return json.loads(basemodel_cls.schema_json(indent=indent))

    def _parse_to_proto_message(self, json_body: Dict) -> str:
        output_str = ""
        if "description" in json_body:
            new_line_sep_cmnt: List[str] = json_body["description"].split("\n")
            for cmnt in new_line_sep_cmnt:
                output_str += f'// {cmnt}\n'
        output_str += f"message {json_body['title']}" + " {\n"
        for index, field in enumerate(json_body["properties"]):
            try:
                if field == PydanticToProtoPlugin.revision_id_str:
                    continue
                # else not required: If field is other than revision_id then adding it to proto output str

                is_date_time = False
                """
                Different cases of required:
                1. no required attribute: Denotes all fields are optional or combination of optional or repeated 
                (repeated is considered as optional in pydantic)
                2. required attribute exists: Denotes at least one field is required (at least one field is 
                non-optional and non-repeated)
                """
                if "required" not in json_body:
                    if "type" in json_body["properties"][field] and \
                            "array" == json_body["properties"][field]["type"]:
                        cardinality = "repeated"
                    else:
                        cardinality = "optional"
                else:
                    if field not in json_body["required"]:
                        cardinality = "optional"
                    else:
                        if "type" in json_body["properties"][field] and \
                                "array" == json_body["properties"][field]["type"]:
                            cardinality = "repeated"
                        else:
                            cardinality = "required"
                if "$ref" in json_body["properties"][field]:
                    kind = json_body["properties"][field]["$ref"].split("/")[-1]
                elif "allOf" in json_body["properties"][field]:
                    kind = json_body["properties"][field]["allOf"][0]["$ref"].split("/")[-1]
                elif "array" == json_body["properties"][field]["type"]:
                    if "$ref" in json_body["properties"][field]["items"]:
                        kind = json_body["properties"][field]["items"]["$ref"].split("/")[-1]
                    else:
                        kind = PydanticToProtoPlugin.pydantic_to_proto_type[json_body["properties"][field]["items"]["type"]]
                else:
                    if "format" in json_body["properties"][field] and "date-time":
                        is_date_time = True
                        kind = "int64"
                    else:
                        kind = PydanticToProtoPlugin.pydantic_to_proto_type[json_body["properties"][field]["type"]]

                if "description" in json_body["properties"][field]:
                    new_line_sep_cmnt: List[str] = json_body['properties'][field]['description'].split("\n")
                    for cmnt in new_line_sep_cmnt:
                        output_str += f"    // {cmnt}\n"
                # else not required: avoiding if description is not present
            except Exception as e:
                err_str = f"Error while generating proto message for {json_body['title']} in field {field}, {e}"
                logging.exception(err_str)
                raise Exception(err_str)

            if field == PydanticToProtoPlugin.defualt_id:
                field = "id"
            # else not required: if field other than _id then no need to modify

            output_str += f"    {cardinality} {kind} {field} = {index+1}"

            if is_date_time:
                output_str += f" [({PydanticToProtoPlugin.flux_fld_val_is_date_time}) = true];\n"
            else:
                output_str += ";\n"
        output_str += "}\n"
        return output_str

    def _parse_to_proto_enum(self, json_body: Dict) -> str:
        enum_name = json_body["title"]
        output_str = f"enum {enum_name}" + " {\n"
        for index, enum_val in enumerate(json_body["enum"]):
            output_str += f"    {enum_val} = {index+1};\n"
        output_str += "}\n"
        return output_str

    def _parse_to_proto_text(self, basemodel_cls: Type[BaseModel]) -> str:
        basemodel_json = self._convert_pydantic_to_json(basemodel_cls)
        output_str = ""
        if basemodel_json["title"] not in self.message_name_cache_list:
            # main message conversion
            output_str += self._parse_to_proto_message(basemodel_json)
            self.message_name_cache_list.append(basemodel_json["title"])
            output_str += "\n\n"

        if "definitions" in basemodel_json:
            for message_or_enum in basemodel_json["definitions"]:
                if message_or_enum not in self.message_name_cache_list:
                    if "enum" in basemodel_json["definitions"][message_or_enum]:
                        output_str += self._parse_to_proto_enum(basemodel_json["definitions"][message_or_enum])
                    else:
                        output_str += self._parse_to_proto_message(basemodel_json["definitions"][message_or_enum])
                    output_str += "\n\n"
                    self.message_name_cache_list.append(message_or_enum)
                # else not required: Avoiding repetition
        # else not required: If definitions not in basemodel then no more message/enum to iterate

        return output_str

    def _generate_file_content(self):
        output_str = 'syntax = "proto2";\n'
        for import_proto in self._imports_list:
            output_str += f'import "{import_proto}";\n\n'
        output_str += f'package {self._package_name};\n\n'
        for basemodel_cls in self._pydantic_model_list:
            output_str += self._parse_to_proto_text(basemodel_cls)
        return output_str

    def run(self, file_name: str, file_path: str | None = None):
        """
        Main Function: creates the output proto file
        """
        if file_path is not None:
            file_name = file_path + file_name if file_path.endswith("/") else file_path + "/" + file_name
        file_content = self._generate_file_content()
        with open(file_name, "w") as fl:
            fl.write(file_content)

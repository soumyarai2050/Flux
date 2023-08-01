#!/usr/bin/env python
import os
import textwrap
import time
from typing import List, Tuple
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case

# Required for accessing custom options from schema


class BaseDbBindingPlugin(BaseProtoPlugin):
    """
    Base DB Binding plugin class that holds all important handler methods that are needed in both template and
    non-template required bs_binding plugin derived implementation classes
    """
    main_message_option_name = "FluxMsgOrmRoot"
    db_only_field_message_option_name = "FluxDbOnlyField"
    foreign_key_msg_option_name = "FluxMsgFk"
    foreign_key_fld_option_name = "FluxFldFk"
    usage_param_option_name = "FluxMsgOrmUsageParam"
    default_value_placeholder_string_option = "FluxDefaultValuePlaceholderString"
    primary_key_option_name = "FluxFldPk"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.proto_type_to_db_type_dict = self.config_yaml['proto_type_to_db_type_dict']
        self.proto_type_to_py_type_dict = self.config_yaml['proto_type_to_py_type_dict']
        self.db_type_to_py_type_dict = self.config_yaml['db_type_to_py_type_dict']
        self.main_proto_msg_class_name = ""
        self.class_name_snake_cased: str = ""
        self.class_name_hyphen_cased: str = ""

        # Below data members will be initialized at runtime
        self.db_fields_in_sequence: List[str] = []

        # Where each tuple is of each field having below deta:
        # (field_name, field_data_type(converted for db), schema number of proto, IsPrimary, IsRequired,
        # bool for field if option FldForeignKey is True)
        self.db_only_fields_list_of_tuples: List[Tuple[str, str, int, bool, bool, bool]] = []
        self.all_db_fields_list_of_tuples: List[Tuple[str, str, int, bool, bool, bool]] = []

        # Where each tuple is of each option having values (UsageParamName, UsageParamdataType)
        self.usage_param_option_names_list_of_tuples: List[Tuple[str, str]] = []

        # Where each tuple is of each foreign key having:
        # (foreign_key, TableName, FieldName, FieldType, IsPrimary, IsRequired)
        self.foreign_keys_list_of_tuples: List[Tuple[str, str, str, str, bool, bool]] = []

    @staticmethod
    def __get_field_data_type(field: protogen.Field):
        if field.kind.name.lower() == 'message':
            field_data_type = field.message.proto.name
        elif field.kind.name.lower() == 'enum':
            field_data_type = field.enum.proto.name
        else:
            field_data_type = field.kind.name.lower()
        return field_data_type

    def __get_proto_to_db_data_type(self, field: protogen.Field | None = None,
                                    datatype: str | None = None) -> str:
        field_data_type = ""
        if field is None and datatype is None:
            err_str = "Both params of get_proto_to_db_data_type can't be left empty"
            logging.exception(err_str)
            raise Exception(err_str)
        elif field is not None and datatype is not None:
            err_str = "Both params of get_proto_to_db_data_type can't be provided in same call"
            logging.exception(err_str)
            raise Exception(err_str)
        elif field is not None:
            field_data_type = self.__get_field_data_type(field)
        elif datatype is not None:
            field_data_type = datatype

        # Handling proto datatype conversion to db datatype
        if field_data_type in self.proto_type_to_db_type_dict:
            return self.proto_type_to_db_type_dict[field_data_type]
        else:
            err_str = f"Proto Data Type {field_data_type} not found in proto_type_to_db_type_dict from config file"
            logging.exception(err_str)
            raise Exception(err_str)

    def __get_proto_to_py_data_type(self, field: protogen.Field | None = None,
                                    datatype: str | None = None) -> str:
        field_data_type = ""
        if field is None and datatype is None:
            err_str = "Both params of get_proto_to_db_data_type can't be left empty"
            logging.exception(err_str)
            raise Exception(err_str)
        elif field is not None and datatype is not None:
            err_str = "Both params of get_proto_to_db_data_type can't be provided in same call"
            logging.exception(err_str)
            raise Exception(err_str)
        elif field is not None:
            field_data_type = self.__get_field_data_type(field)
        elif datatype is not None:
            field_data_type = datatype

        # Handling proto datatype conBaseProtoversion to python datatype
        if field_data_type in self.proto_type_to_py_type_dict:
            return self.proto_type_to_py_type_dict[field_data_type]
        else:
            err_str = f"Proto Data Type {field_data_type} not found in proto_type_to_py_type_dict from config file"
            logging.exception(err_str)
            raise Exception(err_str)

    def __get_db_to_py_data_type(self, datatype: str) -> str:
        # Handling Db datatype conversion to python datatype
        if datatype in self.db_type_to_py_type_dict:
            return self.db_type_to_py_type_dict[datatype]
        else:
            err_str = f"DB Data Type {datatype} not found in db_type_to_py_type_dict from config file"
            logging.exception(err_str)
            raise Exception(err_str)

    def __set_db_fields_sequence_to_data_members(self, file: protogen.File):
        root_message = None
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                root_message = message
                break
            # else not required: Avoiding messages other than ORM root

        if root_message is None:
            err_str = f"Can't find the ORM root message in {file.proto.name}"
            logging.exception(err_str)
            raise Exception(err_str)

        # Fetching Db Only fields data and setting to self.db_only_fields_list_of_tuple
        self.db_only_fields_list_of_tuples = \
            self.get_complex_msg_option_values_as_list_of_tuple(root_message,
                                                                BaseDbBindingPlugin.db_only_field_message_option_name)

        # FldForeignKey for db_only_fields is False as If any Field is not having field lvl foreign_key option
        # then msg lvl option is used for it
        # Therefore setting Tuple index for FldForeignKey as False
        for index, db_only_field_tuple in enumerate(self.db_only_fields_list_of_tuples):
            self.db_only_fields_list_of_tuples[index] = (*db_only_field_tuple, False)

        # Fetching Usage Param Names from data members and Setting to self.usage_param_option_names_list_of_tuples
        self.usage_param_option_names_list_of_tuples = \
            self.get_complex_msg_option_values_as_list_of_tuple(root_message,
                                                                BaseDbBindingPlugin.usage_param_option_name)

        # Fetching Foreign Key options from schema and setting to self.foreign_keys_list_of_tuples
        self.foreign_keys_list_of_tuples = \
            self.get_complex_msg_option_values_as_list_of_tuple(root_message,
                                                                BaseDbBindingPlugin.foreign_key_msg_option_name)

        # Adding foreign_key field at first index of tuple with other present items
        # foreign_key = foreign_table_key + foreign_field_name (in snake case)
        counter = 0
        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            foreign_key_field = f"{convert_camel_case_to_specific_case(foreign_key_tuple[0])}_{convert_camel_case_to_specific_case(foreign_key_tuple[1])}"
            self.foreign_keys_list_of_tuples[counter] = (foreign_key_field, *foreign_key_tuple)
            counter += 1

        temp_dict = {}
        # Adding db only fields
        for db_only_field in self.db_only_fields_list_of_tuples:
            temp_dict[db_only_field[2]] = db_only_field[0]
        # Adding other db fields
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                for field in message.fields:
                    temp_dict[field.proto.number] = field.proto.name
                    temp_list = [field.proto.name, self.__get_proto_to_db_data_type(field), field.proto.number]
                    if self.is_option_enabled(field, BaseDbBindingPlugin.primary_key_option_name):
                        temp_list.append(True)
                    else:
                        temp_list.append(False)
                    if "repeated" != (field.cardinality.name.lower()):
                        if "required" == field.cardinality.name.lower():
                            temp_list.append(True)
                        else:
                            temp_list.append(False)
                    else:
                        err_str = f"Repeated fields are not supported in db binding class, check field " \
                                  f"{field.proto.name} in proto model"
                        logging.exception(err_str)
                        raise Exception(err_str)

                    # Using Field level option to set foreign key
                    if self.is_option_enabled(field, BaseDbBindingPlugin.foreign_key_fld_option_name):
                        temp_list.append(True)

                        field_option_fk_tuple_list = BaseProtoPlugin._get_complex_option_value_as_list_of_dict(
                            str(field.proto.options), BaseDbBindingPlugin.foreign_key_fld_option_name)
                        for field_fk_option_tuple in field_option_fk_tuple_list:
                            self.foreign_keys_list_of_tuples.append((field.proto.name, *field_fk_option_tuple))

                    else:
                        temp_list.append(False)

                    self.all_db_fields_list_of_tuples.append(tuple(temp_list))

        # Joining db_only_fields_list_of_tuples + other fields present all_db_fields_list_of_tuples
        self.all_db_fields_list_of_tuples.extend(self.db_only_fields_list_of_tuples)

        field_list = []
        for field_tuple in sorted(temp_dict.items()):
            field_list.append(field_tuple[1])

        self.db_fields_in_sequence = field_list

    def handle_import_pb2(self, file: protogen.File) -> str:
        # Setting required data members in very first handler method
        self.assign_diff_msg_name_format_data_members(file)

        # Setting db field's related data members in very first handler method
        self.__set_db_fields_sequence_to_data_members(file)

        proto_file_name = str(file.proto.name).split(os.sep)[-1].split(".")[0]
        return f"# To access custom options from schema\nimport {proto_file_name}_pb2 " \
               f"as {proto_file_name}_pb2"

    def handle_class_container_name(self, file: protogen.File) -> str:
        return f"class {self.main_proto_msg_class_name}Container:"

    def handle_db_columns_without_id(self, file: protogen.File) -> str:
        db_fields = []
        for field in self.db_fields_in_sequence:
            for field_tuple in self.all_db_fields_list_of_tuples:
                if field == field_tuple[0]:
                    # 4th item in tuple is bool of Primary key
                    if field_tuple[3] is not True:
                        db_fields.append(field_tuple[0])
                    # else not required: avoiding primary key in this method as output

        # Appending foreign key in db_fields
        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            db_fields.append(foreign_key_tuple[0])

        db_fields_str = ", ".join(db_fields)
        return textwrap.dedent(f'{self.class_name_snake_cased}_db_columns_without_id: Final[str] = "{db_fields_str}"')

    def handle_db_columns_with_id(self, file: protogen.File) -> str:
        primary_key = ""
        for field_tuple in self.all_db_fields_list_of_tuples:
            # 4th item in tuple is bool of Primary key
            if field_tuple[3] is True:
                primary_key = field_tuple[0]
                break
            # else not required: avoiding any other field than primary key

        return textwrap.dedent(
            f'{self.class_name_snake_cased}_db_columns_with_id: Final[str] = "{primary_key}, " + {self.class_name_snake_cased}_db_columns_without_id')

    def handle_create_table_query(self, file: protogen.File) -> str:
        output_str = textwrap.dedent("""
        # Note: we rely on sqlite3 ROWID logic to automatically populate our integer primary key instead of explicit use of
        # AUTOINCREMENT keyword (appears after INTEGER PRIMARY KEY), that changes the automatic ROWID assignment algorithm
        # to prevent the reuse of ROWID(s) from previously deleted rows - this is done on purpose as we don't delete any
        # chat, skipping Primary Key field (INTEGER type) in insert query triggers makes primary key an alias to ROWID\n""")

        output_str += textwrap.dedent(
            f"""# Usage: create_{self.class_name_snake_cased}_table_query.format(chat_group_name, chat_group_name)""")

        output_str += textwrap.dedent(f'''
            create_{self.class_name_snake_cased}_table_query: Final[str] = """CREATE TABLE IF NOT EXISTS ''' + "'{}-" + f"{self.class_name_hyphen_cased}' (\n")

        for field in self.db_fields_in_sequence:
            field_tuple = None
            for field_tuple in self.all_db_fields_list_of_tuples:
                if field_tuple[0] == field:
                    break
            # else not required: if field tuple not found in all_db_fields_list_of_tuples then handling below

            if field_tuple is None:
                err_msg = f"Could not find tuple of field {field} in all_db_fields_list_of_tuples"
                raise Exception(err_msg)
            # else not required: if not none then ignore

            db_field = f"    {field_tuple[0]} {field_tuple[1]}"

            # 6th item is bool for primary key option in field
            if field_tuple[5]:
                db_field = f"{db_field} FOREIGN KEY"
            # else not required: if field is not primary key then ignoring

            # 4th item is bool for primary key option in field
            if field_tuple[3]:
                db_field = f"{db_field} PRIMARY KEY"
            # else not required: if field is not primary key then ignoring

            # 5th item of tuple is bool for IsRequired in field
            if field_tuple[4]:
                db_field = f"{db_field} NOT NULL"
            # else not required: if field is_required is false then ignoring

            output_str += db_field + ",\n"

        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            output_str += f'    {foreign_key_tuple[0]} {self.__get_proto_to_db_data_type(datatype=foreign_key_tuple[3])}'
            # 5th item of tuple is IsPrimary
            if foreign_key_tuple[4]:
                output_str += " PRIMARY KEY"
            # else not required: If not IsPrimary then Ignoring

            # 6th item of tuple is IsRequired
            if foreign_key_tuple[5]:
                output_str += " NOT NULL"
            # else not required: If not IsRequired then Ignoring

            output_str += ",\n"
        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            output_str += f'    FOREIGN KEY ({foreign_key_tuple[0]}) REFERENCES ' + ''''{}-''' + f'''{convert_camel_case_to_specific_case(foreign_key_tuple[1], "-")}'({foreign_key_tuple[2]})\n'''

        output_str += f'); """'''

        return textwrap.dedent(output_str)

    def handle_insert_query_suffix(self, file: protogen.File) -> str:
        field_count = 0
        for field_tuple in self.all_db_fields_list_of_tuples:
            # 4th item in tuple is bool of Primary key
            if field_tuple[3] is not True:
                field_count += 1
            # else not required: avoiding primary key in this method as output

        # Adding Total number of fields leaving primary key
        field_count = field_count + len(self.foreign_keys_list_of_tuples)

        placeholder_str = ", ".join(["?"] * field_count)

        output_str = f"# skip id\n" + f"""insert_{self.class_name_snake_cased}_query_suffix: Final[str] = """ + "\\" + \
                     """\n    '''( {} ) """ + \
                     f"VALUES ({placeholder_str}); '''.format({self.class_name_snake_cased}_db_columns_without_id)"

        return textwrap.dedent(output_str)

    def handle_insert_query(self, file: protogen.File):
        output_str: str = f"# Usage: insert_{self.class_name_snake_cased}_query.format(chat_group_name)\n"
        output_str += f"insert_{self.class_name_snake_cased}_query: Final[str] = \\\n" + '    """INSERT INTO' + " '{}-" \
                      + f"{self.class_name_hyphen_cased}' " + f'""" + insert_{self.class_name_snake_cased}_query_suffix'
        return output_str

    def handle_select_all_query_prefix(self, file: protogen.File):
        output_str = "# while reading - also no id needed for now (currently we don't delete/update an existing record)\n"
        output_str += textwrap.dedent(
            f"select_all_{self.class_name_snake_cased}_query_prefix: Final[str] = '''SELECT " + "{} from '''" +
            ".format(chat_msg_db_columns_without_id)")
        return output_str

    def handle_select_all_query(self, file: protogen.File):
        output_str: str = f"# Usage: select_all_{self.class_name_snake_cased}_query.format(chat_group_id)\n"
        output_str += f'select_all_{self.class_name_snake_cased}_query: Final[str] = select_all_{self.class_name_snake_cased}_query_prefix + """' \
                      + "'{}-" + f"{self.class_name_hyphen_cased}'" + ' """'
        return output_str

    def handle_data_members(self, file: protogen.File):
        init_formatted_params_list = []
        init_formatted_params_list_with_default_value = []
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                for field in message.fields:
                    if self.is_option_enabled(field, BaseDbBindingPlugin.default_value_placeholder_string_option):
                        default_value = ""
                        for option in str(field.proto.options).split("\n"):
                            if BaseDbBindingPlugin.default_value_placeholder_string_option in option:
                                default_value = str(option.split(":")[1][2:-1])
                        # else not required: if no value is found below is the handling for it

                        # Handling no default value fetched exception
                        if not default_value:
                            err_str = f"Could not find default value for field {field.proto.name}"
                            logging.exception(err_str)
                            raise Exception
                        # else not required: if default_value is found properly then ignore

                        if default_value == "None":
                            init_formatted_params_list_with_default_value.append(
                                f"{field.proto.name}: {self.__get_proto_to_py_data_type(field)}|None = {default_value}")
                        else:
                            init_formatted_params_list_with_default_value.append(
                                f"{field.proto.name}: {self.__get_proto_to_py_data_type(field)} = {default_value}")
                    else:
                        init_formatted_params_list.append(
                            f"{field.proto.name}: {self.__get_proto_to_py_data_type(field)}")
            # else not required: Avoiding messages other than ORM message

        # Adding params having default values at last to avoid exception in python
        init_formatted_params_list += init_formatted_params_list_with_default_value

        output_str = f"def __init__(self, {', '.join(init_formatted_params_list)}):\n"
        output_str += f"    self.{self.class_name_snake_cased}: {self.class_name_snake_cased}_pb2.{self.main_proto_msg_class_name} " \
                      f"= {self.class_name_snake_cased}_pb2.{self.main_proto_msg_class_name}() \n"
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                for field in message.fields:
                    # Adding leading comment if available before field
                    if comment_content := field.location.leading_comments:
                        for comment in comment_content.split("\n"):
                            output_str += f"    # {comment}\n"
                    # else not required: if field lvl leading_comment not present then avoiding

                    # Adding FluxFldCmnt option value if available before field
                    if flx_fld_cmt_value := self.get_flux_fld_cmt_option_value(field):
                        output_str += f"    # {flx_fld_cmt_value}\n"
                    # else not required: Avoiding empty string if no value provided in option

                    output_str += f"    self.{self.class_name_snake_cased}.{field.proto.name} = {field.proto.name}\n"
                    if comment_content := field.location.trailing_comments:
                        for comment in comment_content.split("\n"):
                            output_str += f"    # {comment}\n"
                    # else not required: if field lvl trailing_comment not present then avoiding
                break
        return output_str

    def handle_str_method_return(self, file: protogen.File):
        output_str = "def __str__(self):\n"
        output_str += "    return f'"
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                counter = 0
                for field in message.fields:
                    if counter > 1:
                        output_str += "\\\n        "
                        counter = 0
                    # else not required: if counter is greater than 2 then to avoid long single line
                    # format string, breaking and adding new line after every 2 values
                    counter += 1
                    output_str += f"{field.proto.name}: " + "{" + f"self.{self.class_name_snake_cased}.{field.proto.name}" + "}"
                    if field != message.fields[-1]:
                        output_str += ", "
                    # else not required: Avoiding comma after last item from list
                break
            # else not required: if message is not having option MainMessage as true, then it signifies
            # that message is defined for option or field data-type therefore ignoring these messages
        output_str += "'"
        return output_str

    def handle_get_from_db_row(self, file: protogen.File):
        if self.db_only_fields_list_of_tuples:
            output_str = f"@staticmethod\ndef get_{self.class_name_snake_cased}_and_db_fields_from_db_row({self.class_name_snake_cased}_row):\n"
        else:
            output_str = f"@staticmethod\ndef get_{self.class_name_snake_cased}_from_db_row({self.class_name_snake_cased}_row):\n"

        db_fields_without_primary = []
        class_attr_fields = []
        for field in self.db_fields_in_sequence:

            db_field_tuple = None
            for db_field_tuple in self.all_db_fields_list_of_tuples:
                if db_field_tuple[0] == field:
                    break
            # else not required: if field tuple not found in all_db_fields_list_of_tuples then handling below

            if db_field_tuple is None:
                err_msg = f"Could not find tuple of field {field} in all_db_fields_list_of_tuples"
                raise Exception(err_msg)
            # else not required: if not none then ignore

            # 4th item of tuple is bool for primary key
            if db_field_tuple[3] is False:
                db_fields_without_primary.append(db_field_tuple[0])
            # else not required: avoiding primary key field

            if db_field_tuple not in self.db_only_fields_list_of_tuples and not db_field_tuple[3]:
                class_attr_fields.append(db_field_tuple[0])
            # else not required: avoiding db only fields and primary key

        # Adding foreign key
        for foreign_tuple in self.foreign_keys_list_of_tuples:
            if not foreign_tuple[4]:
                db_fields_without_primary.append(foreign_tuple[0])
            # else not required: avoiding primary key field

        output_str += f"    {', '.join(db_fields_without_primary)} = {self.class_name_snake_cased}_row\n"

        temp = ""
        for db_field_tuple in self.db_only_fields_list_of_tuples:
            # 4th item of tuple is bool for primary key
            if db_field_tuple[3] is False:
                temp = db_field_tuple[0]
                break
            # else not required: avoiding primary key field

        output_str += f"    return {temp}, {self.main_proto_msg_class_name}Container({', '.join(class_attr_fields)})"
        return output_str

    def handle_insert_params(self, file: protogen.File):
        output_str = f"# used to provide params for insert_{self.class_name_snake_cased}_params\n"
        if foreign_key_list_of_tuples := self.foreign_keys_list_of_tuples:
            foreign_keys_comma_sep_str = ""
            for foreign_key_tuple in foreign_key_list_of_tuples:
                if foreign_key_tuple == foreign_key_list_of_tuples[0]:
                    foreign_keys_comma_sep_str += f"{foreign_key_tuple[0]}: {self.__get_proto_to_py_data_type(datatype=foreign_key_tuple[3])}"
                else:
                    foreign_keys_comma_sep_str += f", {foreign_key_tuple[0]}: {self.__get_proto_to_py_data_type(datatype=foreign_key_tuple[3])}"

            output_str += f"def insert_{self.class_name_snake_cased}_params(self, {foreign_keys_comma_sep_str}"
        else:
            output_str += f"def insert_{self.class_name_snake_cased}_params(self"
        for db_only_field in self.db_only_fields_list_of_tuples:
            # 4th item in tuple is bool for primary key
            if not db_only_field[3]:
                db_only_field_py_data_type = self.__get_db_to_py_data_type(db_only_field[1])
                output_str += f", {db_only_field[0]}: {db_only_field_py_data_type}"
            # else not required: avoiding primary key to be added
        output_str += "):\n"

        output_str += f"    return "

        for db_field_name in self.db_fields_in_sequence:
            db_field_tuple = ()
            for field_tuple in self.all_db_fields_list_of_tuples:
                if field_tuple[0] == db_field_name:
                    db_field_tuple = field_tuple
                # else not required: if no match found then handled below

            if not db_field_tuple:
                err_str = f"Could not find {db_field_name} in self.all_db_fields_list_of_tuples"
                logging.exception(err_str)
                raise Exception(err_str)

            # 4th item of tuple is Primary key bool
            if db_field_tuple[3] is False:
                if db_field_tuple not in self.db_only_fields_list_of_tuples:
                    output_str += f"self.{self.class_name_snake_cased}.{db_field_tuple[0]}"
                else:
                    output_str += f"{db_field_tuple[0]}"
                # else not required: avoiding primary key field
                if db_field_tuple[0] != self.db_fields_in_sequence[-1]:
                    output_str += ", "
                # else not required: avoiding comma after last field

        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            output_str += f", {foreign_key_tuple[0]}"

        return output_str

    def handle_store_in_db(self, file: protogen.File):
        db_only_fields_other_than_primary = ""
        data_type = ""
        for db_field_tuple in self.db_only_fields_list_of_tuples:
            # 4th item of tuple is bool for primary key
            if db_field_tuple[3] is False:
                db_only_fields_other_than_primary = db_field_tuple[0]
                data_type = self.__get_db_to_py_data_type(db_field_tuple[1])
                break
            # else not required: avoiding primary key field

        usage_params_str = ""
        usage_params_use_case_str = ""
        for usage_param_tuple in self.usage_param_option_names_list_of_tuples:
            if usage_param_tuple == self.usage_param_option_names_list_of_tuples[0]:
                usage_params_str += f"{usage_param_tuple[0]}: {self.__get_proto_to_py_data_type(datatype=usage_param_tuple[1])}"
                usage_params_use_case_str += f"{usage_param_tuple[0]}"
            else:
                usage_params_str += f", {usage_param_tuple[0]}: {usage_param_tuple[1]}"
                usage_params_use_case_str += f", {usage_param_tuple[0]}"

        foreign_keys_comma_sep_str = ""
        foreign_keys_with_datatype_comma_sep_str = ""
        for foreign_key_tuple in self.foreign_keys_list_of_tuples:
            if foreign_key_tuple == self.foreign_keys_list_of_tuples[0]:
                foreign_keys_comma_sep_str += f"{foreign_key_tuple[0]}"
                foreign_keys_with_datatype_comma_sep_str += f"{foreign_key_tuple[0]}: {self.__get_proto_to_py_data_type(datatype=foreign_key_tuple[3])}"
            else:
                foreign_keys_comma_sep_str += f", {foreign_key_tuple[0]}"
                foreign_keys_with_datatype_comma_sep_str += f", {foreign_key_tuple[0]}: {self.__get_proto_to_py_data_type(datatype=foreign_key_tuple[3])}"

        output_str = f"def store_in_db(self, {foreign_keys_with_datatype_comma_sep_str}, {db_only_fields_other_than_primary}: {data_type}, {usage_params_str}, db_cursor):\n"
        output_str += f"    data_tuple = (self.insert_{self.class_name_snake_cased}_params({foreign_keys_comma_sep_str}, {db_only_fields_other_than_primary}))\n"
        output_str += f"    sql_query = self.insert_{self.class_name_snake_cased}_query.format({usage_params_use_case_str})\n"
        output_str += f"    db_cursor.execute(sql_query, data_tuple)"

        return textwrap.dedent(output_str)

    def handle_root_msg_comment(self, file: protogen.File) -> str:
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                if self.get_flux_msg_cmt_option_value(message):
                    return f"# {self.get_flux_msg_cmt_option_value(message)}"
                else:
                    return ""
            # else not required: avoiding message not having orm root option

    def handle_file_comment(self, file: protogen.File):
        if self.get_flux_file_cmt_option_value(file):
            return f"# {self.get_flux_file_cmt_option_value(file)}\n"
        else:
            return ""

    def assign_diff_msg_name_format_data_members(self, file: protogen.File):
        """
        Assigns data members associated with proto msg class name
        """
        message_name: str | None = None
        for message in file.messages:
            if self.is_option_enabled(message, BaseDbBindingPlugin.main_message_option_name):
                message_name = message.proto.name
                break
        # else not required: if no message finds "MainMessage" as true, then handling it below

        if message_name is not None:
            msg_name_snake_case = convert_camel_case_to_specific_case(message_name)
            msg_name_hyphen_case = convert_camel_case_to_specific_case(message_name, "-")

            self.main_proto_msg_class_name = message_name
            self.class_name_snake_cased = msg_name_snake_case
            self.class_name_hyphen_cased = msg_name_hyphen_case

            if self.class_name_snake_cased is None or self.class_name_snake_cased == "":
                err_str = "Could not assign snake cased value of message from proto schema"
                logging.exception(err_str)
                raise Exception(err_str)
            # else not required: if self.class_name_snake_cased got assigned correctly then ignore
        # else not required: if message_name is not found then not assigning values to data members

# standard imports
from typing import List
import orjson
import importlib
import inspect
import typing
from typing import Type, Any, Dict
import re
import hashlib
import copy
from pymongo import UpdateOne

# project imports
from FluxPythonUtils.scripts.general_utility_functions import non_jsonable_types_handler


# Aggregates required in all projects

def get_limited_objs(limit: int):
    # used in limit model option
    if limit > 0:
        return [
            {
                "$limit": limit
            }
        ]
    elif limit < 0:
        return [
            {
                "$sort": {"_id": -1},
            },
            {
                "$limit": -limit  # limit becomes positive (limit agg always accepts +ive argument)
            }
        ]
    else:
        return []


def get_match_layer_for_obj_id_list(obj_id_list: List[int]):
    return {
        "$match": {
            "_id": {
                "$in": obj_id_list
            }
        }
    }


def get_non_stored_ids(ids_to_check: List[int]):
    pipeline = [
        # Step 1: Match documents with _id in the ids_to_check list
        {"$match": {"_id": {"$in": ids_to_check}}},

        # Step 2: Group the found _id values into an array
        {"$group": {"_id": None, "found_ids": {"$addToSet": "$_id"}}},

        # Step 3: Use facet to handle the case when no documents match
        {"$facet": {
            "results": [
                {"$project": {
                    "found_ids": "$found_ids",
                    "missing_ids": {"$setDifference": [ids_to_check, "$found_ids"]}
                }}
            ],
            "empty": [
                {"$count": "count"}
            ]
        }},

        # Step 4: Handle empty results by merging the facets
        {"$project": {
            "found_ids": {
                "$cond": [{"$eq": [{"$size": "$results"}, 0]}, [], {"$arrayElemAt": ["$results.found_ids", 0]}]},
            "missing_ids": {"$cond": [{"$eq": [{"$size": "$results"}, 0]}, ids_to_check,
                                      {"$arrayElemAt": ["$results.missing_ids", 0]}]}
        }}
    ]
    return pipeline


def get_nested_field_max_id(nested_field_name):
    pipeline = [
        {"$unwind": f"${nested_field_name}"},  # Unwind the "nested_field_name" array
        {"$group": {"_id": None, "max_id": {"$max": f"${nested_field_name}._id"}}}  # Get the max id
    ]
    return pipeline


def get_raw_perf_data_callable_names_pipeline():
    agg_pipeline = {"aggregate": [
        {
            '$group': {
                '_id': '$callable_name',
                'count': {
                    '$count': {}
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'callable_name': '$_id',
                'total_calls': '$count'
            }
        }
    ]}
    return agg_pipeline


def get_raw_performance_data_from_callable_name_agg_pipeline(callable_name: str):
    return {"aggregate": [
        {
            "$match": {
                "callable_name": callable_name
            }
        }
    ]}


def get_array_path_for_key(model_class, key: str) -> list[str]:
    path_parts = key.split('.')
    array_path = []
    current_type = model_class

    for part in path_parts[:-1]:
        if not inspect.isclass(current_type):
            break

        try:
            module = importlib.import_module(current_type.__module__)
            type_hints = typing.get_type_hints(current_type, globalns=vars(module))
            field_type = type_hints.get(part)
        except Exception:
            break

        if field_type is None:
            break

        origin = typing.get_origin(field_type)
        args = typing.get_args(field_type)

        is_list = False
        list_element_type = None

        if origin is list or origin is List:
            is_list = True
            if args:
                list_element_type = args[0]
        elif origin is typing.Union:
            list_in_union = next((arg for arg in args if typing.get_origin(arg) in [list, List]), None)
            if list_in_union:
                is_list = True
                union_list_args = typing.get_args(list_in_union)
                if union_list_args:
                    list_element_type = union_list_args[0]

        if is_list:
            array_path.append(part)
            if list_element_type:
                current_type = list_element_type
            else:
                break  # List without type args, can't go deeper
        elif inspect.isclass(field_type):
            current_type = field_type
        elif origin is typing.Union:
            class_in_union = next((arg for arg in args if inspect.isclass(arg)), None)
            if class_in_union:
                current_type = class_in_union
            else:
                break
        else:
            break
    return array_path


def create_cascading_multi_filter_pipeline(model_class: Type,
                                           filters: List[dict[str, Any]] | None = None,
                                           sort_order: List[dict[str, Any]] | None = None,
                                           pagination: dict[str, int] | None = None):
    """
    Creates a generic, cascading MongoDB pipeline that filters nested arrays
    based on multiple conditions.

    This version intelligently discovers array paths and filter conditions
    from the provided model class annotations.

    If an inner array becomes empty after filtering, its parent element in the
    outer array is also removed, continuing up to the top level.

    Args:
      model_class (type): The top-level msgspec/Pydantic model class corresponding
                          to the MongoDB collection.
      filters (List[dict], optional): List of filter conditions. Each dict can have:
                                      "column_name": The dot-notation path to the field.
                                      "filtered_values": A list of values for an $in match.
                                      "text_filter": A string for text-based filtering.
                                      "text_filter_type": Type of text match (e.g., 'contains').
      sort_order (List[dict], optional): A list of dictionaries specifying the sort order.
                                         Each dictionary should contain:
                                         "sort_by": The field path to sort by.
                                         "sort_direction": 1 for ascending, -1 for descending.
                                         "is_absolute_sort": (optional) bool, if True, sorts by the
                                                             absolute value of the field. Defaults to False.
      pagination (dict, optional): A dictionary for pagination.
                                   "page_number": The page number to retrieve (1-based).
                                   "page_size": The number of documents per page.
    """
    if filters is None:
        filters = []
    nested_filters = [f for f in filters if '.' in f.get('column_name')]

    # Build initial $match stage for all filters as an optimization
    pipeline = []
    match_and_conditions = []

    for f in filters:
        key = f['column_name']

        # Condition for filtered_values
        if f.get('filtered_values'):
            if f.get('filter_type') == 'notIn':
                match_and_conditions.append({key: {"$nin": f['filtered_values']}})
            else:
                match_and_conditions.append({key: {"$in": f['filtered_values']}})

        # Condition for text_filter
        if f.get('text_filter') and f.get('text_filter_type'):
            text_filter = f['text_filter']
            text_filter_type = f['text_filter_type']
            escaped_text = re.escape(text_filter)

            text_op = None
            if text_filter_type == 'equals':
                text_op = {"$eq": text_filter}
            elif text_filter_type == 'notEqual':
                text_op = {"$ne": text_filter}
            elif text_filter_type == 'contains':
                text_op = {"$regex": escaped_text, "$options": "i"}
            elif text_filter_type == 'notContains':
                match_and_conditions.append({key: {"$not": re.compile(escaped_text, re.IGNORECASE)}})
                continue
            elif text_filter_type == 'beginsWith':
                text_op = {"$regex": f"^{escaped_text}", "$options": "i"}
            elif text_filter_type == 'endsWith':
                text_op = {"$regex": f"{escaped_text}$", "$options": "i"}

            if text_op:
                match_and_conditions.append({key: text_op})

    if match_and_conditions:
        pipeline.append({"$match": {"$and": match_and_conditions}})

    if nested_filters:
        # --- Dynamic discovery for nested part ---
        all_array_paths = {
            f['column_name']: get_array_path_for_key(model_class, f['column_name'])
            for f in nested_filters
        }

        # Filter out keys that don't have a valid array path
        all_array_paths = {k: v for k, v in all_array_paths.items() if v}

        if all_array_paths:
            longest_path_key = max(all_array_paths, key=lambda k: len(all_array_paths[k]))
            longest_path = all_array_paths[longest_path_key]

            filters_by_level = {i: [] for i in range(len(longest_path))}
            for f in nested_filters:
                path = all_array_paths.get(f['column_name'])
                if path:
                    level = len(path) - 1
                    if level in filters_by_level:
                        filters_by_level[level].append(f)

            # --- Dynamic Pipeline Construction for Cascading Filter ---
            expression = None

            for i in range(len(longest_path) - 1, -1, -1):
                current_array_name = longest_path[i]
                item_as_variable = current_array_name[:-1] if current_array_name.endswith(
                    's') else f"{current_array_name}_item"
                current_path_prefix = '.'.join(longest_path[:i + 1])

                # Build conditions for the current aggregation level
                level_conditions = []
                if i in filters_by_level:
                    for f in filters_by_level[i]:
                        key = f['column_name']
                        field_in_element = key.replace(current_path_prefix + '.', '', 1)
                        single_filter_conditions = []

                        if f.get('filtered_values'):
                            single_filter_conditions.append(
                                {"$in": [f"$${item_as_variable}.{field_in_element}", f['filtered_values']]})

                        if f.get('text_filter') and f.get('text_filter_type'):
                            text_filter = f['text_filter']
                            text_filter_type = f['text_filter_type']
                            escaped_text = re.escape(text_filter)
                            field_path_expr = f"$${item_as_variable}.{field_in_element}"

                            text_condition = None
                            if text_filter_type == 'equals':
                                text_condition = {"$eq": [field_path_expr, text_filter]}
                            elif text_filter_type == 'notEqual':
                                text_condition = {"$ne": [field_path_expr, text_filter]}
                            elif text_filter_type == 'contains':
                                text_condition = {
                                    "$regexMatch": {"input": field_path_expr, "regex": escaped_text, "options": "i"}}
                            elif text_filter_type == 'notContains':
                                text_condition = {"$not": [
                                    {"$regexMatch": {"input": field_path_expr, "regex": escaped_text, "options": "i"}}]}
                            elif text_filter_type == 'beginsWith':
                                text_condition = {"$regexMatch": {"input": field_path_expr, "regex": f"^{escaped_text}",
                                                                  "options": "i"}}
                            elif text_filter_type == 'endsWith':
                                text_condition = {"$regexMatch": {"input": field_path_expr, "regex": f"{escaped_text}$",
                                                                  "options": "i"}}

                            if text_condition:
                                single_filter_conditions.append(text_condition)

                        if single_filter_conditions:
                            if len(single_filter_conditions) > 1:
                                level_conditions.append({"$and": single_filter_conditions})
                            else:
                                level_conditions.extend(single_filter_conditions)

                if expression is None:
                    # BASE CASE: Innermost array
                    expression = {
                        "$filter": {
                            "input": f"__PARENT__.{current_array_name}",
                            "as": item_as_variable,
                            "cond": {"$and": level_conditions} if level_conditions else {}
                        }
                    }
                else:
                    # RECURSIVE STEP for all parent arrays.
                    child_array_name = longest_path[i + 1]
                    child_expr_str = orjson.dumps(expression, default=non_jsonable_types_handler).decode().replace('"__PARENT__.', f'"$${item_as_variable}.')
                    resolved_child_expr = orjson.loads(child_expr_str)

                    map_expression = {
                        "$map": {
                            "input": f"__PARENT__.{current_array_name}",
                            "as": item_as_variable,
                            "in": {
                                "$let": {
                                    "vars": {"filtered_child": resolved_child_expr},
                                    "in": {"$mergeObjects": [f"$${item_as_variable}",
                                                             {child_array_name: "$$filtered_child"}]}
                                }
                            }
                        }
                    }

                    filter_item_var = f"{item_as_variable}_x"

                    # Build conditions for this level, using the new variable
                    current_level_conditions_for_filter = []
                    if i in filters_by_level:
                        for f in filters_by_level[i]:
                            key = f['column_name']
                            field_in_element = key.replace(current_path_prefix + '.', '', 1)
                            single_filter_conditions = []

                            if f.get('filtered_values'):
                                single_filter_conditions.append(
                                    {"$in": [f"$${filter_item_var}.{field_in_element}", f['filtered_values']]})

                            if f.get('text_filter') and f.get('text_filter_type'):
                                text_filter = f['text_filter']
                                text_filter_type = f['text_filter_type']
                                escaped_text = re.escape(text_filter)
                                field_path_expr = f"$${filter_item_var}.{field_in_element}"

                                text_condition = None
                                if text_filter_type == 'equals':
                                    text_condition = {"$eq": [field_path_expr, text_filter]}
                                elif text_filter_type == 'notEqual':
                                    text_condition = {"$ne": [field_path_expr, text_filter]}
                                elif text_filter_type == 'contains':
                                    text_condition = {"$regexMatch": {"input": field_path_expr, "regex": escaped_text,
                                                                      "options": "i"}}
                                elif text_filter_type == 'notContains':
                                    text_condition = {"$not": [{"$regexMatch": {"input": field_path_expr,
                                                                                "regex": escaped_text,
                                                                                "options": "i"}}]}
                                elif text_filter_type == 'beginsWith':
                                    text_condition = {
                                        "$regexMatch": {"input": field_path_expr, "regex": f"^{escaped_text}",
                                                        "options": "i"}}
                                elif text_filter_type == 'endsWith':
                                    text_condition = {
                                        "$regexMatch": {"input": field_path_expr, "regex": f"{escaped_text}$",
                                                        "options": "i"}}

                                if text_condition:
                                    single_filter_conditions.append(text_condition)

                            if single_filter_conditions:
                                if len(single_filter_conditions) > 1:
                                    current_level_conditions_for_filter.append({"$and": single_filter_conditions})
                                else:
                                    current_level_conditions_for_filter.extend(single_filter_conditions)

                    non_empty_child_condition = {"$gt": [{"$size": f"$${filter_item_var}.{child_array_name}"}, 0]}
                    all_conditions_for_level = [non_empty_child_condition] + current_level_conditions_for_filter

                    expression = {
                        "$filter": {
                            "input": map_expression,
                            "as": filter_item_var,
                            "cond": {"$and": all_conditions_for_level}
                        }
                    }

            # Replace the top-level placeholder with the root document operator '$'
            final_expression_str = orjson.dumps(expression, default=non_jsonable_types_handler).decode().replace('"__PARENT__.', '"$')
            final_expression = orjson.loads(final_expression_str)

            top_level_array = longest_path[0]
            pipeline.append({
                "$addFields": {
                    top_level_array: final_expression
                }
            })

    # Handle sorting after filter for efficiency - without pagination sort layer is redundant
    if sort_order:
        add_fields_for_abs_sort = {}
        sort_spec = {}

        # This list will store the fields to be removed after sorting
        unset_fields = []

        for so in sort_order:
            field = so['sort_by']
            direction = so['sort_direction']

            if so.get('is_absolute_sort', False):
                # For absolute sorting, we need to sort by the absolute value first,
                # and then by the original value to handle ties (e.g., -5 and 5).

                # 1. Create a temporary field for the absolute value.
                temp_field = f"abs_{field.replace('.', '_')}"
                add_fields_for_abs_sort[temp_field] = {'$abs': f'${field}'}

                # 2. The primary sort key is the temporary absolute value field.
                sort_spec[temp_field] = direction

                # 3. The secondary sort key is the original field itself.
                # This ensures that if absolute values are the same (e.g., abs(-5) and abs(5)),
                # the original values are used to break the tie.
                # Sorting by the original field in the same direction ensures that
                # for a descending sort, 5 comes before -5, and for an ascending sort, -5 comes before 5.
                sort_spec[field] = direction

                # 4. Mark the temporary field for removal after the sort.
                unset_fields.append(temp_field)
            else:
                # For regular sorting, just use the field and direction.
                sort_spec[field] = direction

        # Add the temporary fields to the pipeline if any were created.
        if add_fields_for_abs_sort:
            pipeline.append({"$addFields": add_fields_for_abs_sort})

        # Add the sort stage to the pipeline if there are any sort specifications.
        if sort_spec:
            pipeline.append({"$sort": sort_spec})

        # Remove the temporary fields from the pipeline if any were created.
        if unset_fields:
            pipeline.append({"$unset": unset_fields})

    if pagination:
        # Handle pagination at the end of the pipeline
        page_number = pagination.get('page_number')
        page_size = pagination.get('page_size')
        if page_number > 0 and page_size > 0:
            skip = (page_number - 1) * page_size
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": page_size})
    # else not required: If pagination is present then no sort required as sort is
    # only useful when pagination is required - without pagination sort layer is redundant

    return pipeline


def get_cascading_multi_filter_count_pipeline(model_class: Type, filters: List[Dict] | None = None):
    pipeline = create_cascading_multi_filter_pipeline(model_class, filters)

    # Finally, count the documents that match all criteria.
    pipeline.append({"$count": "filtered_count"})

    return {"aggregate": pipeline}


def item_matches_filters(item: dict, filters: list[dict]) -> bool:
    """
    Check if an item matches the given filters.

    Args:
        item: Document to check
        filters: List of filter definitions

    Returns:
        True if item matches all filters, False otherwise
    """
    if not filters:
        return True

    for filter_def in filters:
        column_name = filter_def["column_name"]

        # Get the field value using dot notation
        field_value = item
        for part in column_name.split('.'):
            if isinstance(field_value, dict) and part in field_value:
                field_value = field_value[part]
            else:
                field_value = None
                break

        # Check filtered_values condition
        if "filtered_values" in filter_def:
            filtered_values = filter_def["filtered_values"]
            if filter_def.get("filter_type") == "notIn":
                if field_value in filtered_values:
                    return False
            else:
                # Handle both string and non-string comparisons
                if isinstance(field_value, str) and isinstance(filtered_values[0], str):
                    if field_value not in filtered_values:
                        return False
                elif isinstance(field_value, bool) and isinstance(filtered_values[0], bool):
                    if field_value not in filtered_values:
                        return False
                else:
                    # Type mismatch, try string conversion
                    if str(field_value) not in [str(v) for v in filtered_values]:
                        return False

        # Check text_filter condition
        if "text_filter" in filter_def:
            text_filter = filter_def["text_filter"]
            text_filter_type = filter_def.get("text_filter_type", "contains")

            if not isinstance(field_value, str):
                return False

            text_lower = str(field_value).lower()
            filter_lower = text_filter.lower()

            if text_filter_type == "equals":
                if text_lower != filter_lower:
                    return False
            elif text_filter_type == "notEqual":
                if text_lower == filter_lower:
                    return False
            elif text_filter_type == "contains":
                if filter_lower not in text_lower:
                    return False
            elif text_filter_type == "notContains":
                if filter_lower in text_lower:
                    return False
            elif text_filter_type == "beginsWith":
                if not text_lower.startswith(filter_lower):
                    return False
            elif text_filter_type == "endsWith":
                if not text_lower.endswith(filter_lower):
                    return False

    return True


def is_relevant_update(before_item: Dict[str, Any], after_item: Dict[str, Any], filters: List[Dict[str, Any]],
                       sort_order: List[Dict[str, Any]]) -> bool:
    """
    Check if an update affects filter or sort fields (i.e., if it's relevant for change detection).

    Args:
        before_item: The item before the update
        after_item: The item after the update
        filters: List of filter definitions
        sort_order: List of sort definitions

    Returns:
        True if the update affects filter/sort fields, False otherwise
    """
    # If no filters or sort, any update is irrelevant
    if not filters and not sort_order:
        return False

    # Check filter field changes
    if filters:
        before_matches = item_matches_filters(before_item, filters)
        after_matches = item_matches_filters(after_item, filters)
        if before_matches != after_matches:
            return True

    # Check sort field changes
    if sort_order:
        for sort_def in sort_order:
            sort_by = sort_def["sort_by"]

            # Get field values using dot notation
            def get_field_value(item, field_path):
                value = item
                for part in field_path.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return None
                return value

            before_value = get_field_value(before_item, sort_by)
            after_value = get_field_value(after_item, sort_by)

            if before_value != after_value:
                return True

    return False


async def detect_multiple_page_changes(
        collection,  # MongoDB collection instance
        page_definitions: list[dict],  # List of page definitions with filters, sort, pagination
        created_items: list[dict],  # List of newly created documents (must have _id)
        deleted_item_ids: list,  # List of _id values for deleted documents
        model_class,  # Model class for type hints and structure
        updated_items: list[dict] = None  # List of updated documents (must have _id and at least one updated field)
) -> list[dict]:
    """
    Detects changes across multiple pages of data using MongoDB aggregation pipeline.
    All logic is handled in MongoDB aggregation pipeline for performance benefits.

    Args:
        collection: MongoDB collection instance
        page_definitions: List of page definitions with filters, sort, pagination
        created_items: List of newly created documents (must have _id)
        deleted_item_ids: List of _id values for deleted documents
        model_class: Model class for type hints and structure
        updated_items: List of updated documents (must have _id and at least one updated field)

    Returns:
        List of change reports for each page with detected changes
    """
    # Validate operation constraints - only one type of operation allowed per call
    operation_count = sum([
        bool(created_items),
        bool(deleted_item_ids),
        bool(updated_items)
    ])

    if operation_count > 1:
        raise ValueError("Only one type of operation (create, delete, or update) can be performed per call. "
                         "Parameters must be mutually exclusive.")

    # Validate updated_items structure if provided
    if updated_items is None:
        updated_items = []
    elif updated_items:
        for i, item in enumerate(updated_items):
            if not isinstance(item, dict):
                raise ValueError(f"updated_items[{i}] must be a dictionary")
            if "_id" not in item:
                raise ValueError(f"updated_items[{i}] must contain '_id' field")
            if len(item) < 2:  # Only _id field, no updated fields
                raise ValueError(f"updated_items[{i}] must contain at least one updated field besides '_id'")

    # Create temporary collections for created and updated items
    # Use hash-based naming to avoid namespace length limitations
    created_items_hash = hashlib.md5(orjson.dumps(created_items, default=non_jsonable_types_handler)).hexdigest()[
        :16] if created_items else "empty"
    updated_items_hash = hashlib.md5(orjson.dumps(updated_items, default=non_jsonable_types_handler)).hexdigest()[
        :16] if updated_items else "empty"

    created_temp_name = f"temp_created_{created_items_hash}"
    updated_temp_name = f"temp_updated_{updated_items_hash}"

    created_temp = collection.database[created_temp_name]
    updated_temp = collection.database[updated_temp_name]

    try:
        if created_items:
            await created_temp.insert_many(created_items)
        if updated_items:
            # Check for duplicate _id values in updated_items and remove duplicates
            unique_updated_items = {}
            for item in updated_items:
                item_id = item["_id"]
                # Merge items with the same _id, with later items taking precedence
                if item_id in unique_updated_items:
                    unique_updated_items[item_id].update(item)
                else:
                    unique_updated_items[item_id] = item.copy()

            # Convert back to list and use bulk_write with upsert to handle duplicates safely
            deduplicated_items = list(unique_updated_items.values())
            if deduplicated_items:
                # Use bulk_write with upsert operations to avoid duplicate key errors
                operations = [
                    UpdateOne(
                        {"_id": item["_id"]},
                        {"$set": item},
                        upsert=True
                    )
                    for item in deduplicated_items
                ]
                await updated_temp.bulk_write(operations)

        facet_stage = {}
        has_relevant_updates = False
        for page_def in page_definitions:
            page_id = page_def["page_id"]
            filters = page_def.get("filters", [])
            if filters is None:
                filters = []
            sort_order = page_def.get("sort_order", [])
            if sort_order is None:
                sort_order = []
            pagination = page_def.get("pagination", {})
            if pagination is None:
                pagination = {}
            custom_aggregation_before_filter_sort_pagination = page_def.get(
                "custom_aggregation_before_filter_sort_pagination", [])
            if custom_aggregation_before_filter_sort_pagination is None:
                custom_aggregation_before_filter_sort_pagination = []

            # --- "Before" Pipeline ---
            before_pipeline = create_cascading_multi_filter_pipeline(
                model_class=model_class, filters=filters, sort_order=sort_order, pagination=pagination
            )
            facet_stage[f"{page_id}_before"] = copy.deepcopy(custom_aggregation_before_filter_sort_pagination)
            facet_stage[f"{page_id}_before"].extend(before_pipeline)

            # --- "After" Pipeline ---
            # Create base pipeline that excludes deleted items
            after_filters = list(filters)
            if deleted_item_ids:
                after_filters.append(
                    {"column_name": "_id", "filtered_values": deleted_item_ids, "filter_type": "notIn"})

            # Exclude only relevant updated items from original pipeline
            # Relevant updates are those that affect filter or sort fields
            if updated_items:
                # Fetch original versions of updated items to compare
                updated_ids = [item["_id"] for item in updated_items]
                original_items_cursor = collection.find({"_id": {"$in": updated_ids}})
                original_items_dict = {item["_id"]: item for item in await original_items_cursor.to_list(length=None)}

                relevant_updated_ids = []
                for updated_item in updated_items:
                    item_id = updated_item["_id"]
                    original_item = original_items_dict.get(item_id)

                    if original_item:
                        # Check if this update is relevant (affects filter/sort fields)
                        if is_relevant_update(original_item, updated_item, filters, sort_order):
                            relevant_updated_ids.append(item_id)
                    else:
                        # Original item not found, treat as relevant by default
                        relevant_updated_ids.append(item_id)

                if relevant_updated_ids:
                    has_relevant_updates = True
                    after_filters.append(
                        {"column_name": "_id", "filtered_values": relevant_updated_ids, "filter_type": "notIn"})

            after_pipeline = create_cascading_multi_filter_pipeline(
                model_class=model_class, filters=after_filters, sort_order=sort_order, pagination=None
            )

            # Union created and updated items
            if created_items or updated_items:
                # First union created items
                if created_items:
                    after_pipeline.append({"$unionWith": {"coll": created_temp_name}})

                # Then union updated items (only if they were excluded from original data)
                if updated_items:
                    # Check if we excluded relevant updated items from the original pipeline
                    # Only union updated items that were actually excluded
                    excluded_updated_ids = []
                    if updated_items and (filters or sort_order):
                        # Only when there are filters or sort order could updates be excluded
                        updated_ids = [item["_id"] for item in updated_items]
                        original_items_cursor = collection.find({"_id": {"$in": updated_ids}})
                        original_items_dict = {item["_id"]: item for item in
                                               await original_items_cursor.to_list(length=None)}

                        for updated_item in updated_items:
                            item_id = updated_item["_id"]
                            original_item = original_items_dict.get(item_id)

                            if original_item:
                                # Check if this update is relevant (affects filter/sort fields)
                                if is_relevant_update(original_item, updated_item, filters, sort_order):
                                    excluded_updated_ids.append(item_id)
                            else:
                                # Original item not found, treat as excluded
                                excluded_updated_ids.append(item_id)

                    if excluded_updated_ids:
                        after_pipeline.append({"$unionWith": {"coll": updated_temp_name}})
                    else:
                        pass

                # After union, apply the page filters to maintain filter isolation
                # This ensures only items matching filters affect the final result
                if filters:
                    for filter_def in filters:
                        column_name = filter_def["column_name"]

                        if "filtered_values" in filter_def:
                            filtered_values = filter_def["filtered_values"]
                            after_pipeline.append({
                                "$match": {column_name: {"$in": filtered_values}}
                            })
                        elif "text_filter" in filter_def:
                            text_filter = filter_def["text_filter"]
                            text_filter_type = filter_def.get("text_filter_type", "contains")

                            if text_filter_type == "contains":
                                regex_pattern = f".*{re.escape(text_filter)}.*"
                            elif text_filter_type == "beginsWith":
                                regex_pattern = f"^{re.escape(text_filter)}.*"
                            elif text_filter_type == "endsWith":
                                regex_pattern = f".*{re.escape(text_filter)}$"
                            elif text_filter_type == "equals":
                                regex_pattern = f"^{re.escape(text_filter)}$"
                            elif text_filter_type == "notEqual":
                                regex_pattern = f"^(?!.*{re.escape(text_filter)}).*$"
                            elif text_filter_type == "notContains":
                                regex_pattern = f"^(?!.*{re.escape(text_filter)}).*$"
                            else:
                                regex_pattern = f".*{text_filter}.*"

                            after_pipeline.append({
                                "$match": {column_name: {"$regex": regex_pattern, "$options": "i"}}
                            })

            # Add sorting and pagination after the union
            if sort_order:
                add_fields_for_abs_sort = {}
                sort_spec = {}
                unset_fields = []
                for so in sort_order:
                    field, direction = so['sort_by'], so['sort_direction']
                    if so.get('is_absolute_sort', False):
                        temp_field = f"abs_{field.replace('.', '_')}"
                        add_fields_for_abs_sort[temp_field] = {'$abs': f'${field}'}
                        sort_spec[temp_field], sort_spec[field] = direction, direction
                        unset_fields.append(temp_field)
                    else:
                        sort_spec[field] = direction
                if add_fields_for_abs_sort: after_pipeline.append({"$addFields": add_fields_for_abs_sort})
                if sort_spec: after_pipeline.append({"$sort": sort_spec})
                if unset_fields: after_pipeline.append({"$unset": unset_fields})
            else:
                # When no sort order is defined, preserve natural order
                # Use $sort with {$_id: 1} only if needed for consistency, but prefer natural order
                pass  # Keep natural order

            if pagination:
                page_number, page_size = pagination.get('page_number'), pagination.get('page_size')
                if page_number > 0 and page_size > 0:
                    after_pipeline.extend([{"$skip": (page_number - 1) * page_size}, {"$limit": page_size}])

            facet_stage[f"{page_id}_after"] = copy.deepcopy(custom_aggregation_before_filter_sort_pagination)
            facet_stage[f"{page_id}_after"].extend(after_pipeline)

        if not facet_stage:
            return []

        result = await collection.aggregate([{"$facet": facet_stage}]).to_list(1)
        if not result:
            return []

        all_pages_data = result[0]
        final_reports = []

        for page_def in page_definitions:
            page_id = page_def["page_id"]
            filters = page_def.get("filters", [])  # Extract filters from page definition
            if filters is None:
                filters = []
            sort_order = page_def.get("sort_order", [])
            if sort_order is None:
                sort_order = []
            pagination = page_def.get("pagination", {})
            if pagination is None:
                pagination = {}
            # Store the original custom aggregation for later use
            custom_aggregation_before_filter_sort_pagination = page_def.get(
                "custom_aggregation_before_filter_sort_pagination", [])
            if custom_aggregation_before_filter_sort_pagination is None:
                custom_aggregation_before_filter_sort_pagination = []

            before_items = all_pages_data.get(f"{page_id}_before", [])
            after_items = all_pages_data.get(f"{page_id}_after", [])
            before_ids = {item["_id"] for item in before_items}
            after_ids = {item["_id"] for item in after_items}
            created_ids = {item["_id"] for item in created_items}
            updated_ids = {item["_id"] for item in updated_items}
            deleted_ids_set = set(deleted_item_ids)

            changes = []

            # Helper function to get deterministic sort key for tie resolution
            def get_sort_key(item, sort_order_list):
                """Create a deterministic sort key including _id for tie-breaking"""
                key = []
                for so in sort_order_list:
                    field = so['sort_by']
                    direction = so['sort_direction']
                    value = item.get(field, None)
                    # Handle None values consistently
                    if value is None:
                        key.append(None if direction == 1 else float('inf'))
                    else:
                        key.append(value)
                # Add _id as final tie-breaker for deterministic ordering
                key.append(item['_id'])
                return tuple(key)

            # --- Deletion Detection ---
            deleted_on_page = before_ids - after_ids
            for item_id in deleted_on_page:
                if item_id in deleted_ids_set:
                    changes.append({"_id": item_id})

            # --- Update Detection ---
            if filters:
                # For filtered pages, check filter-eligibility changes
                for item_id in updated_ids:
                    updated_item = next((item for item in updated_items if item["_id"] == item_id), None)
                    if updated_item:
                        # For items not found in before_items, check if they should be there by querying the database
                        before_item = next((item for item in before_items if item["_id"] == item_id), None)
                        if before_item is None:
                            # Item not in before_items, check if it exists in database and matches filters
                            try:
                                db_item = await collection.find_one({"_id": item_id})
                                if db_item and item_matches_filters(db_item, filters):
                                    # Item exists in DB and matches filters, should be in before_items but isn't
                                    # This could be due to pagination/limiting issues
                                    before_item = db_item
                            except Exception:
                                # If we can't check the database, continue with before_item as None
                                pass

                        before_matches = item_matches_filters(before_item, filters) if before_item else False
                        after_matches = item_matches_filters(updated_item, filters)

                        # Only process if the item was originally in the page OR will be in the page after
                        was_in_page_before = item_id in before_ids
                        # Check if the item will actually be in the page after the update
                        will_be_in_page_after = after_matches and item_id in after_ids

                        if was_in_page_before:
                            # Item was in the page before
                            if before_matches and not after_matches:
                                # Update makes item no longer match filters - treat as deletion
                                changes.append({"_id": item_id})
                            elif after_matches:
                                # Update keeps item in filters - check for sort position changes
                                if sort_order and pagination:
                                    # Check if position changed within the page using deterministic sort keys
                                    before_item = next((item for item in before_items if item["_id"] == item_id), None)
                                    after_item = next((item for item in after_items if item["_id"] == item_id), None)

                                    if before_item and after_item:
                                        # Compare actual sort keys instead of array positions
                                        before_key = get_sort_key(before_item, sort_order)
                                        after_key = get_sort_key(after_item, sort_order)

                                        if before_key != after_key:
                                            # Item's sort position changed
                                            after_top_key = get_sort_key(after_items[0], sort_order)
                                            after_bottom_key = get_sort_key(after_items[-1], sort_order)

                                            if after_key == after_top_key:
                                                # Moved to top position
                                                changes.append({**updated_item, "_new_top": True})
                                            elif after_key == after_bottom_key:
                                                # Moved to bottom position
                                                changes.append({**updated_item, "_new_bottom": True})
                                            else:
                                                # Still in page but no boundary change
                                                changes.append(updated_item)
                                        else:
                                            # Sort position unchanged, just return the updated item
                                            changes.append(updated_item)
                                    elif before_item and not after_item:
                                        # Item was in the page before but moved out due to sort change - treat as deletion
                                        changes.append({"_id": item_id})
                                    else:
                                        # Item couldn't be determined or unchanged
                                        changes.append(updated_item)
                                else:
                                    # No sort or no pagination, just return updated item
                                    changes.append(updated_item)
                        elif will_be_in_page_after and not was_in_page_before:
                            # Update makes item match filters and it's now in the page - treat as creation
                            changes.append(updated_item)
                        else:
                            pass
            else:
                # For filter-ignorant pages, only process updates that affect the page
                if sort_order and pagination:
                    for item_id in updated_ids:
                        updated_item = next((item for item in updated_items if item["_id"] == item_id), None)
                        if updated_item:
                            # Check if item was in the page before
                            before_item = next((item for item in before_items if item["_id"] == item_id), None)
                            if before_item:
                                # Item was in the page before, check if it's still in the page after
                                after_item = next((item for item in after_items if item["_id"] == item_id), None)
                                if after_item:
                                    # Item is still in the page, check position change
                                    before_position = next(
                                        (i for i, item in enumerate(before_items) if item["_id"] == item_id), None)
                                    after_position = next(
                                        (i for i, item in enumerate(after_items) if item["_id"] == item_id), None)

                                    if before_position is not None and after_position is not None:
                                        if after_position == 0 and before_position != 0:
                                            # Moved to top
                                            changes.append({**updated_item, "_new_top": True})
                                        elif after_position == len(after_items) - 1 and before_position != len(
                                                after_items) - 1:
                                            # Moved to bottom
                                            changes.append({**updated_item, "_new_bottom": True})
                                        else:
                                            # Still in page but no boundary change
                                            changes.append(updated_item)
                                else:
                                    # Item moved out of page due to sort change
                                    changes.append({"_id": item_id})
                            else:
                                # Item wasn't in page before, check if it moved into page
                                after_item = next((item for item in after_items if item["_id"] == item_id), None)
                                if after_item:
                                    if after_items and after_item["_id"] == after_items[0]["_id"]:
                                        changes.append({**updated_item, "_new_top": True})
                                    elif after_items and after_item["_id"] == after_items[-1]["_id"]:
                                        changes.append({**updated_item, "_new_bottom": True})
                                    else:
                                        changes.append(updated_item)
                else:
                    # No sort or no pagination, just return updated items that were in the page
                    for item_id in updated_ids:
                        if item_id in before_ids:
                            updated_item = next((item for item in updated_items if item["_id"] == item_id), None)
                            if updated_item:
                                changes.append(updated_item)
                        else:
                            pass

            # --- Created Items Detection ---
            for item_id in created_ids:
                if item_id in after_ids:
                    created_item = next((item for item in created_items if item["_id"] == item_id), None)
                    if created_item:
                        # Mark created items with boundary flags if they're at boundaries
                        if pagination and after_items:
                            if item_id == after_items[0]["_id"]:
                                changes.append({**created_item, "_new_top": True})
                            elif item_id == after_items[-1]["_id"]:
                                changes.append({**created_item, "_new_bottom": True})
                            else:
                                changes.append(created_item)
                        else:
                            changes.append(created_item)

            # --- Boundary Change Detection (only when pagination is provided) ---
            if pagination and after_items and before_items:
                # Detect top boundary change with tie resolution
                before_top_key = get_sort_key(before_items[0], sort_order)
                after_top_key = get_sort_key(after_items[0], sort_order)

                # Check if top boundary actually changed (accounting for ties)
                if before_top_key != after_top_key:
                    if not any(change.get("_new_top") and change["_id"] == after_items[0]["_id"] for change in changes):
                        changes.append({**after_items[0], "_new_top": True})

                # Detect bottom boundary change with tie resolution
                before_bottom_key = get_sort_key(before_items[-1], sort_order)
                after_bottom_key = get_sort_key(after_items[-1], sort_order)

                # Check if bottom boundary actually changed (accounting for ties)
                if before_bottom_key != after_bottom_key:
                    if not any(
                            change.get("_new_bottom") and change["_id"] == after_items[-1]["_id"] for change in changes):
                        # For single item pages, ensure both flags are set
                        if len(after_items) == 1:
                            existing_change = next(
                                (change for change in changes if change["_id"] == after_items[0]["_id"]), None)
                            if existing_change and existing_change.get("_new_top"):
                                existing_change["_new_bottom"] = True
                            else:
                                changes.append({**after_items[0], "_new_bottom": True})
                        else:
                            changes.append({**after_items[-1], "_new_bottom": True})

            # --- Special Cases ---

            # Handle items that moved into page due to deletions/shifts
            if pagination and (deleted_item_ids or has_relevant_updates):
                moved_into_page = []
                for item in after_items:
                    if item["_id"] not in before_ids and item["_id"] not in created_ids and item[
                        "_id"] not in updated_ids:
                        moved_into_page.append(item)

                for moved_item in moved_into_page:
                    moved_key = get_sort_key(moved_item, sort_order)

                    # Check if moved item is at top boundary using deterministic comparison
                    if moved_key == get_sort_key(after_items[0], sort_order):
                        if not any(change.get("_new_top") and change["_id"] == moved_item["_id"] for change in changes):
                            changes.append({**moved_item, "_new_top": True})
                    # Check if moved item is at bottom boundary using deterministic comparison
                    elif moved_key == get_sort_key(after_items[-1], sort_order):
                        if not any(
                                change.get("_new_bottom") and change["_id"] == moved_item["_id"] for change in changes):
                            changes.append({**moved_item, "_new_bottom": True})
                    else:
                        # For items moved into middle position:
                        # Include them for single-page deletion scenarios (shifts from next pages)
                        # Include them for filter scenarios (filter compliance changes)
                        # BUT be more selective in multi-page deletion scenarios
                        if deleted_item_ids:
                            # Multi-page deletion scenario - only include if this is the only page being processed
                            if len(page_definitions) == 1:
                                changes.append(moved_item)
                            else:
                                pass
                        elif filters and has_relevant_updates:
                            changes.append(moved_item)
                        else:
                            pass

            # Handle case where page size changed due to filter deletion
            if pagination and filters and has_relevant_updates:
                expected_page_size = pagination.get('page_size')
                actual_after_size = len(after_items)

                # Check if we lost items and the page is not full
                if actual_after_size < expected_page_size:
                    # We lost items, find what should be the new bottom item
                    try:
                        # Build the pipeline to find the next item using the same logic as the page definition
                        extended_pipeline = []

                        # Add custom aggregation if present
                        if custom_aggregation_before_filter_sort_pagination:
                            extended_pipeline.extend(copy.deepcopy(custom_aggregation_before_filter_sort_pagination))

                        # Build the base pipeline with filters and sort but without pagination
                        base_pipeline = create_cascading_multi_filter_pipeline(
                            model_class=model_class,
                            filters=filters,
                            sort_order=sort_order,
                            pagination=None  # No pagination for finding next item
                        )
                        extended_pipeline.extend(base_pipeline)

                        # Skip the items we already have and get the next one
                        extended_pipeline.extend([
                            {"$skip": actual_after_size},  # Skip current after_items
                            {"$limit": 1}  # Get just the next item
                        ])

                        next_items = await collection.aggregate(extended_pipeline).to_list(1)
                        if next_items:
                            next_item = next_items[0]
                            # Add this item as _new_bottom
                            changes.append({**next_item, "_new_bottom": True})
                    except Exception:
                        # If we can't find the next item, just continue without it
                        pass

            # --- Final Deduplication and Cleanup ---
            # Remove duplicate changes by _id, but keep different types of changes separately
            unique_changes = {}
            for change in changes:
                change_id = change["_id"]
                change_type = "deletion" if len(change) == 1 else "full_item"

                # Create a unique key based on _id and change type
                unique_key = f"{change_id}_{change_type}"

                # Store the change with its unique key
                unique_changes[unique_key] = change

            final_changes = list(unique_changes.values())

            # Sort changes according to sort_order if provided
            if sort_order and final_changes:
                # Create a mapping of item_id to full item data for sorting
                item_data_map = {}

                # First, populate with updated_items data
                for updated_item in updated_items:
                    item_id = updated_item["_id"]
                    item_data_map[item_id] = updated_item

                # For items that are filtered out (only have _id), fetch from database
                filtered_out_ids = [change["_id"] for change in final_changes if len(change) == 1]
                if filtered_out_ids:
                    try:
                        db_items_cursor = collection.find({"_id": {"$in": filtered_out_ids}})
                        db_items_dict = {item["_id"]: item for item in await db_items_cursor.to_list(length=None)}
                        item_data_map.update(db_items_dict)
                    except Exception:
                        pass  # If we can't fetch from DB, continue with available data

                def get_sort_value(change, sort_def):
                    field = sort_def['sort_by']
                    direction = sort_def['sort_direction']
                    item_id = change["_id"]

                    # Get the full item data for sorting
                    sort_item = item_data_map.get(item_id, change)
                    value = sort_item.get(field, 0)

                    # Handle absolute sorting
                    if sort_def.get('is_absolute_sort', False) and isinstance(value, (int, float)):
                        value = abs(value)

                    # Handle None values
                    if value is None:
                        value = 0

                    return value if direction > 0 else -value

                try:
                    # Separate items into "full items" and "filtered out items"
                    # Full items: have more than just _id field (remain in filters)
                    # Filtered out items: only have _id field (filtered out)
                    full_items = [change for change in final_changes if len(change) > 1]
                    filtered_items = [change for change in final_changes if len(change) == 1]

                    # Sort each group separately
                    if full_items:
                        full_items.sort(key=lambda change: tuple(
                            get_sort_value(change, sort_def) for sort_def in sort_order
                        ))

                    if filtered_items:
                        filtered_items.sort(key=lambda change: tuple(
                            get_sort_value(change, sort_def) for sort_def in sort_order
                        ))

                    # Combine: full items first, then filtered items
                    final_changes = full_items + filtered_items

                except Exception:
                    # If sorting fails, keep original order
                    pass

            # Remove boundary flags when no pagination
            if not pagination:
                for change in final_changes:
                    if "_new_top" in change:
                        del change["_new_top"]
                    if "_new_bottom" in change:
                        del change["_new_bottom"]

            final_reports.append({"page_id": page_id, "changes": final_changes})

        return final_reports

    finally:
        # Clean up temporary collections
        if created_items:
            await created_temp.drop()
        if updated_items:
            await updated_temp.drop()

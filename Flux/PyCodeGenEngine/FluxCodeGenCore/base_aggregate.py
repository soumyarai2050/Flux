# standard imports
from typing import List
import orjson
import importlib
import inspect
import typing
from typing import Type, Any
import re

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
                    child_expr_str = orjson.dumps(expression).decode().replace('"__PARENT__.', f'"$${item_as_variable}.')
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
            final_expression_str = orjson.dumps(expression).decode().replace('"__PARENT__.', '"$')
            final_expression = orjson.loads(final_expression_str)

            top_level_array = longest_path[0]
            pipeline.append({
                "$addFields": {
                    top_level_array: final_expression
                }
            })

    if pagination:
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

        # Handle pagination at the end of the pipeline
        page_number = pagination.get('page_number', 1)
        page_size = pagination.get('page_size', 10)
        if page_number > 0 and page_size > 0:
            skip = (page_number - 1) * page_size
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": page_size})
    # else not required: If pagination is present then no sort required as sort is
    # only useful when pagination is required - without pagination sort layer is redundant

    return pipeline


def get_cascading_multi_filter_count_pipeline(model_class: Type, filter_dict):
    pipeline = create_cascading_multi_filter_pipeline(model_class, filter_dict)

    # Finally, count the documents that match all criteria.
    pipeline.append({"$count": "filtered_count"})

    return {"aggregate": pipeline}

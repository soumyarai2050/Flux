from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import street_book_config_yaml_path
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.conftest import *


def test_avoid_db_update(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                         expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                         market_depth_basemodel_list, last_barter_fixture_list):

    config_dict = YAMLConfigurationManager.load_yaml_configurations(str(street_book_config_yaml_path))
    config_dict["avoid_cpp_db_update"] = True
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(street_book_config_yaml_path))

    # creates and activates multiple pair_plans
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        activated_pair_plan, executor_web_client = create_n_activate_plan(leg1_symbol, leg2_symbol, pair_plan_,
                                                                            expected_plan_limits_,
                                                                            expected_plan_status_,
                                                                            symbol_overview_obj_list,
                                                                            market_depth_basemodel_list)

        run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_pair_plan.cpp_port)
        top_of_book_list: List[TopOfBookBaseModel] = executor_web_client.get_all_top_of_book_client()
        market_depth_list: List[MarketDepthBaseModel] = cpp_get_all_market_depth_client(activated_pair_plan.cpp_port)
        last_barter_list: List[LastBarterBaseModel] = executor_web_client.get_all_last_barter_client()

        assert top_of_book_list == []
        assert market_depth_list == []
        assert last_barter_list == []
    config_dict["avoid_cpp_db_update"] = False
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(street_book_config_yaml_path))


import os
from pathlib import PurePath


def test_build_and_clean_web_project(root_dir: PurePath, build_and_clean_web_project_path: PurePath):
    list_of_generated_files: list = ['Layout.jsx', 'OrderLimits.jsx', 'orderLimitsSlice.js', 'PairStratParams.jsx',
                                     'pairStratSlice.js', 'PortfolioLimits.jsx', 'portfolioLimitsSlice.js',
                                     'PortfolioStatus.jsx', 'portfolioStatusSlice.js', 'projectSpecificUtils.js',
                                     'store.js', 'strat_core_pb2.py', 'strat_manager_service_beanie_database.py',
                                     'strat_manager_service_beanie_fastapi.py', 'strat_manager_service_beanie_model.py',
                                     'strat_manager_service_cache_fastapi.py', 'strat_manager_service_cache_model.py',
                                     'strat_manager_service_callback_override_set_instance.py',
                                     'strat_manager_service_json_sample.json', 'strat_manager_service_json_schema.json',
                                     'strat_manager_service_launch_server.py', 'strat_manager_service_model_imports.py',
                                     'strat_manager_service_pb2.py', 'strat_manager_service_routes.py',
                                     'strat_manager_service_routes_callback.py',
                                     'strat_manager_service_routes_callback_beanie_override.py',
                                     'strat_manager_service_http_client.py',
                                     'strat_manager_service_ws_client.py', 'StratCollection.jsx',
                                     'stratCollectionSlice.js', 'StratLimits.jsx', 'StratStatus.jsx', 'uiLayoutSlice.js'
                                     ]
    generated_files_dir_path: PurePath = root_dir / 'CodeGenProjects' / 'phone_book' / 'generated'

    list_of_files_generated_in_dir = os.listdir(generated_files_dir_path)
    if all(word in list_of_files_generated_in_dir for word in list_of_generated_files):
        os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh clean-web-project.sh') == mobile_book
        # os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh build_web_project.sh') == mobile_book
    else:
        os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh build_web_project.sh') == mobile_book

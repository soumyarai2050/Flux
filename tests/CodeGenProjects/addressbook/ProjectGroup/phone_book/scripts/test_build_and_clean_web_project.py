import os
from pathlib import PurePath


def test_build_and_clean_web_project(root_dir: PurePath, build_and_clean_web_project_path: PurePath):
    list_of_generated_files: list = ['Layout.jsx', 'ChoreLimits.jsx', 'choreLimitsSlice.js', 'PairPlanParams.jsx',
                                     'pairPlanSlice.js', 'ContactLimits.jsx', 'contactLimitsSlice.js',
                                     'ContactStatus.jsx', 'contactStatusSlice.js', 'projectSpecificUtils.js',
                                     'store.js', 'plan_core_pb2.py', 'email_book_service_beanie_database.py',
                                     'email_book_service_beanie_fastapi.py', 'email_book_service_beanie_model.py',
                                     'email_book_service_cache_fastapi.py', 'email_book_service_cache_model.py',
                                     'email_book_service_callback_override_set_instance.py',
                                     'email_book_service_json_sample.json', 'email_book_service_json_schema.json',
                                     'email_book_service_launch_server.py', 'email_book_service_model_imports.py',
                                     'email_book_service_pb2.py', 'email_book_service_routes.py',
                                     'email_book_service_routes_callback.py',
                                     'email_book_service_routes_callback_beanie_override.py',
                                     'email_book_service_http_client.py',
                                     'email_book_service_ws_client.py', 'PlanCollection.jsx',
                                     'planCollectionSlice.js', 'PlanLimits.jsx', 'PlanStatus.jsx', 'uiLayoutSlice.js'
                                     ]
    generated_files_dir_path: PurePath = root_dir / 'CodeGenProjects' / 'phone_book' / 'generated'

    list_of_files_generated_in_dir = os.listdir(generated_files_dir_path)
    if all(word in list_of_files_generated_in_dir for word in list_of_generated_files):
        os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh clean-web-project.sh') == 0
        # os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh build_web_project.sh') == 0
    else:
        os.chdir(build_and_clean_web_project_path)
        assert os.system(f'sh build_web_project.sh') == 0

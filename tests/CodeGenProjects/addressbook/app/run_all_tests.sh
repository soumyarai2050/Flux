pytest test_strat_manager_service_routes_callback_override.py -v --html=../test_reports/"test_strat_manager_service_routes_callback_override_report_$(date +"%FT%H%M%S").html" --self-contained-html;
pytest test_strat_executor.py -v --html=../test_reports/"test_strat_executor$(date +"%FT%H%M%S").html" --self-contained-html
pytest test_strat_recovery.py -v --html=../test_reports/"test_strat_executor$(date +"%FT%H%M%S").html" --self-contained-html

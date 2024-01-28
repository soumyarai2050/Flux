pytest -m recovery -v --html=../test_reports/"test_recovery$(date +"%FT%H%M%S").html" --self-contained-html
pytest -m nightly -v --html=../test_reports/"test_nightly$(date +"%FT%H%M%S").html" --self-contained-html

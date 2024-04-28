python -m pytest -m recovery -v --html=../test_reports/"test_recovery$(date +"%FT%H%M%S").html" --self-contained-html
python -m pytest -m nightly -v --html=../test_reports/"test_nightly$(date +"%FT%H%M%S").html" --self-contained-html

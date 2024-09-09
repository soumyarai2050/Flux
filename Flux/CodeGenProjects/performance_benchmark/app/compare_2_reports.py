# standard imports
from typing import Dict, List
import pandas as pd
from pathlib import PurePath
from datetime import datetime


pd.set_option('display.precision', 10)  # setting up the precision point so can see the data how looks, here is 5


def compare_2_reports(file_path_1: PurePath | str, file_path_2: PurePath | str, output_path: PurePath | str) -> None:
    """
    compares 2 csv files and generate output of file1 - file2 per each callable_name for all numeric columns
    """

    columns = ['compared_callables', 'count', 'compared_min', 'latest_min', 'compared_max', 'latest_max', 'compared_median',
               'latest_median', 'compared_perc_25', 'latest_perc_25', 'compared_perc_50', 'latest_perc_50',
               'compared_perc_75', 'latest_perc_75', 'compared_perc_90', 'latest_perc_90', 'compared_perc_95',
               'latest_perc_95']

    df1 = pd.read_csv(file_path_1)
    df2 = pd.read_csv(file_path_2)
    new_df = pd.DataFrame(columns=columns)

    df1_callable_prefix_to_callable_name_to_idx_dict: Dict[str, Dict[str, int]] = {}
    df2_callable_prefix_to_callable_name_to_idx_dict: Dict[str, Dict[str, int]] = {}

    # initializing dict for callable_name to index
    for df, df_callable_prefix_to_callable_name_to_idx_dict in [(df1, df1_callable_prefix_to_callable_name_to_idx_dict),
                                                                (df2, df2_callable_prefix_to_callable_name_to_idx_dict)]:
        for idx in df.index:
            callable_name = df["callable_name"][idx]
            try:
                callable_prefix = callable_name[:callable_name.index('http')]
            except ValueError:
                callable_prefix = callable_name

            if callable_prefix not in df_callable_prefix_to_callable_name_to_idx_dict:
                df_callable_prefix_to_callable_name_to_idx_dict[callable_prefix] = {callable_name: idx}
            else:
                df_callable_prefix_to_callable_name_to_idx_dict[callable_prefix][callable_name] = idx

    for cal_prefix, callable_name_to_idx_dict in df1_callable_prefix_to_callable_name_to_idx_dict.items():
        other_callable_name_to_idx_dict = df2_callable_prefix_to_callable_name_to_idx_dict.get(cal_prefix)
        if other_callable_name_to_idx_dict is not None:
            for callable_name, idx in callable_name_to_idx_dict.items():
                for other_callable_name, other_idx in other_callable_name_to_idx_dict.items():
                    # if exact same name is found in new
                    new_row_dict = {'compared_callables': f"{callable_name}-{other_callable_name}"}

                    for col in columns:
                        if col == 'compared_callables':
                            continue    # avoiding str type column
                        elif col.startswith('latest'):
                            new_row_dict[col] = df2[col[len("latest_"):]][other_idx]
                        elif col.startswith('compared'):
                            new_row_dict[col] = (df1[col[len("compared_"):]][idx] -
                                                 df2[col[len("compared_"):]][other_idx])
                        elif col == "count":
                            new_row_dict[col] = f"{df1[col][idx]}-{df2[col][other_idx]}"

                    new_df.loc[len(new_df)] = new_row_dict
        else:
            pass

    new_df.to_csv(output_path, columns=columns, float_format='%.6f', index=False)


if __name__ == '__main__':

    test_report_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "tests" / "CodeGenProjects" /
                       "TradeEngine" / "ProjectGroup" / "test_reports" / "performance_data")

    # file_path_1_ = test_report_dir / "beanie_20_performance_data_20240711_173529.csv"
    file_path_1_ = test_report_dir / "log_analyzer_beanie_performance_data_20240813_002335.csv"
    file_path_2_ = test_report_dir / "log_analyzer_msgspec_performance_data_20240814_020005.csv"
    # file_path_1_ = test_report_dir / "msgspec_20_performance_data_20240723_013308.csv"
    # file_path_2_ = test_report_dir / "msgspec_20_performance_data_20240727_032935.csv"
    datetime_str: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path_ = test_report_dir / f"compared_reports_{datetime_str}.csv"

    compare_2_reports(file_path_1_, file_path_2_, output_path_)

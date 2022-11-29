import sys
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from json_plugin_execute_script import JsonPluginExecuteScript


if __name__ == "__main__":
    def main():
        match len(sys.argv):
            case 2:
                project_dir_path = sys.argv[1]
                config_path = None
            case 3:
                project_dir_path = sys.argv[1]
                config_path = sys.argv[2]
            case other:
                raise Exception("Invalid arguments, pass only project's base path")

        json_plugin_execute_script = JsonPluginExecuteScript(project_dir_path, config_path)
        json_plugin_execute_script.execute()

    main()

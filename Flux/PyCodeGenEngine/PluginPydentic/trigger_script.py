import sys
import time
import os

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from pydantic_plugin_execute_script import PydanticPluginExecuteScript


if __name__ == "__main__":
    def main():
        match len(sys.argv):
            case 2:
                project_dir_path = sys.argv[1]
            case other:
                raise Exception("Invalid arguments, usage: python trigger_script.py <project_dir_path>")

        json_plugin_execute_script = PydanticPluginExecuteScript(project_dir_path)
        json_plugin_execute_script.execute()

    main()

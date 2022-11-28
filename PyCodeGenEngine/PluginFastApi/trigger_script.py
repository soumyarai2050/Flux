import sys
from fastapi_plugin_execute_script import FastApiPluginExecuteScript

project_dir_path: str
config_path: str | None
match len(sys.argv):
    case 1:
        pass
    case 2:
        project_dir_path = sys.argv[1]
        config_path = None
    case 3:
        project_dir_path = sys.argv[1]
        config_path = sys.argv[2]
    case other:
        raise Exception("Invalid arguments, pass only project's base path")

if __name__ == "__main__":
    def main():
        json_plugin_execute_script = FastApiPluginExecuteScript(project_dir_path, config_path)
        json_plugin_execute_script.execute()
    main()

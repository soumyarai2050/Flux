import sys
from jsx_plugin_execute_script import JsxPluginExecuteScript

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
        # time.sleep(10)
        jsx_plugin_execute_script = JsxPluginExecuteScript(project_dir_path, config_path)
        jsx_plugin_execute_script.execute()

    main()

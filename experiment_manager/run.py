import sys
import json
import os
import importlib.util

CONFIG_FOLDER_PATH = '/home/user/project/25050300iGemLLM/QA/'
sys.path.append(CONFIG_FOLDER_PATH)
import path_config

def run_experiment(config_path, expr_path):
    print(f"run_experiment(config_path=\"{config_path}\", expr_path=\"{expr_path}\")")
    with open(path_config.PATH_EXPERIMENT_MANAGER + "default_config.json", 'r') as f:
        default_config = json.load(f)
    with open(config_path, 'r') as f:
        config = json.load(f)

    def merge_configs(default_config, config):
        merged_config = default_config.copy()
        for key, value in config.items():
            if key not in merged_config:
                pass
            elif isinstance(value, dict) and isinstance(merged_config[key], dict):
                merged_config[key] = merge_configs(merged_config[key], value)
            else:
                merged_config[key] = value
        return merged_config
    final_config = merge_configs(default_config, config)

    if not os.path.exists(expr_path):
        os.makedirs(expr_path)

    spec = importlib.util.spec_from_file_location("myMain", path_config.PATH_MAIN + final_config["entry"])
    myMain = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(myMain)

    myMain.main(final_config, expr_path)


if __name__ == '__main__':
    if len(sys.argv) != 3 and len(sys.argv) != 2:
        print("Usage: python run.py <configFilePath> <saveFolderPath> OR python run.py <configFolderPath>")
        sys.exit(1)

    config_path = sys.argv[1]
    expr_path = sys.argv[2] if len(sys.argv) == 3 else os.path.dirname(config_path) + "/"

    run_experiment(config_path, expr_path)

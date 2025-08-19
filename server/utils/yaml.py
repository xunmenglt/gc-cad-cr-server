import yaml
def read_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
# 将修改后的数据写入 YAML 文件
def write_yaml(file_path, data):
    with open(file_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)
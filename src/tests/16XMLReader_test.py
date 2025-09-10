import re
from lxml import etree

tree = etree.parse("/opt/data/private/liuteng/code/gc-cad-cr/data/input/中心区N1区学校/计价文件/中心区N1区学校建设工程.xml")  # 替换为你的文件路径

# 找出所有含有属性值中包含“电梯DT”的节点
nodes = tree.xpath('//*')  # 获取所有节点

matched_values = []

for node in nodes:
    matched_values.append("|".join(node.attrib.values()))
            
# 用空格连接所有属性值
result = '\n'.join(matched_values)

pattern='电梯DT(\d+)'
matches = re.findall(pattern, result)
print(set(matches))





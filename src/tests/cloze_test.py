import re


def run():
    text="二类高层类建筑，耐火等级__级地下室耐火等级___级"
    values=["一"]
    # 动态填充值的生成函数
    def dynamic_replacement(match):
        nonlocal values
        # 记录替换的次数（可用全局变量或函数属性）
        value=match.group()
        if values:
            value=values[0]
            values=values[1:]
        return f"{value}"
    pattern = r"_{2,}"
    replaced_text = re.sub(pattern, dynamic_replacement, text)
    print(replaced_text)
    
run()
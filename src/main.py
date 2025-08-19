import sys
import os
import json
import argparse
import time

from extraction.identifier import CADContentIdentifier
from field_resgister import FIELDS_POOL
from conf.config import DATA_TMP_DIR

def extract_fields(project_dir: str, agent_model_name: str, output_dir: str,**kwargs):
    """
    抽取CAD项目中的字段
    Args:
        project_dir: CAD项目输入目录
        agent_model_name: 使用的模型名称
        output_dir: 输出保存目录（默认 DATA_TMP_DIR/general_data）
        **kwargs: 其他参数
    Returns:
    """
    startTime=time.time()
    identifier = CADContentIdentifier(
        project_dir=project_dir,
        agent_model_name=agent_model_name,
    )
    kwargs['output_dir']=output_dir
    result = identifier.extract_filds(FIELDS_POOL,**kwargs)
    endTime=time.time()
    caseTime=endTime-startTime
    caseTime=round(caseTime)
    result["caseTime"]=caseTime
    
    output_path = os.path.join(output_dir, f"{result['project_name']}.json")
    if kwargs.get("task_id"):
        output_path = os.path.join(output_dir, f"{kwargs['task_id']}.json")
    
    with open(output_path, 'w', encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=4)
    # 保存结果到本地目录 
    return result

def main():
    parser = argparse.ArgumentParser(description="CAD 内容抽取抽取脚本")
    parser.add_argument("--project_dir", required=True, help="CAD 项目输入目录")
    parser.add_argument("--agent_model_name", default="qwen3-8b", help="使用的模型名称")
    parser.add_argument("--output_dir", default=None, help="输出保存目录（默认 DATA_TMP_DIR/general_data）")

    args = parser.parse_args()
    startTime=time.time()
    project_dir = args.project_dir.rstrip('/')
    agent_model_name = args.agent_model_name
    output_dir = args.output_dir or os.path.join(DATA_TMP_DIR, 'general_data')
    os.makedirs(output_dir, exist_ok=True)

    identifier = CADContentIdentifier(
        project_dir=project_dir,
        agent_model_name=agent_model_name,
    )

    print("开始抽取字段...")
    result = identifier.extract_filds(FIELDS_POOL)
    base_info = result["general"]
    endTime=time.time()
    caseTime=endTime-startTime
    caseTime=round(caseTime)
    for idx, (key, tt) in enumerate(base_info.items()):
        value = tt['value']
        print(f"{idx + 1:02d}.【{key}】==>【{value}】")
    result["caseTime"]=caseTime
    output_path = os.path.join(output_dir, f"{result['project_name']}.json")
    try:
        with open(output_path, 'w', encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存结果文件时出错: {str(e)}")

    print(f"\n抽取完成，结果已保存至: {output_path}")
    
    print(f"\n当前耗时：{caseTime} 秒")

if __name__ == "__main__":
    main()

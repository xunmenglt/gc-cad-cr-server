import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
import os
from utils.openai import openai_chat_by_api
from typing import List,Literal
import re
import json
from jinja2 import Template
from collections import Counter
from utils.address import parse_regions,get_level_by_city



from extraction.fields import Key

KEYS_STORE={}

def regist_key(key:Key):
    key_name=key.key_name
    if key_name in KEYS_STORE:
        return False
    else:
        KEYS_STORE[key_name]=key
    return True

def get_value_by_key(key_name:str):
    if key_name not in KEYS_STORE:
        return None
    else:
        return KEYS_STORE[key_name]

regist_key(
    Key(
        key_name="项目名称",
        obtain_sources=["ZB"],
        alias=["标段名称","工程名称"]
    )
)

regist_key(
    Key(
        key_name="项目地点",
        obtain_sources=["ZB"],
        alias=["工程地点"],
        post_fun=lambda x:"".join(parse_regions(x)[:3])
    )
)

regist_key(
    Key(
        key_name="建设地点等级",
        obtain_sources=["dwg","pdf"],
        is_dependent=True,
        dependent_type="city",
        dependencies=["项目地点"]
    )
)


regist_key(Key(
    key_name="建设性质",
    obtain_sources=["ZB"],
    is_classify=True,
    classifications=["新建","改建","扩建"],
))

regist_key(Key(
        key_name="一级项目类别",
        obtain_sources=["ZB"],
        is_classify=True,
        classifications=["居住建筑","学校","办公建筑","体育建筑","卫生建筑","文化建筑","商业建筑","旅馆酒店建筑","交通建筑","居民服务建筑","工业建筑","市政工程","轨道交通工程"],
        classification_suffix="建筑",
        classification_map={
            "学校":"教育建筑"
        }
))

regist_key(
    Key(
        key_name="投资类型",
        obtain_sources=["ZB"],
        is_classify=True,
        classifications=["政府投资","企业投资","个人投资"],
        alias=["资金来源"]
    )
)

regist_key(
    Key(
        key_name="造价阶段",
        obtain_sources=["ZB"],
        is_classify=True,
        classifications=["估算","概算","招标","预算","结算","决算"],
        classification_suffix="阶段"
    )
)

regist_key(
    Key(
        key_name="执行清单",
        obtain_sources=["ZB"],
        is_classify=True,
        alias=["工程量的确定方法"],
        classifications=["GB50500-2008《建设工程工程量清单计价规范》","GB50500-2013《建设工程工程量清单计价规范》","GB/T50854-2024《房屋建筑与装饰工程工程量计算标准》"],
        default_value="GB50500-2008《建设工程工程量清单计价规范》"
    )
)


regist_key(
    Key(
        key_name="基础类型",
        obtain_sources=["ZB"],
        is_classify=True,
        classifications=["条形基础","独立基础","满堂基础","桩基础","桩基工程","桩基"],
        classification_map={
            "桩基工程":"桩基础",
            "桩基":"桩基础"
        }
    )
)


regist_key(
    Key(
        key_name="学位数",
        obtain_sources=["ZB"],
        alias=["学位个数","学位"],
        post_fun=lambda text:text
    )
)

regist_key(
    Key(
        key_name="信息价取定时间",
        obtain_sources=["ZB"],
        alias=["信息价","日    期"],
        post_fun=lambda text:text.replace(" ","")
    )
)

regist_key(
    Key(
        key_name="工程质量创优标准",
        obtain_sources=["ZB"],
        alias=["工程质量标准","工程质量"],
        post_fun=lambda text:next((clazz for clazz in ["合格", "不合格"] if clazz in text), text)
    )
)

regist_key(
    Key(
        key_name="开工日期",
        obtain_sources=["ZB"],
        alias=['计划开工日期'],
        post_fun=lambda text:text.replace(" ","").replace("计划开工日期：","")
    )
)

regist_key(
    Key(
        key_name="工期",
        obtain_sources=["ZB"],
        alias=['计划施工总工期'],
        post_fun=lambda text:''.join(re.findall(r'\d+', text))
    )
)




def caculate_completion_date(values):
    try:
        startTime,total_days=values
        from datetime import datetime,timedelta
        # 原始日期
        if "-" in startTime:
            format="%Y-%m-%d"
        elif "/" in startTime:
            format="%Y/%m/%d"
        elif "年" in startTime:
            format="%Y年%m月%d日"
        else:
            raise ValueError(f"日期异常，无法解析：{startTime}")
        date_obj = datetime.strptime(startTime,format)
        # 加30天
        new_date = date_obj + timedelta(days=int(total_days))
        return new_date.strftime(format)
    except:
        return None

regist_key(
    Key(
        key_name="竣工日期",
        is_dependent=True,
        dependent_type="caculate",
        dependencies=["开工日期","工期"],
        is_caculate=True,
        caculation_type="add",
        caculate_fun=caculate_completion_date
    )
)


regist_key(
    Key(
        key_name="建设单位",
        obtain_sources=["ZTJ"],
        post_fun=lambda text:text.replace(" ","").replace("建设单位：","")
    )
)

regist_key(
    Key(
        key_name="设计单位",
        obtain_sources=["ZTJ"],
        alias=["设计有限公司","科技发展有限公司"]
    )
)



field_requiring_classification_prompt_template=Template(
    """
    你是一位专业的分类专家，你可以根据给定的参考内容输出限定类别列表中的某一个类别，并以json格式给出。
限定类别列表：{{ classifications }}
<content>
参考内容，你需要对参考内容进行分类
</content>
<output>
{
    "classification":"限定类别列表中的某一个类别"
}
</output>
注意：<content></content>中包裹的是需要分类的参考内容。<output></output>包裹的是参考内容对应的分类。

<content>
{{content}}
</content>
    """.strip()
)

field_directed_prompt_template=Template(
    """
你是一位专业的信息抽取专家，你需要从给定的参考文本中抽取与关键字相关的内容信息，即信息抽取。其中<content></content>包裹的是参考内容。我将给你一个包含多个key的列表，但这些key都意思都大致相同，因此你抽取的时候只需要抽取出一个内容即可，无需为每一个key抽取内容，因为他们对应的值其实都是一样的。
key列表：{{keys}}
<content>
{{content}}
</content>
输出内容请用<output></output>标签包裹。
格式如下：
<output>
{
    "extract_content":"抽取的内容"
}
</output>
注意：涉及到日期到内容你只需要抽取日期或天数，无需抽取其他内容。建设单位以及设计单位应该是一个公司名称
如果学位存在多种，请相加其学位数，学位数只需返回总数即可，无需返回单位。
    """.strip()
)

def most_common_element(lst):
    count = Counter(lst)
    most_common = count.most_common(1)  # 获取出现最多的元素
    return most_common[0] if most_common else None




class CADContentIdentifier:
    def __init__(self,zb_file_path,zjt_file_path,agent_model_name:str="gpt-4o-mini"):
        assert zb_file_path
        assert zjt_file_path
        with open(zb_file_path,'r',encoding="utf-8") as fp:
            content=fp.read()
            self.zb_content=json.loads(content)
        with open(zjt_file_path,'r',encoding="utf-8") as fp:
            content=fp.read()
            self.zjt_content=json.loads(content)
        self.agent_model_name=agent_model_name
    
    def extract_surrounding_text(self,text,key,context_length=50)->List[str]:
        matches=re.finditer(re.escape(key), text)  # 查找所有匹配的 key
        results = [
            text[max(0, match.start() - context_length): min(len(text), match.end() + context_length)]
            for match in matches
        ]
        return results
    
    def get_contents_by_source(self,source=Literal["ZB","ZTJ"]):
        if source=='ZB':
            return self.zb_content
        else:
            return self.zjt_content
    
    
    def _extract_field_requiring_classification(self,key:Key):
        """
        抽取需要被分类的字段
        """
        value=""
        key_name=key.key_name
        classifications=key.classifications
        obtain_sources=key.obtain_sources
        alias=key.alias
        # 首先直接根据分类列表在原文本中进行匹配
        matched_classifications=[]
        for source in obtain_sources:
            contents=self.get_contents_by_source(source)
            for classification in classifications:
                for content in contents:
                    count=content.count(classification)
                    for _ in range(count):
                        matched_classifications.append(classification)
        if matched_classifications and len(matched_classifications)>0:
            value,count=most_common_element(matched_classifications)
        else:
            # 根据key_name和alias获取文本相关片段，让大模型进行判断
            matched_str_list=[]
            for source in obtain_sources:
                contents=self.get_contents_by_source(source)
                for content in contents:
                    matched_str_list=self.extract_surrounding_text(content,key_name)
                if not matched_str_list or len(matched_str_list)<=0:
                    for content in contents:
                        for alia in alias:
                            str_list=self.extract_surrounding_text(content,alia)
                            matched_str_list.extend(str_list)
            content='\n'.join(matched_str_list)[:300]
            ai_res=openai_chat_by_api(
                model_name=self.agent_model_name,
                messages=[{
                    "role":"user",
                    "content":field_requiring_classification_prompt_template.render(
                        {
                            "content":content,
                            "classifications":classifications
                        }
                    )
                }],
                inference_params={
                    "temperature":0.7,
                    "max_tokens":1024
                }
            )
            for classification in classifications:
                if classification in ai_res:
                    value=classification
                    break
        if not value:
            return key.default_value
        value=key.classification_map.get(value,value)
        value=value.strip(key.classification_prefix)
        value=value.strip(key.classification_suffix)
        return key.classification_prefix+value+key.classification_suffix
    
    def parse_ai_res_for_field_directed(self,ai_res:str):
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        data=json.loads(ai_res.strip())
        if data.get("extract_content"):
            return data["extract_content"]
        return None
    
    def _extract_field_directed(self,key:Key):
        value=""
        key_name=key.key_name
        alias=key.alias
        alias.insert(0,key_name)
        obtain_sources=key.obtain_sources
        matched_str_list=[]
        for source in obtain_sources:
            contents=self.get_contents_by_source(source)
            for content in contents:
                for alia in alias:
                    str_list=self.extract_surrounding_text(content,alia,25)
                    matched_str_list.extend(str_list)
        content="\n".join(matched_str_list)
        ai_res=openai_chat_by_api(
                model_name=self.agent_model_name,
                messages=[{
                    "role":"user",
                    "content":field_directed_prompt_template.render(
                        {
                            "content":content,
                            "keys":alias
                        }
                    )
                }],
                inference_params={
                    "temperature":0.7,
                    "max_tokens":1024
                }
        )
        value=self.parse_ai_res_for_field_directed(ai_res=ai_res)
        if value:
            return value
        else:
            return key.default_value
        
    
    def _extract_dependent_field_for_city(self,key:Key):
        dependent_key=key.dependencies[0]
        dependent_value=self.extract(get_value_by_key(dependent_key))
        regions=parse_regions(dependent_value)
        value=get_level_by_city(regions[1])
        return value
    
    def _extract_dependent_field_for_caculate(self,key:Key):
        dependencie_keys=key.dependencies
        dependent_values=[self.extract(get_value_by_key(dependencie_key)) for dependencie_key in dependencie_keys]
        if key.caculate_fun is not None:
            return key.caculate_fun(dependent_values)
        return None
    
    def _extract_dependent_field(self,key:Key):
        if not key.dependencies:
            return None
        value=None
        if key.dependent_type=="city":
            value=self._extract_dependent_field_for_city(key)
        elif key.dependent_type=="caculate":
            value=self._extract_dependent_field_for_caculate(key)
        else:
            pass
        return value


    def extract(self,key:Key):
        if key.value:
            return key.value
        # 判断key的类型
        value=None
        if key.is_caculate:
            if key.is_dependent:
                value=self._extract_dependent_field(key=key)
        else:
            # 非计算属性
            ## 判断key是否为具有分类的key
            if key.is_classify:
                value = self._extract_field_requiring_classification(key=key)
            else:
                if key.is_dependent:
                    value=self._extract_dependent_field(key=key)
                else:
                    value = self._extract_field_directed(key=key)
        key.value=value
        return key.post_process()
        

ztj_file="/opt/data/private/liuteng/code/gc-cad-cr/data/tmp/e/a.json"
zb_file="/opt/data/private/liuteng/code/gc-cad-cr/data/tmp/e/b.json"

identifier =CADContentIdentifier(
    zb_file_path=zb_file,
    zjt_file_path=ztj_file,
    agent_model_name="gpt-4o-mini"
)
print("\n========================================")
for idx,key in enumerate(KEYS_STORE):
    value=identifier.extract(KEYS_STORE[key])
    print(f"{idx+1:02d}.【{key}】==>【{value}】")
print("========================================\n")








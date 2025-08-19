import hashlib
import os
import sys
import re
import base64
from typing import List
from pathlib import Path
from typing import Optional
from markitdown import MarkItDown, StreamInfo, DocumentConverterResult
from utils.openai import openai_chat_by_api,InferenceParams
from conf.config import VL_MODEL_NAME,DATA_TMP_DIR
from common.prompts import markdown_transfrom_prompt,text_transfrom_prompt


def calculate_file_metadata_md5(file_path: str) -> str:
    """计算文件的 MD5，基于路径、名称、大小、创建时间和更新时间"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 获取文件属性
    file_name = path.name
    file_size = path.stat().st_size
    file_ctime = path.stat().st_ctime  # 创建时间（时间戳）
    file_mtime = path.stat().st_mtime  # 修改时间（时间戳）

    # 去除DATA_TMP_DIR
    file_path=file_path.replace(DATA_TMP_DIR,"")
    # 组合元数据为字符串
    metadata_string = f"{file_path}|{file_name}|{file_size}"

    # 计算 MD5
    md5_hash = hashlib.md5(metadata_string.encode()).hexdigest()
    return md5_hash


def get_all_files_in_dir(directory:str,allowed_extensions:List[str]=[]):
    """遍历目录中的文件，并根据后缀名过滤"""
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if allowed_extensions and len(allowed_extensions)>0:
                # 获取文件后缀（忽略大小写）
                ext = os.path.splitext(file)[-1].lower()
                if ext not in allowed_extensions:
                    continue
            file_list.append(os.path.join(root, file))
    return file_list


def file_to_markdown(
    file_path: str,
    output_file: Optional[str] = None,
    extension_hint: Optional[str] = None,
    mime_type_hint: Optional[str] = None,
    charset_hint: Optional[str] = None,
    use_plugins: bool = False,
    keep_data_uris: bool = False,
    docintel_endpoint: Optional[str] = None
) -> str:
    """
    将文件转换为Markdown内容
    
    参数:
        file_path: 输入文件路径
        output_file: 输出文件路径(可选)，如果不提供则返回内容
        extension_hint: 文件扩展名提示(如".pdf")
        mime_type_hint: MIME类型提示(如"application/pdf")
        charset_hint: 字符集提示(如"utf-8")
        use_plugins: 是否使用第三方插件
        keep_data_uris: 是否保留数据URI(如base64图片)
        docintel_endpoint: 使用Document Intelligence时的端点URL
    
    返回:
        转换后的Markdown内容字符串(当output_file为None时)
    """
    # 创建流信息对象(如果有提示信息)
    stream_info = None
    if any([extension_hint, mime_type_hint, charset_hint]):
        stream_info = StreamInfo(
            extension=extension_hint,
            mimetype=mime_type_hint,
            charset=charset_hint
        )
    
    # 初始化MarkItDown转换器
    markitdown = MarkItDown(
        enable_plugins=use_plugins,
        docintel_endpoint=docintel_endpoint if docintel_endpoint else None
    )
    
    # 执行转换
    result = markitdown.convert(
        file_path,
        stream_info=stream_info,
        keep_data_uris=keep_data_uris
    )
    
    # 处理输出
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.markdown)
        return f"Successfully saved to {output_file}"
    else:
        return result.markdown



def split_paragraphs(text):
    # 匹配 **标题**\n（可能后面有内容或另一个标题）
    regex = r'(\*\*[^\n]*?\*\*\n)(.*?)(?=\n\*\*|\Z)'
    matches = re.findall(regex, text, re.DOTALL)
    paragraphs = []
    for title, content in matches:
        paragraphs.append({
            "title": title.strip(),
            "content": content.strip()
        })
    
    return paragraphs


def image_to_base64(image_path):
    """将图片转换为base64字符串"""
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return base64_image

def image_to_markdown(image_path):
    if not os.path.exists(image_path):
        return ""
    base64_image=image_to_base64(image_path)
    try:
        res=openai_chat_by_api(
            model_name=VL_MODEL_NAME,
            messages=[
                {
                    "role":"system",
                    "content":[{"type":"text","text": "你是表格识别助手"}],
                },
                {
                    "role":"user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}, 
                        },
                        {"type": "text", "text": markdown_transfrom_prompt},
                    ],
                }
            ],
            inference_params=InferenceParams(
                    temperature=0,
                    max_tokens=4096
            )
        )
        if res:
            res= res.replace("```markdown","")
            res= res.replace("```","")
        else:
            res=""
        return res
    except Exception as e:
        return ""
    
def image_to_text(image_path):
    if not os.path.exists(image_path):
        return ""
    base64_image=image_to_base64(image_path)
    try:
        res=openai_chat_by_api(
            model_name=VL_MODEL_NAME,
            messages=[
                {
                    "role":"system",
                    "content":[{"type":"text","text": "你是文本提取助手"}],
                },
                {
                    "role":"user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}, 
                        },
                        {"type": "text", "text": text_transfrom_prompt},
                    ],
                }
            ],
            inference_params=InferenceParams(
                    temperature=0,
                    max_tokens=4096
            )
        )
        if not res:
            res=""
        return res
    except Exception as e:
        return ""
    
def image_chat(image_path, prompt):
    if not os.path.exists(image_path):
        return ""
    base64_image=image_to_base64(image_path)
    res = openai_chat_by_api(
        model_name=VL_MODEL_NAME,
        messages=[
            {
                "role":"user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}, 
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
    )
    return res
    

# 使用示例
if __name__ == "__main__":
    # 基本用法
    markdown_content = file_to_markdown("/opt/data/private/liuteng/code/gc-cad-cr/data/input/合水口人才房学校/招标文件/招标文件.doc")
    print(markdown_content)  # 打印前200字符
    # 正则表达式子，以**xxx**开头的行，进行分割，但是要保留**xxx**
    
    

import gradio as gr
import json
from typing import Tuple, Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError,field_validator

# ------------------------- 数据结构定义 -------------------------
class IERestultItem(BaseModel):
    id: str = Field("", description="唯一标识符")
    instruction: str = Field("", description="指令")
    start: List[int] = Field(default_factory=list, description="开始位置")
    end: List[int] = Field(default_factory=list, description="结束位置")
    target: str = Field("", description="目标文本")

    def to_dict(self) -> dict:
        return self.model_dump()


class ContentItem(BaseModel):
    content: str = Field(default="", description="参考内容")
    ie_info: Optional[IERestultItem] = Field(default=None, description="IE模型对参考内容的抽取内容")

    def to_dict(self):
        return self.model_dump()

    @classmethod
    def from_dict(cls, item):
        return cls(**item)


class OcrItem(BaseModel):
    image_path: str = Field(default="", description="图片存储路径")
    content: Optional[str] = Field(default="", description="OCR识别图片的内容")

    def to_dict(self):
        return self.model_dump()

    @classmethod
    def from_dict(cls, item):
        return cls(**item)


class ReferenceData(BaseModel):
    texts: List[ContentItem] = Field(default_factory=list, description="参考文本对象")
    ocrs: List[OcrItem] = Field(default_factory=list, description="参考OCR对象")

    def to_dict(self):
        return self.model_dump()


class General(BaseModel):
    value: str = Field("", description="字段值")
    ref_data: ReferenceData = Field(default_factory=ReferenceData, description="参考数据")

    @field_validator("value", mode="before")
    @classmethod
    def cast_value_to_str(cls, v):
        return str(v)


class Project(BaseModel):
    project_name: str = Field("", description="项目名称")
    general: Dict[str, General] = Field(default_factory=dict, description="项目通用字段")
    business_type: Dict[str, str] = Field(default_factory=dict, description="项目业态字段")


# ------------------------- Gradio 逻辑 -------------------------
def parse_project_json(file) -> Tuple[str, List[Tuple[str, str]], Project]:
    try:
        with open(file, 'r', encoding="utf-8") as f:
            raw = json.load(f)
        project = Project(**raw)
        field_dict = {k: {'value': v.value} for k, v in project.general.items()}
        field_rows=[]
        index=0
        for k, v in field_dict.items():
            index+=1
            field_rows.append([index,k,v['value']])
        return project.project_name, field_rows, project
    except ValidationError as e:
        raise gr.Error(f"JSON 格式错误: {e}")


def get_reference_info(project: Project, field: str):
    try:
        general_field = project.general.get(field)
        if not general_field:
            return gr.update(visible=False, value=[])

        ocrs = general_field.ref_data.ocrs
        image_paths = [ocr.image_path for ocr in ocrs if ocr.image_path]
        texts = general_field.ref_data.texts
        text_and_ie_info=[(text.content,text.ie_info) for text in texts]
        return gr.update(visible=True, value=image_paths)  # Gallery只接受一个List[str]
    except Exception as e:
        return gr.update(visible=True, value=[f"❌ 错误: {e}"])




def get_ie_info(project: Project, field: str, evt: gr.SelectData):
    try:
        idx = evt.index
        texts = project.general[field].ref_data.texts
        if idx < len(texts):
            ie_info = texts[idx].ie_info
            return json.dumps(ie_info.to_dict(), indent=2, ensure_ascii=False) if ie_info else "无 IE 信息"
        else:
            return ""
    except Exception as e:
        return f"❌ 获取IE信息失败: {e}"

# 新增回调函数：展示对应 IE 信息
def show_selected_ie_info(project: Project, field: str, evt: gr.SelectData):
    try:
        idx = evt.index
        texts = project.general[field].ref_data.texts
        if idx < len(texts):
            ie_info = texts[idx].ie_info
            return (
                json.dumps(ie_info.to_dict(), indent=2, ensure_ascii=False) if ie_info else "无 IE 信息",
                True if ie_info else False
            )
        else:
            return "", False
    except Exception as e:
        return f"❌ 获取IE信息失败: {e}", True

# 新增回调函数：更新参考文本列表
def update_text_and_ie(project: Project, field: str):
    try:
        general_field = project.general.get(field)
        if not general_field:
            return gr.update(visible=False, value=[]), gr.update(visible=False, value="")

        texts = general_field.ref_data.texts
        text_rows = [[text.content] for text in texts]
        return gr.update(visible=True, value=text_rows), gr.update(visible=False, value="")
    except Exception as e:
        return gr.update(visible=True, value=[[f"❌ 错误: {e}"]]), gr.update(visible=False, value="")


# ------------------------- Gradio 界面 -------------------------
with gr.Blocks(title="Project Viewer", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📘 广诚CAD内容识别系统")

    with gr.Row():
        with gr.Column(scale=1):
            project_name_box = gr.Textbox(label="项目名称", interactive=False)
            file_upload = gr.File(label="上传 项目 JSON 文件", file_types=['.json'])
            field_list = gr.Radio(label="字段列表", choices=[], interactive=True)

        with gr.Column(scale=4):
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown("### 字段内容展示")
                    field_table = gr.Dataframe(headers=["编号","字段名", "字段值"], label="字段值列表", interactive=False)
                with gr.Column(scale=1):
                    gr.Markdown("### 📑 参考内容展示")
                    ocr_gallery = gr.Gallery(
                        label="OCR 识别结果（点击放大查看）",
                        show_label=True,
                        columns=1,
                        elem_id="ocr-gallery"
                    )

            with gr.Row():
                text_list = gr.Dataframe(
                        headers=["参考文本"], 
                        interactive=True, 
                        row_count=(1, "dynamic"), 
                        col_count=(1, "fixed"), 
                        label="参考文本列表"
                )
                ie_info_json = gr.Code(label="抽取信息（点击文本查看）", language="json", visible=False)
            


    project_state = gr.State()  # 存储 Project 对象

    file_upload.change(
        fn=parse_project_json,
        inputs=[file_upload],
        outputs=[project_name_box, field_table, project_state]
    ).then(
        lambda project: gr.update(choices=list(project.general.keys())) if project else gr.update(choices=[]),
        inputs=[project_state],
        outputs=[field_list]
    )

    field_list.change(
        fn=get_reference_info,
        inputs=[project_state, field_list],
        outputs=[ocr_gallery]
    ).then(
        fn=update_text_and_ie,
        inputs=[project_state, field_list],
        outputs=[text_list, ie_info_json]
    )
    # 在点击某条参考文本时，展示对应的抽取信息
    text_list.select(
        fn=show_selected_ie_info,
        inputs=[project_state, field_list],
        outputs=[ie_info_json, ie_info_json]
    )


if __name__ == '__main__':
    demo.launch()
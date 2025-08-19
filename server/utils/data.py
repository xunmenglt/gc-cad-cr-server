import os
import tqdm
import json
from datasets import Dataset,DatasetDict,load_dataset
import torch
import uuid

def load_custom_data_file(data_path):
    data={}
    sep="|&&|"
    with open(data_path,'r',encoding="utf-8") as fp:
        contents=fp.readlines()
        headers=[item.strip() for item in contents[0].split(sep)]
        lines=[content.split(sep) for content in contents]
        for line in tqdm.tqdm(lines[1:],desc="自定义文件类型处理中"):
            for idx,item in enumerate(line):
                label=headers[idx]
                if not data.get(label):
                    data[label]=[]
                data[label].append(item.strip())
    return Dataset.from_dict(data)
        


def pre_load_dataset(train_dataset_path,test_dataset_path)->DatasetDict:
    data={}
    if not os.path.exists(train_dataset_path):
        raise FileExistsError("训练文件不存在")
    train_data_dir=os.path.dirname(train_dataset_path)
    file_name=os.path.basename(train_dataset_path)
    file_extension = os.path.splitext(train_dataset_path)[1]
    if "txt" in file_extension:
        train_data=load_custom_data_file(train_dataset_path)
    else:
        train_data=load_dataset(path=train_data_dir,data_files=file_name)["train"]
    data["train"]=train_data
    if os.path.exists(test_dataset_path):
        test_data_dir=os.path.dirname(test_dataset_path)
        file_name=os.path.basename(test_dataset_path)
        file_extension = os.path.splitext(test_dataset_path)[1]
        if "txt" in file_extension:
            test_data=load_custom_data_file(test_dataset_path)
        else:
            test_data=load_dataset(path=test_data_dir,data_files=file_name)["train"]
        data["test"]=test_data
    
    return DatasetDict(data)


def json_to_custom_data(json_path,custom_data_path):
    sep="|&&|"
    if not os.path.exists(json_path):
        raise FileExistsError("文件不存在")
    with open(json_path,'r',encoding="utf-8") as jp:
        json_data=json.loads(jp.read())
        headers=json_data[0].keys()
        contents=[]
        for line in tqdm.tqdm(json_data,desc="转换自定义文件格式中"):
            items=[]
            for key in headers:
                items.append(str(line.get(key,'')).strip())
            contents.append(items)
    with open(custom_data_path,'w',encoding="utf-8") as cp:
        lines=[sep.join(headers)+"\n"]
        lines=lines+[sep.join(content)+"\n" for content in contents]
        cp.writelines(lines)


def tsv_to_json(tsv_path,json_path,nums):
    with open(tsv_path,'r',encoding="utf-8") as tp:
        contents=tp.readlines()
        json_data=[]
        for content in tqdm.tqdm(contents):
            items=content.split("\t")
            json_item={
                "id":items[0].strip(),
                "instruction":items[1][2:-2],
                "start":eval(items[2]),
                "end":eval(items[3]),
                "target":items[4].strip()
            }
            json_data.append(json_item)
    with open(json_path,'w',encoding="utf-8") as jp:
        if nums>0:
            json_data=json_data[:nums]
        jp.write(json.dumps(json_data,indent=4,ensure_ascii=False))
    print("数据总量：",f"{len(json_data)}")
    
def formatting_prompts_func(example,prompt_type):
    if prompt_type == "qwen2":
        text = f"<|im_start|>{example['instruction'].strip()}<|im_end|>"
    else:
        raise NotImplementedError(
            f"Prompt type {prompt_type} not implemented."
        )
    id = example["id"]
    instruction = text
    target = example["target"]

    start = eval(example["start"])    
    if start == None:
        start = []
    end = eval(example["end"])
    if end == None:
        end = []
    new_sart=[]
    new_end=[]
    for s,e in zip(start,end):
        new_sart.append(s+len('<|im_start|>'))
        new_end.append(e+len('<|im_start|>'))
    start=new_sart
    end=new_end
    
    return {"id":id,"instruction":instruction,"start":start,"end":end,"target":target}

def tokenize(element,tokenizer,max_seq_length=512,dataset_text_field="instruction"):
    max_seq_length=max_seq_length
    example = tokenizer(
        element[dataset_text_field],
        padding="max_length",
        truncation=True,
        max_length=max_seq_length,
        return_offsets_mapping=True
    )

    labels = torch.zeros(max_seq_length, max_seq_length)  # 阅读理解任务entity种类为1 [bz, 1, max_len, max_len]
    starts, ends = element['start'], element['end']
    offset = example['offset_mapping'] # 表示tokenizer生成的token对应原始文本中字符级别的位置区间
    position_map = {}
    for i, (m, n) in enumerate(offset):
        if i != 0 and m == 0 and n == 0:
            continue
        for k in range(m, n + 1):
            position_map[k] = i # 字符级别的第k个字符属于分词i
    for start, end in zip(starts, ends):
        end -= 1
        # MRC 没有答案时则把label指向CLS
        if start == 0:
            assert end == -1
            labels[0, 0] = 1
        else:
            if start in position_map and end in position_map:
                # 指定下列元素为1，说明表示第feature_id个样本的预测区间
                labels[position_map[start], position_map[end]] = 1
    
    example["id"] = element["id"]
    example["instruction"] = element["instruction"]
    example["start"] = element["start"]
    example["end"] = element["end"]
    example["target"] = element["target"]
    example["input_ids"]=example["input_ids"]
    example["attention_mask"]=example["attention_mask"]
    example["label_ids"]=labels
    return example

def format_predictions(predictions,topk_predictions,instruction):
        for key in predictions:
            start=[]
            end=[]
            target=[]
            for prediction in topk_predictions[key]:
                for s,e in prediction["pos"]:
                    start.append(s)
                    end.append(e)
                target.append(prediction["answer"])
            
        item=dict(
            id=str(uuid.uuid4()),
            instruction=instruction,
            start=start,
            end=end,
            target="|".join(target)
        )
        return item

if __name__=="__main__":
    # res=pre_load_dataset(
    #     "/opt/data/private/liuteng/code/dev/amies-train-server/data/ner_json/test.json",
    #     "/opt/data/private/liuteng/code/dev/amies-train-server/data/ner_json/test.txt"
    # )
    # print(res)
    # tsv_path="/opt/data/private/liuteng/code/dev/amies-train-server/data/ner/dev.tsv"
    # json_path="/opt/data/private/liuteng/code/dev/amies-train-server/data/ner_json/dev.txt"
    # tsv_to_json(tsv_path,json_path,10000)
    json_file="/opt/data/private/liuteng/code/dev/amies-train-server/data/ner_json/dev.json"
    data_file="/opt/data/private/liuteng/code/dev/amies-train-server/data/ner_json/dev.txt"
    json_to_custom_data(json_file,data_file)
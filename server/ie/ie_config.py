import os
import json
from dataclasses import dataclass, field,asdict
from typing import Any, Optional,Union,Literal
from transformers import TrainingArguments

# if you need use wandb，then please to set the wandb‘s api key
os.environ["WANDB_API_KEY"] = "69ae6e2753f3a7bce46460080ec48b6f2a756462"
os.environ["WANDB_WATCH"]="false"

@dataclass
class IETainerConfig(TrainingArguments):
    per_device_train_batch_size: Optional[int] = field(default=1)
    
    per_device_eval_batch_size: Optional[int] = field(default=1)
    
    gradient_accumulation_steps: Optional[int] = field(default=4)
    
    learning_rate: Optional[float] = field(default=2.0e-5)
    
    weight_decay: Optional[float] = field(default=0.0)
    
    save_strategy: Union[str] = field(
        default="steps",
        metadata={"help": "The checkpoint save strategy to use."},
    )
    
    save_steps: float = field(
        default=500,
        metadata={
            "help": (
                "Save checkpoint every X updates steps. Should be an integer or a float in range `[0,1)`. "
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    
    eval_strategy: Optional[str] = field(
        default="steps",
        metadata={"help": "The evaluation strategy to use."},
    )
    
    eval_steps: Optional[float] = field(
        default=0.1,
        metadata={
            "help": (
                "Run an evaluation every X steps. Should be an integer or a float in range `[0,1)`. "
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    
    logging_strategy: Optional[str] = field(
        default="steps",
        metadata={"help": "The logging strategy to use."},
    )
    
    logging_steps: float = field(
        default=0.01,
        metadata={
            "help": (
                "Log every X updates steps. Should be an integer or a float in range `[0,1)`. "
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    
    model_path: Optional[str] = field(
        default="Qwen/Qwen2.5-1.5B",
        metadata={
            "help": "The model that you want to train from the Hugging Face hub. E.g. gpt2, gpt2-xl, bert, etc."
        },
    )
    
    dataset_path: Optional[str] = field(
        default=None,
        metadata={
            "help": "The parameter should be passed to the directory address of the data set, and the data set format should be json format.",
        },
    )
    
    prompt_type: Optional[str] = field(
        default="qwen2",
    )
    
    bf16: Optional[bool] = field(
        default=True,
        metadata={
            "help": "This essentially cuts the training time in half if you want to sacrifice a little precision and have a supported GPU."
        },
    )
    
    tf32: Optional[bool] = field(
        default=None,
    )
    num_train_epochs: Optional[float] = field(
        default=1,
        metadata={"help": "The number of training epochs for the reward model."},
    )
    gradient_checkpointing: Optional[bool] = field(
        default=False,
        metadata={"help": "Enables gradient checkpointing."},
    )
    optim: Optional[str] = field(
        default="paged_adamw_32bit",
        metadata={"help": "The optimizer to use."},
    )
    
    lr_scheduler_type: Optional[str] = field(
        default="cosine",
        metadata={"help": "The lr scheduler"},
    )

    max_training_samples: Optional[int] = field(
        default=-1, metadata={"help": "the maximum sample size"}
    )
    
    max_length: Optional[int] = field(
        default=512
    )
    
    dataset_num_proc: Optional[int] = field(
        default=10,
        metadata={"help":"dataset num proc"}
    )
    
    dataset_kwargs: Optional[dict] =field(
        default=None,
        metadata={"help":"dataset kwargs"}
    )
    
    output_dir: Optional[str] = field(
        default="./models/global-prointer-qwen2-0.5B"
    )
    
    dataset_text_field: Optional[str] = field(
        default="instruction",
        metadata={"help":"Field requiring tokenization"}
    )
    use_wandb: Optional[bool] = field(
        default=True,
        metadata={"help":"whether to use wandb"}
    )
    
    wandb_project: Optional[str] = field(
        default="ner_train",
        metadata={"help":"wandb project name"}
    )
    
    wandb_log_model: Optional[bool] = field(
        default=False,
        metadata={"help":"save your trained model checkpoint to wandb"}
    )
    
    wandb_run_name: Optional[str] = field(
        default="qwen2-0.5b-ner-tainer",
        metadata={"help":"runing name"}
    )


@dataclass
class IETainerServerConfig:
    # 训练ID
    train_id:Optional[str] = field(default=None)
    # 日志保存路径
    log_path:Optional[str] = field(default=None)
    # 训练数据路径
    train_dataset_path:Optional[str]=field(default=None)
    # 测试集路径
    test_dataset_path:Optional[str]=field(default=None)
    # 钩子url
    hook_url:Optional[str]=field(default=None)
    
    
@dataclass
class IEEvalServerConfig:
    # 训练ID
    eval_id:Optional[str] = field(default=None)
    # 模型名称
    model_name_or_path:str=field(default=""),
    # 评估数据集路径
    eval_dataset_path:str=field(default="")
    # 最大序列长度
    max_seq_length:int=field(default=512)
    # 数据批大小
    batch_szie:int=field(default=4)
    # 评估提示词模版
    prompt_type:str=field(default="qwen2")    
    # gpu编号
    gpu_number:int=field(default=0)
    # 钩子url
    hook_url:Optional[str]=field(default=None)
    
    
@dataclass
class IETainerEvent:
    type:Literal["no_start",
                 "starting",
                 "init_success",
                 "train_start",
                 "update_train_progress",
                 "train_end",
                 "stoped",
                 "stoped_unusual",
                 "train_error",
                 "save_log",
                 "save_model"
                 ]=field(default="no_start")
    data:Optional[object]=field(default=dict)
    msg:Optional[str]=field(default="")
    
    def to_json(self):
        return asdict(self)
    
    def to_json_str(self):
        return json.dumps(self.to_json(),ensure_ascii=False)
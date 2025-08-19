
import os
from typing import Callable, Optional, Union,List,Any,Dict,Mapping
import datasets 
import dataclasses
from dataclasses import dataclass
import torch
import torch.nn as nn
from datasets import Dataset
from transformers.trainer_callback import TrainerCallback
from transformers.trainer_utils import EvalPrediction
from accelerate.state import PartialState
import warnings
from transformers import (
    AutoTokenizer,
    BaseImageProcessor,
    DataCollator,
    FeatureExtractionMixin,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    ProcessorMixin,
    Trainer,
    is_wandb_available,
)
from transformers.utils.deprecation import deprecate_kwarg
from transformers.data.data_collator import DataCollatorMixin
from trl.trainer.utils import (
    ConstantLengthDataset,
    generate_model_card,
    get_comet_experiment_url,
)
from ie.global_pointer import QwenForEffiGlobalPointer,multilabel_categorical_crossentropy
from ie.ie_config import IETainerConfig


if is_wandb_available():
    import wandb



class IEDataCollator(DataCollatorMixin):
    def __init__(self,tokenizer,max_seq_length,return_tensors="pt",device="cuda:0",dataset_text_field="instruction"):
        self.return_tensors=return_tensors
        self.device=device
        self.tokenizer=tokenizer
        self.max_seq_length=max_seq_length
        self.dataset_text_field=dataset_text_field

    def tokenize(self,element):
        max_seq_length=self.max_seq_length
        example = self.tokenizer(
            element[self.dataset_text_field],
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
        
        # example["id"] = element["id"]
        # example["instruction"] = element["instruction"]
        # example["start"] = element["start"]
        # example["end"] = element["end"]
        # example["target"] = element["target"]
        # example["input_ids"]=example["input_ids"]
        # example["attention_mask"]=example["attention_mask"]
        # example["label_ids"]=labels.tolist()
        item={
                "input_ids":example["input_ids"],
                "attention_mask":example["attention_mask"],
                "label_ids":labels
        }
        if example.get("token_type_ids"):
            item["token_type_ids"]=example.get("token_type_ids")
        return item


    def torch_call(self, examples: List[Union[List[int], Any, Dict[str, Any]]]) -> Dict[str, Any]:
        # Handle dict or lists with proper padding and conversion to tensor.
        examples=[self.tokenize(element) for element in examples]
        items={}
        for key in ["input_ids","attention_mask","label_ids","token_type_ids"]:
            arr=[]
            for e in examples:
                arr.append(e[key])
            if key=="label_ids":
                items[key]=torch.stack(arr)
            else:
                items[key]=torch.tensor(arr)
        return items



class IETrainer(Trainer):
    _tag_names = ["trl", "ie"]

    @deprecate_kwarg(
        "tokenizer", "0.16.0", "processing_class", warn_if_greater_or_equal_version=True, raise_if_both_names=True
    )
    def __init__(
        self,
        model: Optional[Union[PreTrainedModel, nn.Module, str]] = None,
        args: Optional[IETainerConfig] = None,
        data_collator: Optional[DataCollator] = None,  # type: ignore
        train_dataset: Optional[Dataset] = None,
        eval_dataset: Optional[Union[Dataset, dict[str, Dataset]]] = None,
        processing_class: Optional[
            Union[PreTrainedTokenizerBase, BaseImageProcessor, FeatureExtractionMixin, ProcessorMixin]
        ] = None,
        model_init: Optional[Callable[[], PreTrainedModel]] = None,
        compute_metrics: Optional[Callable[[EvalPrediction], dict]] = None,
        callbacks: Optional[list[TrainerCallback]] = None,
        optimizers: tuple[torch.optim.Optimizer, torch.optim.lr_scheduler.LambdaLR] = (None, None),
        preprocess_logits_for_metrics: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None,
        formatting_func: Optional[Callable] = None,
    ):
        # todo set wandb config
        if is_wandb_available():
            if args.use_wandb:
                wandb.init(project=args.wandb_project,name=args.wandb_run_name)
        if args is None:
            args = NERTainerConfig(output_dir="tmp_trainer")
        elif args is not None and args.__class__.__name__ == "TrainingArguments":
            args_as_dict = args.to_dict()
            # Manually copy token values as TrainingArguments.to_dict() redacts them
            args_as_dict.update({k: getattr(args, k) for k in args_as_dict.keys() if k.endswith("_token")})
            args = NERTainerConfig(**args_as_dict)

        if getattr(args, "model_init_kwargs", None) is None:
            model_init_kwargs = {}
        elif not isinstance(model, str):
            raise ValueError("You passed model_init_kwargs to the SFTConfig, but your model is already instantiated.")
        else:
            model_init_kwargs = args.model_init_kwargs
            torch_dtype = model_init_kwargs.get("torch_dtype")
            if torch_dtype is not None:
                # Convert to `torch.dtype` if an str is passed
                if isinstance(torch_dtype, str) and torch_dtype != "auto":
                    torch_dtype = getattr(torch, torch_dtype)
                if torch_dtype != "auto" and not isinstance(torch_dtype, torch.dtype):
                    raise ValueError(
                        f"Invalid `torch_dtype` passed to the SFTConfig. Expected a string with either `torch.dtype` or 'auto', but got {torch_dtype}."
                    )
                model_init_kwargs["torch_dtype"] = torch_dtype

        if isinstance(model, str):
            model = QwenForEffiGlobalPointer.from_pretrained(model, **model_init_kwargs)

        if processing_class is None:
            processing_class = AutoTokenizer.from_pretrained(model.config._name_or_path)
            if getattr(processing_class, "pad_token", None) is None:
                processing_class.pad_token = processing_class.eos_token

        if not hasattr(args,"max_seq_length"):
            # to overcome some issues with broken tokenizers
            setattr(args,"max_seq_length",min(processing_class.model_max_length, args.max_length))

        self.dataset_num_proc = args.dataset_num_proc

        if args.dataset_kwargs is None:
            args.dataset_kwargs = {}

        if formatting_func is not None:
            args.dataset_kwargs["add_special_tokens"] = False

        if data_collator is None:
            data_collator = IEDataCollator(processing_class, args.max_length,return_tensors="pt",device=model.device)

        # Pre-process the datasets only once per node. The remaining processes will use the cache.
        with PartialState().local_main_process_first():
            if train_dataset is not None:
                train_dataset = self._prepare_dataset(
                    train_dataset,
                    processing_class,
                    args.dataset_text_field,
                    args.max_seq_length,
                    formatting_func,
                    remove_unused_columns=args.remove_unused_columns if args is not None else True,
                    **args.dataset_kwargs,
                )
            if eval_dataset is not None:
                _multiple = isinstance(eval_dataset, dict)
                _eval_datasets = eval_dataset if _multiple else {"singleton": eval_dataset}

                for _eval_dataset_name, _eval_dataset in _eval_datasets.items():
                    _eval_datasets[_eval_dataset_name] = self._prepare_dataset(
                        _eval_dataset,
                        processing_class,
                        args.dataset_text_field,
                        args.max_seq_length,
                        formatting_func,
                        remove_unused_columns=args.remove_unused_columns if args is not None else True,
                        **args.dataset_kwargs,
                    )
                if not _multiple:
                    eval_dataset = _eval_datasets["singleton"]

        if processing_class.padding_side is not None and processing_class.padding_side != "right":
            warnings.warn(
                "You passed a processing_class with `padding_side` not equal to `right` to the SFTTrainer. This might "
                "lead to some unexpected behaviour due to overflow issues when training a model in half-precision. "
                "You might consider adding `processing_class.padding_side = 'right'` to your code.",
                UserWarning,
            )
        

        super().__init__(
            model=model,
            args=args,
            data_collator=data_collator,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            processing_class=processing_class,
            model_init=model_init,
            compute_metrics=compute_metrics,
            callbacks=callbacks,
            optimizers=optimizers,
            preprocess_logits_for_metrics=preprocess_logits_for_metrics,
        )

        # Add tags for models that have been loaded with the correct transformers version
        if hasattr(self.model, "add_model_tags"):
            self.model.add_model_tags(self._tag_names)

    def _prepare_dataset(
        self,
        dataset,
        processing_class,
        dataset_text_field: str,
        max_seq_length,
        formatting_func: Optional[Callable],
        remove_unused_columns=True,
        append_concat_token=True,
        add_special_tokens=True,
        skip_prepare_dataset=False,
    ):
        if dataset is None:
            raise ValueError("The dataset should not be None")

        if skip_prepare_dataset:
            return dataset

        if isinstance(
            dataset, (torch.utils.data.IterableDataset, torch.utils.data.Dataset, ConstantLengthDataset)
        ) and not isinstance(dataset, datasets.IterableDataset):
            return dataset
        return dataset
        # return self._prepare_dataloader(
        #     processing_class,
        #     dataset,
        #     dataset_text_field,
        #     max_seq_length,
        #     formatting_func,
        #     add_special_tokens,
        #     remove_unused_columns,
        # )

    def _prepare_dataloader(
        self,
        processing_class,
        dataset,
        dataset_text_field: str,
        max_seq_length,
        formatting_func: Optional[Callable] = None,
        add_special_tokens=True,
        remove_unused_columns=True,
    ):
        def tokenize(element):
            example = processing_class(
                element[dataset_text_field] if formatting_func is None else formatting_func(element),
                padding="max_length",
                truncation=True,
                max_length=max_seq_length,
                return_offsets_mapping=True
            )
            if formatting_func is not None and not isinstance(formatting_func(element), list):
                raise ValueError(
                    "The `formatting_func` should return a list of processed strings since it can lead to silent bugs."
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

        signature_columns = ["input_ids", "label_ids", "attention_mask"]

        if dataset.column_names is not None:  # None for IterableDataset
            extra_columns = list(set(dataset.column_names) - set(signature_columns))
        else:
            extra_columns = []

        if not remove_unused_columns and len(extra_columns) > 0:
            warnings.warn(
                "You passed `remove_unused_columns=False` on a non-packed dataset. This might create some issues with "
                "the default collator and yield to errors. If you want to inspect dataset other columns (in this "
                f"case {extra_columns}), you can subclass `DataCollatorForLanguageModeling` in case you used the "
                "default collator and create your own data collator in order to inspect the unused dataset columns.",
                UserWarning,
            )

        map_kwargs = {
            "batched": False,
            "remove_columns": dataset.column_names if remove_unused_columns else None,
        }
        if isinstance(dataset, datasets.Dataset):
            map_kwargs["num_proc"] = self.dataset_num_proc  # this arg is not available for IterableDataset
        tokenized_dataset = dataset.map(tokenize, **map_kwargs)

        return tokenized_dataset

    def create_model_card(
        self,
        model_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        tags: Union[str, list[str], None] = None,
    ):
        """
        Creates a draft of a model card using the information available to the `Trainer`.

        Args:
            model_name (`str`, *optional*, defaults to `None`):
                The name of the model.
            dataset_name (`str`, *optional*, defaults to `None`):
                The name of the dataset used for training.
            tags (`str`, `list[str]` or `None`, *optional*, defaults to `None`):
                Tags to be associated with the model card.
        """
        if not self.is_world_process_zero():
            return

        if hasattr(self.model.config, "_name_or_path") and not os.path.isdir(self.model.config._name_or_path):
            base_model = self.model.config._name_or_path
        else:
            base_model = None

        tags = tags or []
        if isinstance(tags, str):
            tags = [tags]

        if hasattr(self.model.config, "unsloth_version"):
            tags.append("unsloth")

        model_card = generate_model_card(
            base_model=base_model,
            model_name=model_name,
            hub_model_id=self.hub_model_id,
            dataset_name=dataset_name,
            tags=tags,
            wandb_url=wandb.run.get_url() if is_wandb_available() and wandb.run is not None else None,
            comet_url=get_comet_experiment_url(),
            trainer_name="NER",
        )

        model_card.save(os.path.join(self.args.output_dir, "README.md"))
        
    def compute_loss(self, model, inputs:Dict, return_outputs=False, num_items_in_batch=None):
        
        outputs = model(**inputs)
        label_ids=inputs['label_ids']
        
        if hasattr(model,"compute_loss"):
            loss=model.compute_loss(outputs,label_ids)
        else:
            input_ids = outputs['input_ids']
            attention_mask = outputs['attention_mask']
            logits = outputs['logits']
            mask = torch.triu(attention_mask.unsqueeze(2) * attention_mask.unsqueeze(1))
            y_pred = logits - (1-mask.unsqueeze(1))*1e12
            y_true = label_ids.view(input_ids.shape[0] * model.ent_type_size, -1)
            y_pred = y_pred.view(input_ids.shape[0] * model.ent_type_size, -1)
            loss = multilabel_categorical_crossentropy(y_pred, y_true)

        if self.args.average_tokens_across_devices and self.model_accepts_loss_kwargs:
            loss *= self.accelerator.num_processes

        return (loss, outputs) if return_outputs else loss
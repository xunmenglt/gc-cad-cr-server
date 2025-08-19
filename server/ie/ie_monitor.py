import dataclasses 
from dataclasses import dataclass,field
from typing import Optional
from transformers.trainer_callback import (
    TrainerCallback,
    TrainerState,
    TrainerControl
)
from transformers.training_args import TrainingArguments

from ie.ie_config import IETainerConfig,IETainerServerConfig,IETainerEvent
from utils.http import get_httpx_client



class IEMonitor(TrainerCallback):
    
    def __init__(self,train_args:IETainerConfig,train_server_args:IETainerServerConfig):
        self.train_args=train_args
        self.train_server_args=train_server_args
        self.on_init_start()
    
    def on_init_start(self):
        """
        1:启动中
        """
        event= IETainerEvent(type="starting",data={"train_id":self.train_server_args.train_id},msg="初始化中")
        self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)
    
    def on_init_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        event= IETainerEvent(type="init_success",data={"train_id":self.train_server_args.train_id},msg="初始化成功")
        self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)

    def on_train_begin(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):

        event= IETainerEvent(type="train_start",data={"train_id":self.train_server_args.train_id},msg="开始训练")
        self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)

    def on_train_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        
        event= IETainerEvent(type="train_end",data={"train_id":self.train_server_args.train_id},msg="开始训练")
        self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)

    def on_epoch_begin(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the beginning of an epoch.
        """
        pass

    def on_epoch_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the end of an epoch.
        """
        pass

    def on_step_begin(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the beginning of a training step. If using gradient accumulation, one training step might take
        several inputs.
        """
        pass

    def on_pre_optimizer_step(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called before the optimizer step but after gradient clipping. Useful for monitoring gradients.
        """
        pass

    def on_optimizer_step(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called after the optimizer step but before gradients are zeroed out. Useful for monitoring gradients.
        """
        pass

    def on_substep_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the end of an substep during gradient accumulation.
        """
        pass

    def on_step_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the end of a training step. If using gradient accumulation, one training step might take
        several inputs.
        """
        pass

    def on_evaluate(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called after an evaluation phase.
        """
        pass

    def on_predict(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, metrics, **kwargs):
        """
        Event called after a successful prediction.
        """
        pass

    def on_save(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        checkpoint_name=f"checkpoint-{state.global_step}"
        event= IETainerEvent(type="save_model",data={"checkpoint_name":checkpoint_name,"model_type":"IE","train_id":self.train_server_args.train_id},msg="保存模型")
        self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)

    def on_log(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):        
        if(kwargs.get("logs")):
            logs=kwargs.get("logs",{})
            loss=logs.get("loss",-1)
            grad_norm=logs.get("grad_norm",-1)
            learning_rate=logs.get("learning_rate",-1)
            epoch=logs.get("epoch",-1)
            current_step=state.global_step
            total_step=state.max_steps
            train_id=self.train_server_args.train_id
            event = IETainerEvent(
                type="save_log",
                data=dict(
                    loss=loss, 
                    grad_norm=grad_norm, 
                    learning_rate=learning_rate, 
                    epoch=epoch, 
                    current_step=current_step, 
                    total_step=total_step, 
                    train_id=train_id
                ),
                msg="记录日志"
            )
            self.callback_to_hook(hook_url=self.train_server_args.hook_url,event=event)

    def on_prediction_step(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called after a prediction step.
        """
        pass
    
    def callback_to_hook(self,hook_url:str,event:IETainerEvent):
        if hook_url:
            with get_httpx_client() as client:
                r=client.post(url=hook_url,json=event.to_json())
                if r.status_code != 200:
                    return False
                else:
                    return True
        return False
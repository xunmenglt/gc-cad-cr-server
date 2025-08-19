import openai
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai._streaming import Stream,AsyncStream
from dataclasses import dataclass,asdict
from typing import (
    List,
    Optional,
    Union,
    Dict,
    Tuple,
    Literal,
    Iterable
)

from conf.config import (
    OPENAI_API_BASE,
    OPENAI_API_KEY
)

@dataclass
class InferenceParams:
    temperature:Optional[float]=0.7
    max_tokens:Optional[int]=4096
    max_completion_tokens:Optional[int]=2048
    

def openai_chat_by_api(
    model_name:Optional[str]="gpt-3.5-turbo",
    messages:Iterable[ChatCompletionMessageParam]=[], 
    inference_params:Union[InferenceParams,Dict]={}
):
    # 构建客户端
    client=openai.Client(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE
    )
    if isinstance(inference_params,InferenceParams):
        inference_params=asdict(inference_params)
    # 构建请求,忽略大小写    
    if "qwen3" in model_name.lower():
        completion:ChatCompletion=client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False,
            extra_body={"enable_thinking": False},
            **inference_params        
        )
    else:
        completion:ChatCompletion=client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False,
            **inference_params        
        )
    result=completion.choices[0].message.content
    return result

def openai_chat_by_api_as_stream(
    model_name:Optional[str]="gpt-3.5-turbo",
    messages:Iterable[ChatCompletionMessageParam]=[], 
    inference_params:Union[InferenceParams,Dict]={}
):
    # 构建客户端
    client=openai.Client(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE
    )
    if isinstance(inference_params,InferenceParams):
        inference_params=asdict(inference_params)
    # 构建请求    
    response:Stream[ChatCompletionChunk]=client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        **inference_params        
    )
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content
            
async def openai_chat_by_api_as_astream(
    model_name:Optional[str]="gpt-3.5-turbo",
    messages:Iterable[ChatCompletionMessageParam]=[], 
    inference_params:Union[InferenceParams,Dict]={}
):
    # 构建客户端
    client=openai.AsyncClient(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE
    )
    if isinstance(inference_params,InferenceParams):
        inference_params=asdict(inference_params)
    # 构建请求    
    response:AsyncStream[ChatCompletionChunk]=await client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        **inference_params        
    )
    async for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content



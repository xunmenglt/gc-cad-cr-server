# BSD 3- Clause License Copyright (c) 2023, Tecorigin Co., Ltd. All rights
# reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY,OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.


from typing import List, Any, Optional

from teco_client_toolkits import ClientRequest, TritonRequestParams, ApiType
from rag.connector.llm.prompt_templates import build_input

from rag.common.utils import logger

from langchain_core.language_models import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.pydantic_v1 import Extra
from langchain_core.outputs import GenerationChunk

"""
基于Langchain和Teco-Modelzoo-LLM-infer实现大模型接口
"""


class TecoLLM(LLM):
    """
    Teco-Modelzoo-LLM-Inference 提供大模型推理服务
    Backend: Triton Stream
    """
    model_name: str
    ip: str
    port: str
    grpc_port: str

    request_output_len: int = 1024
    infer_mode: str = "non-ensemble"
    top_k: float = 1
    top_p: float = 0
    temperature: float = 1.0
    repetition_penalty: float = 1.0
    len_penalty: float = 1.0
    stop_word: str = '</s>'
    start_id: int = 1
    end_id: int = 2
    protocol: str = 'grpc'

    class Config:
        """Configuration for this pydantic object."""
        extra = Extra.forbid

    def _stream(self,
                prompt: str,
                stop: Optional[List[str]] = None,
                run_manager: Optional[CallbackManagerForLLMRun] = None,
                **kwargs: Any, ):

        if self.model_name in ["Qwen-7B-Chat", "Qwen-72B"]:
            self.stop_word = "<|im_end|>"
            self.end_id = 151643
        elif self.model_name in ["InternLM2-Chat-20B"]:
            self.end_id = 92542

        client = ClientRequest(ip=self.ip, port=self.grpc_port)
        param = TritonRequestParams(mode=self.infer_mode,
                                    max_new_tokens=self.request_output_len,
                                    start_id=self.start_id,
                                    end_id=self.end_id,
                                    topk=self.top_k,
                                    topp=self.top_p,
                                    temperature=self.temperature,
                                    len_penalty=self.len_penalty,
                                    repetition_penalty=self.repetition_penalty,
                                    stop_words_list=[[self.stop_word]],
                                    protocol=self.protocol)  # 构造请求参数，triton区分ensemble格式和non-ensemble格式

        try:
            res = client.request(prompts=build_input(prompt, model_name=self.model_name),
                                 api_type=ApiType.TRITON,
                                 stream=True,
                                 params=param)
            result = res.streamer
        except Exception as e:
            msg = f'triton stream request error'
            logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
            return ''

        split_size = 0
        for out in result:
            token = out['outputs'][split_size:]
            if len(token) == 0:
                continue
            elif token[-1] == "�":
                token = token[:-1]
            split_size += len(token)
            yield GenerationChunk(text=token)

    def _call(self,
              prompt: str,
              stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None,
              **kwargs: Any, ):

        if self.model_name in ["Qwen-7B-Chat", "Qwen-72B"]:
            self.stop_word = "<|im_end|>"
            self.end_id = 151643
        elif self.model_name in ["InternLM2-Chat-20B"]:
            self.end_id = 92542

        """
        Teco Triton LLM Inference 无法同时开启流式和非流式推理
        若要在应用侧使用非流式接口，请确保：
        - 1. model_transaction_policy.decoupled设置为 True（打开Triton流式）
        - 2. 应用侧基于流式服务封装非流式接口
        """

        client = ClientRequest(ip=self.ip, port=self.grpc_port)
        param = TritonRequestParams(mode=self.infer_mode,
                                    max_new_tokens=self.request_output_len,
                                    start_id=self.start_id,
                                    end_id=self.end_id,
                                    topk=self.top_k,
                                    topp=self.top_p,
                                    temperature=self.temperature,
                                    len_penalty=self.len_penalty,
                                    repetition_penalty=self.repetition_penalty,
                                    stop_words_list=[[self.stop_word]],
                                    protocol=self.protocol)  # 构造请求参数，triton区分ensemble格式和non-ensemble格式

        try:
            res = client.request(prompts=build_input(prompt, model_name=self.model_name),
                                 api_type=ApiType.TRITON,
                                 stream=True,
                                 params=param)
            result = res.streamer
        except Exception as e:
            msg = f'triton request error'
            logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
            return ''

        split_size = 0
        output = ""
        for out in result:
            token = out['outputs'][split_size:]
            if len(token) == 0:
                continue
            elif token[-1] == "�":
                token = token[:-1]
            split_size += len(token)
            output += token
        return output

    def _llm_type(self) -> str:
        """Return type of chat model."""
        return self.model_name

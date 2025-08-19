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

from typing import List
import torch

from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import (
    HuggingFaceEmbeddings,
    HuggingFaceBgeEmbeddings
)
from rag.common.utils import logger


class LocalEmbeddings(Embeddings):

    def __init__(self,
                 model_name_or_path: str,
                 model_engine: str = "huggingface"):
        self.model_name_or_path = model_name_or_path
        self.model_engine = model_engine

        self._init_embedding_model()

    def _init_embedding_model(self):
        model_kwargs = {"device": "cpu"}
        if torch.cuda.is_available():
            model_kwargs["device"] = "cuda"
        encode_kwargs = {"normalize_embeddings": True}

        logger.info(f"Using {self.model_engine} as model engine to load embeddings")
        if self.model_engine == "huggingface":
            func_class = HuggingFaceBgeEmbeddings if any(
                [key_word in self.model_name_or_path for key_word in ["bge", "Chuxin"]]) \
                else HuggingFaceEmbeddings
            hf_embeddings = func_class(
                model_name=self.model_name_or_path,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
            )
            self.embeddings = hf_embeddings
        else:
            pass

    def embed_documents(self, docs: List[str]):
        return self.embeddings.embed_documents(docs)

    def embed_query(self, query: str):
        return self.embeddings.embed_query(query)


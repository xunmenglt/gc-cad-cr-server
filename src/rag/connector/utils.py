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

from functools import lru_cache

from rag.common.utils import logger
from rag.connector.vectorstore.base import VectorStoreBase
from rag.connector.vectorstore import ChromaVectorStore
from rag.connector.embedding.local_embedding import LocalEmbeddings
from rag.connector.llm.openai_compatible_llm import OpenaiCompatibleLLM

from langchain_core.embeddings import Embeddings
from langchain_openai.chat_models import ChatOpenAI


@lru_cache
def get_embedding_model(model_name_or_path, model_engine) -> Embeddings:
    """Create the embedding model."""

    if model_engine in ["huggingface"]:
        return LocalEmbeddings(model_name_or_path, model_engine)
    elif model_engine in ["openai"]:
        pass
    else:
        raise RuntimeError("Unable to find any supported embedding model. Supported engine is huggingface.")


# embedding_model = get_embedding_model(settings.embeddings.model_name_or_path,
#                                       settings.embeddings.model_engine)


@lru_cache
def get_vectorstore(knowledge_base_name,
                    vs_type,
                    embed_model) -> VectorStoreBase:
    """Get the vectorstore"""

    logger.info(f"Using {vs_type} as db to create vectorstore")
    if vs_type == "chroma":
        vectorstore = ChromaVectorStore(embedding_model=embed_model,
                                        collection_name=knowledge_base_name)
    elif vs_type == "faiss":
        pass

    else:
        raise ValueError(f"{vs_type} vector database is not supported")
    logger.info("Vector store created")
    return vectorstore


# vector_store = get_vectorstore(settings.vector_store.name,
#                                settings.vector_store.type,
#                                embedding_model)


@lru_cache
def get_llm(model_name, model_engine, ip, port, **kwargs):
    if model_engine == "nvidia":
        model = OpenaiCompatibleLLM(model_name=model_name,
                                    ip=ip,
                                    port=port)
    elif model_engine == "openai":
        openai_api_key = kwargs.get("api_key")
        if openai_api_key:
            model = ChatOpenAI(
                model_name=model_name,
                openai_api_key=openai_api_key,
                temperature=0.1
            )
        else:
            raise ValueError(f"please provide valid openai api key when using openai model engine! ")
    else:
        raise ValueError(f"{model_engine} is not supported! ")
    return model


## 构建一个向量存储库
import uuid
from langchain_core.embeddings import Embeddings
from rag.connector.vectorstore.base import VectorStoreBase
from rag.connector.utils import get_vectorstore
from rag.connector.utils import get_embedding_model
from rag.module.utils import get_reranker
from rag.connector.database.utils import KnowledgeFile
from rag.module.post_retrieval.reranker import Reranker
from rag.chains.indexing import IndexingChain
from rag.common.configuration import settings
from rag.chains.retrieval import RetrievalChain
from rag.module.retrieval import KeywordSearchRetriever
from typing import List

from config import EMBEDDING_MODEL_PATH,RERANKER_MODEL_PATH

def create_default_embedding_model(
    model_engine="huggingface"
)->Embeddings:
    model_path=EMBEDDING_MODEL_PATH
    return get_embedding_model(
            model_path, 
            model_engine
    )

def create_default_reranker_model(
    reranker_type="rank"
)->Reranker:
    model_path=RERANKER_MODEL_PATH
    return get_reranker(
            model_path, 
            reranker_type
    )


def create_vectorstore(
    knowledge_base_name: str = "test_kb",
    vector_store_type: str = "chroma",
    embedding_model:Embeddings=None,
)->VectorStoreBase:
    vectorstore=get_vectorstore(
        knowledge_base_name,
        vector_store_type,
        embedding_model
    )
    return vectorstore



def fast_create_vectorstore(
    vector_store_type: str = "chroma",
)->VectorStoreBase:
    """快速构建存储库"""
    vectorstore=create_vectorstore(
        knowledge_base_name=str(uuid.uuid4()),
        vector_store_type=vector_store_type,
        embedding_model=create_default_embedding_model()
    )
    return vectorstore


def creat_knowledge_file(
    filename_or_path: str,
    knowledge_base_name: str,
)->KnowledgeFile:
    return KnowledgeFile(
        filename=filename_or_path,
        knowledge_base_name=knowledge_base_name
    )


def write_file_to_vectorstore(
    filename_or_path,
    knowledge_base_name="",
    vectorstore:VectorStoreBase=None
):
    CHUNK_SIZE = settings.text_splitter.chunk_size
    OVERLAP_SIZE = settings.text_splitter.chunk_overlap
    ZH_TITLE_ENHANCE = False
    indexing_chain = IndexingChain(vectorstore=vectorstore,
                                chunk_size=CHUNK_SIZE,
                                chunk_overlap=OVERLAP_SIZE,
                                zh_title_enhance=ZH_TITLE_ENHANCE,
                                multi_vector_param={"smaller_chunk_size": settings.text_splitter.smaller_chunk_size,
                                                            "summary": settings.text_splitter.summary})
    
    failed_files = indexing_chain.chain([creat_knowledge_file(filename_or_path,knowledge_base_name)])



def retrieval_docs_from_vectorstore(
    query:str,
    vector_store:VectorStoreBase,
    score_threshold:int=0.6,
    top_k:int=10,
    keyword_list:List[str]=[]
)->list[str]:
    retrieval_chain = RetrievalChain(vectorstore=vector_store,
                                     score_threshold=score_threshold,
                                     retrievers=[
                                         KeywordSearchRetriever(
                                             keyword_list=keyword_list,
                                             vector_store=vector_store,
                                             top_k=top_k
                                         )
                                     ],
                                     top_k=top_k)
    docs = [doc["document"].page_content for doc in retrieval_chain.chain(query=query)]
    return docs
import re
from langchain_core.retrievers import BaseRetriever
from langchain.schema import Document
from typing import List, Tuple
from chromadb import PersistentClient
from rag.connector.vectorstore import ChromaVectorStore

class KeywordSearchRetriever(BaseRetriever):
    keyword_list: List[str]=[]  # 在这里声明字段
    top_k:int=10
    vector_store: ChromaVectorStore  # 也可以声明vector_store
    
    __name__="KeywordSearchRetriever"

    def _search_keywords_in_docs(self, documents: List[str]) -> List[Tuple]:
        """
        使用正则表达式搜索文档中的关键字。

        :param documents: 文档内容列表
        :return: 包含关键字匹配的文档列表
        """
        matching_docs = []
        for idx,doc in enumerate(documents):
            for key_word in self.keyword_list:
                if key_word in doc:
                    matching_docs.append((idx,doc))
        return matching_docs

    def _results_to_docs_and_scores(self, results) -> List[Tuple[Document, float]]:
        """
        处理查询结果并返回文档及其相似度。

        :param results: 查询返回的结果
        :return: 文档及其相似度的列表
        """
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        # 使用正则表达式过滤出匹配关键字的文档
        matching_docs = self._search_keywords_in_docs(documents)
        
        return [
            (Document(page_content=doc, metadata=metadatas[idx]), 1 - distances[idx]) for idx,doc in matching_docs
        ]

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        重写此方法来实现文档检索的具体逻辑

        :param query: 查询文本
        :return: 匹配的文档列表
        """
        # 获取查询的嵌入向量
        query_embeddings = self.vector_store.embeddings.embed_query(query)
        
        # 查询向量数据库
        query_result = self.vector_store.collection.query(
            query_embeddings=query_embeddings,
            n_results=20  # 返回最相关的5个文档
        )

        # 将查询结果转换为文档及其分数
        docs_and_scores = self._results_to_docs_and_scores(query_result)
        
        # 返回文档部分
        return [doc for doc, score in docs_and_scores[:self.top_k]]



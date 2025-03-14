import os
from langchain import PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.deeplake import DeepLake
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader
from langchain.chat_models.openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferWindowMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate
# Set logging for the queries
import logging

from .utils import save

import config as cfg

logging.basicConfig()
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

class Retriever:
    def __init__(self):
        self.vectordb = None
        self.text_retriever = None
        self.text_deeplake_schema = None
        self.embeddings = None
        self.memory = ConversationBufferWindowMemory(k=2, return_messages=True)

    def create_and_add_embeddings(self, file):
        os.makedirs("data", exist_ok=True)

        self.embeddings = OpenAIEmbeddings(
            openai_api_key=cfg.OPENAI_API_KEY,
            chunk_size=cfg.OPENAI_EMBEDDINGS_CHUNK_SIZE,
        )

        loader = PyMuPDFLoader(file)
        documents = loader.load()
        print("#######################################################")
        print (f"You have {len(documents)} essays loaded")
        print("#######################################################")
        text_splitter = CharacterTextSplitter(
            chunk_size=cfg.CHARACTER_SPLITTER_CHUNK_SIZE,
            chunk_overlap=0,
        )
        docs = text_splitter.split_documents(documents)
        print("#######################################################")
        print (f"Your {len(documents)} documents have been split into {len(docs)} chunks")
        print("#######################################################")
        
        if 'vectordb' in globals(): # If you've already made your vectordb this will delete it so you start fresh
             self.vectordb.delete_collection()

        embedding = OpenAIEmbeddings()
        self.vectordb = Chroma.from_documents(documents=docs, embedding=embedding)

        """ self.text_deeplake_schema = DeepLake(
            dataset_path=cfg.TEXT_VECTORSTORE_PATH,
            embedding_function=self.embeddings,
            overwrite=True,
        )

        self.text_deeplake_schema.add_documents(docs)

        self.text_retriever = self.text_deeplake_schema.as_retriever(
            search_type="similarity"
        )
        self.text_retriever.search_kwargs["distance_metric"] = "cos"
        self.text_retriever.search_kwargs["fetch_k"] = 15
        self.text_retriever.search_kwargs["maximal_marginal_relevance"] = True
        self.text_retriever.search_kwargs["k"] = 3
 """
    def retrieve_text(self, question):
        """ self.text_deeplake_schema = DeepLake(
            dataset_path=cfg.TEXT_VECTORSTORE_PATH,
            read_only=True,
            embedding_function=self.embeddings,
        ) """

        llm = ChatOpenAI(temperature=0)

        retriever_from_llm = MultiQueryRetriever.from_llm(
        retriever=self.vectordb.as_retriever(), llm=llm)
        
        unique_docs = retriever_from_llm.get_relevant_documents(query=question)

        print("#######################################################")
        print (f"TAMANHO MULTIQUERY {len(unique_docs)}")
        print("#######################################################")

        prompt_template = """You are an intelligent AI which analyses text from documents and 
        answers the user's questions. Please answer in as much detail as possible, so that the user does not have to 
        revisit the document. If you don't know the answer, say that you don't know, and avoid making up things.
        {context}
        Question: {question} 
        Answer:
        """

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )


        """ chain_type_kwargs = {"prompt": PROMPT}

        model = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            openai_api_key=cfg.OPENAI_API_KEY,
        )

        qa = RetrievalQA.from_chain_type(
            llm=model,
            chain_type="stuff",
            retriever=self.text_retriever,
            return_source_documents=False,
            verbose=False,
            chain_type_kwargs=chain_type_kwargs,
            memory=self.memory,
        ) """

        ##response = qa({"query": query})

        response = llm.predict(text=PROMPT.format_prompt(context=unique_docs,
                                                         question=question).text)

        return response
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.tools.google_scholar import GoogleScholarQueryRun
from langchain_community.utilities.google_scholar import GoogleScholarAPIWrapper
from langchain_community.vectorstores import faiss as f
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts.chat import (ChatPromptTemplate)
from langchain_core.runnables import RunnableLambda, RunnablePassthrough,RunnableParallel
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from pyserpZotero.pyserpZotero import SerpZot as zot
from pyzotero import zotero
from sentence_transformers import SentenceTransformer
import faiss
import fitz
import json
import numpy as np
import os
import pickle
import pyzotero
import uuid

client = OpenAI()


class LangChainAssistant:
    def __init__(self, serp_api_key, zot_id, zot_key, pkl_path="", pdf_paths=""):
        self.pkl_path = pkl_path
        self.session_id = str(uuid.uuid4())
        os.environ["SERP_API_KEY"] = serp_api_key
        self.model = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
        self.sysmsg = ("You are pyserpZotero - an AI Zotero-enabled literature reviewer. "
                       "You will be given access to one or more of: RAG results based on "
                       "the user's list of Zotero citations and PDFs, search results from "
                       "Bing, Google Scholar, and other sources. Use all available knowledge "
                       "to provide the user with an exceedingly high quality answer. You may "
                       "combine the supplied data with your general knowledge, but try to cite "
                       "your sources as much as possible. You should be able to radically exceed "
                       "the quality of other AI assistants and human literature reviewers by doing this.")
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.sysmsg),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )
        self.memory = SQLChatMessageHistory(
            session_id=self.session_id, connection_string="sqlite:///sqlite.db"
        )
        self.google_scholar_tool = GoogleScholarQueryRun(api_wrapper=GoogleScholarAPIWrapper())
        self.google_scholar_runnable = RunnableLambda(func=self.run_google_scholar_query)
        self.zot_id  = zot_id
        self.zot_key = zot_key
        self.zot = pyzotero.zotero.Zotero(zot_id, 'user', zot_key)
        self.pdf_paths = pdf_paths or []
        #self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.faiss_index     = None
        self.documents       = []
        self.chain = (self.prompt
                      | self.google_scholar_runnable
                      | self.model
                      )

        def load_documents_from_pkl(self):
            with open(self.pkl_path, 'rb') as file:
                documents = pickle.load(file)
            return documents

        self.load_documents_from_pkl = load_documents_from_pkl

        def embed_documents_with_openai(self, documents):
            embeddings = []
            documents = documents[-10:]  # TEMP for testing only
            for document in documents:
                response = client.embeddings.create(input=document, model="text-embedding-3-large")
                embeddings.append(response.data[0].embedding)
            return np.vstack(embeddings)
        self.embed_documents_with_openai = embed_documents_with_openai

        def jason_style(self, documents):
            embeddings = OpenAIEmbeddings()
            docs       = documents[-10:]
            from langchain_text_splitters import CharacterTextSplitter
            text_splitter = (CharacterTextSplitter(chunk_size=1000,
                                                   chunk_overlap=0))
            txt = text_splitter.split_text(str(docs))
            db = f.FAISS.from_texts(txt, embeddings)
            return db
        self.jason_style = jason_style

        def create_faiss_index(self, embeddings):
            dimension = embeddings.shape[1]
            faiss_index = faiss.IndexFlatL2(dimension)
            faiss_index.add(embeddings)
            return faiss_index
        self.create_faiss_index = create_faiss_index

    def extract_text_from_pdfs(self):
        text_content = ""
        for pdf_path in self.pdf_paths:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text_content += page.get_text()
        return text_content

    def format_citations_for_prompt(self, items):
        """Format Zotero items for inclusion in a prompt."""
        citations = []
        for item in items:
            try:
                title  = item['data']['title']
                author = item['data']['creators'][0]['lastName'] if item['data']['creators'] else 'Unknown'
                citations.append(f"{title} by {author}")
            except KeyError:
                continue
        return "\n".join(citations)

    def run_google_scholar_query(self, input_data):
        query = input_data.messages[-1].content if input_data.messages else None
        if query:
            tool     = GoogleScholarQueryRun(api_wrapper=GoogleScholarAPIWrapper())
            result   = tool.run({"query": query})

            messages = [
                SystemMessage(
                    content=self.sysmsg
                ),
                HumanMessage(
                    content="The user's question is: " + query + " The Google Scholar search results gathered to help you answer it is: " + result
                ),
            ]
            return messages
        else:
            return {"output": "No query provided."}

    def invoke(self, input_query):
        #extracted_text = self.extract_text_from_pdfs()
        citations = self.load_documents_from_pkl(self)
        #formatted_citations = self.format_citations_for_prompt(citations)
        db = self.jason_style(documents=citations[-3:], self=self)
        print("Starting retrieval...")
        rag_output = db.as_retriever().invoke(input_query)

        print("Starting chain...")
        chain_with_history = RunnableWithMessageHistory(
            self.chain,
            lambda session_id: SQLChatMessageHistory(
                session_id=session_id, connection_string="sqlite:///sqlite.db"
            ),
            input_messages_key="question",
            history_messages_key="history",
        )

        # Execute the chain with the input query, capturing the response
        config = {"configurable": {"session_id": self.session_id}}

        response = chain_with_history.invoke({"question": input_query}, config=config)

        combined_context = f"System: Based on the following details from RAG and Google Scholar search, synthesize a comprehensive answer without losing any information. RAG Output: {rag_output} \n\n Search Output: {response.content}"
        final_prompt = {
            "input": input_query,
            "context": combined_context
        }

        final_chain = (
                RunnablePassthrough(lambda: final_prompt)
                | ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
                #| StrOutputParser()
        )
        final_answer = final_chain.invoke(final_prompt)
        return final_answer.content


# Example usage
if __name__ == "__main__":
    pdf_paths = ["/Users/user/PycharmProjects/pyserpZotero/10.1007_s13347-021-00450-x.pdf"]
    zot_id = "7032524"
    zot_key = "ZVrF7TXnla2jRrQ86ujpecud"
    serp_api_key = "58b73df719b00998d8f2a61d3f6e9bb2d8086a0013020f9a09094521de1ba831"
    #user_question = "Tell me about ?"
    #response = assistant.invoke(user_question)
    #print(response)
    assistant = LangChainAssistant(
        serp_api_key="58b73df719b00998d8f2a61d3f6e9bb2d8086a0013020f9a09094521de1ba831",
        zot_id="7032524",
        zot_key="ZVrF7TXnla2jRrQ86ujpecud",
        pkl_path='../my_object.pkl'
    )


    # Interaction phase: Enter into a loop for handling user queries
    while True:
        user_question = input("What would you like to know? (Type 'exit' to end the session): ")
        if user_question.lower() == 'exit':
            print("Session ended. Thank you for using the AI assistant.")
            break
        response = assistant.invoke(user_question)
        print(response)

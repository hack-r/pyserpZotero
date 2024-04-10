import time

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.tools.google_scholar import GoogleScholarQueryRun
from langchain_community.utilities.google_scholar import GoogleScholarAPIWrapper
from langchain_community.vectorstores import faiss
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts.chat import (ChatPromptTemplate)
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from operator import itemgetter
from pyserpZotero.pyserpZotero import SerpZot as zot
from sentence_transformers import SentenceTransformer
import fitz
import json
import numpy as np
import os
import pyzotero.zotero
import uuid

class LangChainAssistant:
    def __init__(self, serp_api_key, zot_id, zot_key, zotero_citation_path="", pdf_paths=""):
        self.session_id = str(uuid.uuid4())
        os.environ["SERP_API_KEY"] = serp_api_key
        self.model = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
        self.sysmsg = "You are pyserpZotero - an AI Zotero-enabled literature reviewer. You will be given access to one or more of: 1. RAG results based on the user's list of Zotero citations and PDFs 2. search results from Bing, Google Scholar, and other sources. Use all available knowledge to provide the user with an exceedingly high quality answer. You may combine the supplied data with your general knowledge, but try to cite your sources as much as possible. You should be able to radically exceed the quality of other AI assistants and human literature reviewers by doing this."
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
        self.zotero_citation_path = zotero_citation_path or []
        self.pdf_paths = pdf_paths or []
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.faiss_index     = None
        self.documents       = []
        self.chain = (self.prompt
                      | self.google_scholar_runnable
                      | self.model
                      )



    def embed_and_index_documents(self):
        print("Preparing documents for embedding and indexing...")

        # Prepare documents from Zotero and PDFs
        document_texts = self.collect_documents()
        embeddings = OpenAIEmbeddings()
        faiss_db = (faiss.FAISS.from_documents(document_texts, embeddings))
        # Embed documents
        #embeddings = self.embedding_model.encode(document_texts, convert_to_tensor=False)
        # Initialize FAISS index
        #dim = embeddings.shape[1]
        #self.faiss_index = faiss.IndexFlatL2(dim)
        #self.faiss_index.add(np.array(embeddings))
        print("Documents embedded and indexed successfully.")

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
            # Simple formatting - customize as needed
            try:
                title  = item['data']['title']
                author = item['data']['creators'][0]['lastName'] if item['data']['creators'] else 'Unknown'
                citations.append(f"{title} by {author}")
            except KeyError:
                continue
        formatted_citations = "\n".join(citations)
        return formatted_citations

    def load_zotero_citations(self):
        if self.zotero_citation_path and os.path.exists(self.zotero_citation_path):
            with open(self.zotero_citation_path, 'r') as file:
                return json.load(file)
        return {}

    def print_vector_store_summary(self):
        num_documents = len(self.documents)
        print(f"Vector store summary: {num_documents} documents indexed (including citations and PDFs).")

    def prepare_embeddings(self):
        # Collect all texts to be embedded
        texts = self.collect_texts_from_sources()

        # Embed all collected texts
        embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)

        # Return the embeddings and the associated text data
        return embeddings, texts

    def retrieve_documents(self, query, k=5):
        # Embed query
        query_embedding = self.embedding_model.encode([query], convert_to_tensor=False).reshape(1, -1)
        # Search in FAISS
        _, I = self.faiss_index.search(query_embedding, k)
        return [self.documents[i] for i in I[0]]

    def retrieve_zotero_citations(self, query):
        """Retrieve citations from Zotero based on a query."""
        items = self.zot.everything(self.zot.items(q=query))
        return items

    def run_google_scholar_query(self, input_data):
        query = input_data.messages[len(input_data.messages)-1]
        if query:
            tool     = GoogleScholarQueryRun(api_wrapper=GoogleScholarAPIWrapper())
            result   = tool.run({"query": query})

            messages = [
                SystemMessage(
                    content=self.sysmsg
                ),
                HumanMessage(
                    content="The user's question is: " + query.content + " The Google Scholar search results gathered to help you answer it is: " + result
                ),
            ]
            return messages
        else:
            return {"output": "No query provided."}

    def invoke(self, input_query):
        #extracted_text = self.extract_text_from_pdfs()
        #zotero_citations = self.load_zotero_citations()
        citations = self.retrieve_zotero_citations(input_query)
        formatted_citations = self.format_citations_for_prompt(citations)


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
        response = response.content

        return response

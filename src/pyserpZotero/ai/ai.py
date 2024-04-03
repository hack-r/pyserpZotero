#from ragatouille import RAGPretrainedModel
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.tools.google_scholar import GoogleScholarQueryRun
from langchain_community.utilities.google_scholar import GoogleScholarAPIWrapper
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts.chat import (
    ChatPromptTemplate
)
import os


class LangChainAssistant:
    def __init__(self, serp_api_key, session_id):
        self.session_id = session_id
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
        config = {"configurable": {"session_id": "123"}}
        self.memory = SQLChatMessageHistory(
            session_id=session_id, connection_string="sqlite:///sqlite.db"
        )
        #self.RAG = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
        self.google_scholar_tool = GoogleScholarQueryRun(api_wrapper=GoogleScholarAPIWrapper())
        self.google_scholar_runnable = RunnableLambda(func=lambda input_data: self.run_google_scholar_query(input_data))
        self.chain = (self.prompt
                      | self.google_scholar_runnable
                      | self.model
                      )

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
                    content="The user's question is: " + query.content +" The Google Scholar search results gathered to help you answer it is: " + result
                ),
            ]
            return messages
        else:
            return {"output": "No query provided."}

    def invoke(self, input_query):
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

        return response
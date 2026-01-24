import os
from langchain_community.chat_models import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory

# --- Configuration from Environment ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Initialize the LLM pointing to the Ollama container
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0.3,
)

# Conversation memory with summarization
memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000)

# Conversation chain orchestrating LLM + Memory
conversation_chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True,
)


def get_agent_response(user_input: str) -> str:
    """
    Gets a response from the conversational agent.

    Args:
        user_input: The text from the user.

    Returns:
        The agent's response.
    """
    response = conversation_chain.predict(input=user_input)
    return response

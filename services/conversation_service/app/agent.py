from langchain_community.chat_models import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Initialize the LLM
llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# Initialize conversation memory
memory = ConversationBufferMemory()

# Initialize the conversation chain
conversation_chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True  # Set to True to see the chain's internal state in the server logs
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

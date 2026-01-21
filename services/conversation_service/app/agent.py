from langchain_community.chat_models import ChatOllama
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory 

# Initialize the LLM
llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# Initialize conversation memory
# This memory summarizes older parts of the conversation once the token limit is reached.
# It needs the LLM to do the summarization.
memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000)

# Initialize the conversation chain
conversation_chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True  
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

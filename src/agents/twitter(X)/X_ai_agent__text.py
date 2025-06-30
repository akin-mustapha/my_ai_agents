import os
import tweepy
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool


load_dotenv() # Load environment variables from .env file

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

@tool
def post_tweet(tweet_content: str) -> str:
  """
    Publishes a tweet to the connected X (Twitter) account.
    Use this tool whenever a user asks to post something on Twitter
    The input should be the full text content of the tweet.
  """
  try:
    client = tweepy.Client(
      consumer_key=TWITTER_API_KEY,
      consumer_secret=TWITTER_API_SECRET,
      access_token=TWITTER_ACCESS_TOKEN,
      access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )


    res = client.create_tweet(text=tweet_content)
    tweet_id = res.data['id']
    return f"Successfully posted tweet. Tweet ID: {tweet_id}"
  except Exception as e:
    return f"Failed to post tweet. Error: {e}"
  
tools = [post_tweet]

llm = ChatOpenAI(model='gpt-4.1', temperature=0)

template = """
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:
Question: the imput question you must answer
Thought: you should always think about what to do 
Actions the action to take should be one of [{tool_names}]
Aciont Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thoughts I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
"""
prompt = PromptTemplate.from_template(template)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# print('\n--- Running Example 1 ---')
# result = agent_executor.invoke({
#   "input": "Please post a tweet for me that says 'Hello world, I am a Langhain Agent!'"
# })

# print(f"Final Result: {result['output']}")



print('\n--- Running Example 2 ---')
result = agent_executor.invoke({
  "input": "Can you craft can post a tweet about the day to day use of AI and also indicate the post is being made by an AI"
})

print(f"Final Result: {result['output']}")

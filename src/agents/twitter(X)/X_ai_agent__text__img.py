# agent_core.py
import os
import json
import tweepy
import requests
from io import BytesIO
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper

# Load environment variables (ensure .env is in the project root or specified path)
load_dotenv()

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# Twitter API Credentials
consumer_key = os.environ.get("TWITTER_API_KEY")
consumer_secret = os.environ.get("TWITTER_API_SECRET")
access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
    raise ValueError("One or more Twitter API keys/tokens are missing in environment variables.")

# Initialize Twitter API (shared resource)
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
twitter_api = tweepy.API(auth) # For media upload (v1.1)

# Initialize Twitter Client for v2 API (for creating tweets)
twitter_client_v2 = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# --- Define the Twitter Posting Tool ---
@tool
def post_tweet_with_image(tweet_data: str) -> str:
    """
    Posts a tweet to Twitter, optionally with an image.
    The input should be a JSON string like:
    {"text": "Your tweet text", "image_url": "http://image.url/generated.png"}
    or {"text": "Your tweet text"} if no image.
    """
    try:
        data = json.loads(tweet_data)
        text = data.get("text")
        image_url = data.get("image_url")

        if not text:
            return "Error: Tweet text is required."

        media_id = None
        if image_url:
            try:
                response = requests.get(image_url)
                response.raise_for_status()
                image_bytes = BytesIO(response.content)
                # Use tweepy.API for media upload (it uses v1.1 endpoint)
                upload_result = twitter_api.media_upload(filename="image.png", file=image_bytes)
                media_id = upload_result.media_id_string
                print(f"Image uploaded to Twitter with media_id: {media_id}")
            except Exception as e:
                return f"Error uploading image to Twitter: {e}. Please ensure the image_url is valid and accessible."

        if media_id:
            # Use tweepy.Client for posting tweet (v2 API)
            twitter_client_v2.create_tweet(text=text, media_ids=[media_id])
        else:
            twitter_client_v2.create_tweet(text=text)
        return "Tweet posted successfully!"
    except Exception as e:
        return f"Failed to post tweet: {e}"

# --- Define the Image Generation Tool ---
dalle_wrapper = DallEAPIWrapper(model="dall-e-3")

@tool
def generate_dalle_image(prompt: str) -> str:
    """
    Generates an image using DALL-E based on the given prompt.
    Returns the URL of the generated image.
    """
    try:
        image_url = dalle_wrapper.run(prompt)
        return image_url
    except Exception as e:
        return f"Error generating image with DALL-E: {e}"

# --- Set up the Langchain Agent ---
llm = ChatOpenAI(model="gpt-4", temperature=0.7) # Using gpt-4 for better context understanding
tools = [generate_dalle_image, post_tweet_with_image]

# Define the prompt template for the agent
prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
{agent_scratchpad}
""")

# Create and export the agent executor
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

# You can add a function to run the agent from outside if needed
def run_twitter_agent(user_input: str, scratchpad: str = "") -> dict:
    """
    Runs the Twitter AI agent with the given input and scratchpad.
    """
    return agent_executor.invoke({
        "input": user_input,
        "agent_scratchpad": scratchpad
    })

if __name__ == "__main__":
    # pass
    # Example usage for testing agent_core.py directly
    print("Running agent_core.py directly for a test tweet...")
    test_input = "Generate a funny tweet saying Good morning. Tweet should be accompanied by an image of a cat wearing sunglasses. Indicate image was generated by DALL-E. Also ask people to like and retweet the post. Include a link to the image in the tweet."
    test_scratchpad = "I will generate an image of a cat wearing sunglasses."
    try:
        result = run_twitter_agent(test_input, test_scratchpad)
        print("\nTest Agent Output:")
        print(result["output"])
    except Exception as e:
        print(f"An error occurred during direct agent test: {e}")
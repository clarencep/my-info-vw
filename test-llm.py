"""
Simple test script for OpenAI model using LangChain.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables from .env file
load_dotenv()


def test_openai_model():
    """Test the OpenAI model with a simple prompt."""
    # Initialize the OpenAI model with environment variables
    model = ChatOpenAI(
        openai_api_base=os.getenv("OPENAI_API_BASE_URL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL"),
    )

    # Create a simple test message
    message = HumanMessage(
        content="Hello! Please respond with 'Yeah! I am here.'"
    )

    # Invoke the model
    print("Testing OpenAI model...")
    print("-" * 50)

    try:
        response = model.invoke([message])
        print(f"Response: {response.content}")
        print("-" * 50)
        print("✓ Test completed successfully!")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    test_openai_model()

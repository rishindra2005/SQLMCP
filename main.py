import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai
from google.genai import types

load_dotenv() # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mcp_server = FastMCP()

@mcp_server.tool()
def hello(name: str) -> str:
    """
    A simple tool that returns a greeting.
    """
    logging.info(f"Tool 'hello' called with name: {name}")
    return f"Hello, {name}!"

@mcp_server.tool()
def generate_text(prompt: str) -> str:
    """
    Generates text using the Gemini API.
    """
    logging.info(f"Tool 'generate_text' called with prompt: {prompt}")
    
    # --- IMPORTANT ---
    # The user needs to set the GEMINI_API_KEY environment variable for this tool to work.
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set.")
        return "Error: GEMINI_API_KEY not set."

    try:
        client = genai.Client(api_key=api_key)
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
        logging.debug(f"Gemini API response: {response.text}")
        return response.text
    except Exception as e:
        logging.error(f"An error occurred with the Gemini API: {e}")
        return f"Error: {e}"

if __name__ == "__main__":
    logging.info("Starting MCP server in HTTP mode...")
    mcp_server.run(transport="http")

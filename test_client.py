import logging
import asyncio
import click
from dotenv import load_dotenv
from fastmcp import Client

load_dotenv() # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@click.command()
@click.argument('prompt', nargs=-1)
@click.option('--server-url', default='http://127.0.0.1:8000/mcp', help='The URL of the MCP server.')
def main(prompt: tuple[str], server_url: str):
    """
    A CLI client to test the MCP server's generate_text tool.
    """
    prompt_str = " ".join(prompt)
    if not prompt_str:
        print("Error: Please provide a prompt.")
        return
    asyncio.run(run_client(prompt_str, server_url))

async def run_client(prompt: str, server_url: str):
    logging.info(f"Connecting to MCP server at {server_url}")
    try:
        client = Client(server_url)
        async with client:
            logging.info(f"Calling 'generate_text' tool with prompt: {prompt}")
            result = await client.call_tool("generate_text", {"prompt": prompt})
            print(f"Server response: {result}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

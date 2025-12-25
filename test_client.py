import logging
import asyncio
import os
import json
from dotenv import load_dotenv
from fastmcp import Client
from google import genai
from google.genai import types

# --- Basic Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Internal LLM Helper ---
def _generate_text(system_prompt: str, history: list, user_prompt: str) -> str:
    """Internal function to generate text using the Gemini API, including chat history."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY not set.")
        return '{"error": "GEMINI_API_KEY not set."}'
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Construct the full conversation history
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)]),
            types.Content(role="model", parts=[types.Part.from_text(text="Understood. I will act as a database management assistant and use the conversation history to resolve ambiguity.")])
        ]
        for user_msg, model_msg in history:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_msg)]))
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=model_msg)]))
        
        # Add the current user prompt
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]))

        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
        return response.text
    except Exception as e:
        logging.error(f"Error generating text: {e}")
        return f'{{"error": "Error generating text: {e}"}}'

async def main():
    """
    A stateful, continuous chat-like agent client for the DBMS MCP server.
    """
    server_url = 'http://127.0.0.1:8000/mcp'
    print("DBMS Agent Client (type 'exit' or 'quit' to close)")

    try:
        client = Client(server_url)
        async with client:
            logging.info("Fetching available tools from server...")
            tool_schemas_list = await client.list_tools()
            
            tool_schemas = {
                tool.name: {
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tool_schemas_list
            }
            
            logging.info(f"Found {len(tool_schemas)} tools.")
            
            system_prompt = f"""
            You are a database management assistant. Your goal is to help the user manage a MySQL database by calling the appropriate tools.
            You have access to a conversation history. Use the history to resolve ambiguity in prompts. For example, if the user says "delete the database we just created", you should look at the history to find the name of that database.
            Based on the user's prompt and the conversation history, choose the best tool to call from the following list.
            You must respond with a single, valid JSON object containing the 'tool_name' and a dictionary of 'arguments'. Do not add any other text or formatting.

            Available Tools:
            {json.dumps(tool_schemas, indent=2)}
            """
            
            history = []
            
            while True:
                prompt = input("> ")
                if prompt.lower() in ["exit", "quit"]:
                    break
                if not prompt:
                    continue

                llm_prompt = f'User\'s request: "{prompt}"\n\nJSON response:'
                llm_response_str = _generate_text(system_prompt, history, llm_prompt)
                logging.info(f"LLM response: {llm_response_str}")
                
                try:
                    if llm_response_str.strip().startswith("```json"):
                        llm_response_str = llm_response_str.strip()[7:-4].strip()

                    llm_response = json.loads(llm_response_str)
                    tool_name = llm_response.get("tool_name")
                    arguments = llm_response.get("arguments", {})

                    if tool_name in tool_schemas:
                        logging.info(f"Client is calling tool '{tool_name}' with arguments: {arguments}")
                        result = await client.call_tool(tool_name, arguments)
                        result_str = str(result.data)
                        print(f"Result: {result_str}")
                        
                        # Add the successful interaction to the history
                        history.append((f"User request: {prompt}", f"Agent action: Called tool '{tool_name}' with arguments {arguments}. Result: {result_str}"))

                    else:
                        print(f"Error: The model chose an invalid tool: {tool_name}")
                        history.append((f"User request: {prompt}", f"Agent action: The model tried to call an invalid tool: {tool_name}"))

                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Error parsing LLM response: {e} - Response was: {llm_response_str}")
                    print(f"Could not determine which action to take. The model returned an invalid format.")
                    history.append((f"User request: {prompt}", f"Agent action: Error parsing LLM response."))
                except Exception as e:
                    logging.error(f"An unexpected error occurred: {e}")
                    print(f"An unexpected error occurred: {e}")
                    history.append((f"User request: {prompt}", f"Agent action: An unexpected error occurred: {e}"))

    except Exception as e:
        logging.error(f"Failed to connect to the server at {server_url}: {e}")
        print(f"Error: Could not connect to the MCP server. Is it running?")

if __name__ == "__main__":
    asyncio.run(main())

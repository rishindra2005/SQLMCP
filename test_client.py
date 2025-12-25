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
# Reduce logging noise for a cleaner chat interface
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# --- Internal LLM Helper ---
def _generate_text(prompt: str) -> str:
    """Internal function to generate text using the Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY not set.")
        return '{"final_answer": "Error: GEMINI_API_KEY not set."}'
    try:
        client = genai.Client(api_key=api_key)
        # The ReAct prompt is sent as a single block, so we don't need complex history management here.
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
        return response.text
    except Exception as e:
        log.error(f"Error generating text: {e}")
        return f'{{"final_answer": "Error generating text: {e}"}}'

def _parse_json_from_response(response_str: str) -> dict | None:
    """Tries various strategies to parse a JSON object from an LLM response string."""
    # Strategy 1: Direct parsing
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Clean up markdown `json` tags
    if response_str.strip().startswith("```json"):
        cleaned_str = response_str.strip()[7:-4].strip()
        try:
            return json.loads(cleaned_str)
        except json.JSONDecodeError:
            pass
            
    # Strategy 3: Extract JSON object from a larger string
    try:
        start = response_str.find('{')
        end = response_str.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = response_str[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None # Return None if all strategies fail

async def main():
    """
    A ReAct-style agent client for the DBMS MCP server.
    """
    server_url = 'http://127.0.0.1:8000/mcp'
    print("DBMS ReAct Agent Client (type 'exit' or 'quit' to close)")

    try:
        client = Client(server_url)
        async with client:
            log.info("Fetching available tools from server...")
            tool_schemas_list = await client.list_tools()
            
            tool_schemas = {
                tool.name: {
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tool_schemas_list
            }
            
            log.info(f"Found {len(tool_schemas)} tools.")
            
            system_prompt = f"""
            You are a ReAct-style database management assistant. Your goal is to achieve the user's objective by thinking, acting, and observing.

            **Workflow:**
            1.  **Thought:** First, think step-by-step about the user's request and your plan. Your thought process should be detailed.
            2.  **Action:** Based on your thought, decide if you need to use a tool.
                - If you use a tool, the 'arguments' dictionary MUST contain all the required parameters for that tool as defined in its 'input_schema'.
                - If you have the final answer for the user, provide that in the 'final_answer' field.
            3.  **Observation:** After you act, you will be given the result of your action.
            4.  Repeat this process of Thought, Action, Observation until you have the final answer for the user.

            **Self-Correction:**
            If an Action results in an error, you MUST re-evaluate your plan in the next Thought step. Use the error message to inform your next action. For example, if a database name is wrong, list the databases to find the correct name.

            **Response Format:**
            You MUST respond with a single valid JSON object containing EITHER:
            - A 'thought' and an 'action' (for tool calls).
            - A 'thought' and a 'final_answer'.

            **VERY IMPORTANT**: Your entire response MUST be ONLY the JSON object. Do not add any conversational text or formatting before or after the JSON. Any explanation, plan, or final message to the user must be placed inside the `final_answer` field.

            **Example (Tool Call with arguments):**
            ```json
            {{
                "thought": "I have found the correct database name is 'nolan'. I will now delete it.",
                "action": {{
                    "tool_name": "delete_database",
                    "arguments": {{
                        "db_name": "nolan"
                    }}
                }}
            }}
            ```

            **Available Tools:**
            {json.dumps(tool_schemas, indent=2)}
            """
            
            trajectory = [] # Initialize history here
            
            while True:
                user_prompt = input("> ")
                if user_prompt.lower() in ["exit", "quit"]:
                    break
                if not user_prompt:
                    continue

                trajectory.append(f"User's objective: {user_prompt}") # Append to history
                max_steps = 15 # To prevent infinite loops

                for i in range(max_steps):
                    print("---")
                    
                    # 1. THINK and DECIDE on an ACTION
                    prompt_with_history = f"{system_prompt}\n\n**Conversation Trajectory:**\n" + "\n".join(trajectory)
                    llm_response_str = _generate_text(prompt_with_history)
                    
                    try:
                        llm_response = _parse_json_from_response(llm_response_str)

                        if not llm_response:
                            # If parsing fails completely, treat the raw string as a final answer.
                            print(f"Warning: Could not parse model's response as JSON. Assuming it's a final answer.")
                            thought = "(Could not parse thought, assuming raw response is the answer)"
                            print(f"🤔 Thought: {thought}")
                            trajectory.append(f"Thought: {thought}")
                            
                            final_answer = llm_response_str
                            print(f"\n✅ Final Answer: {final_answer}")
                            trajectory.append(f"Final Answer: {final_answer}")
                            break # End of this query's loop

                        thought = llm_response.get("thought", "(No thought provided)")
                        print(f"🤔 Thought: {thought}")
                        trajectory.append(f"Thought: {thought}")

                        # Check if the agent has a final answer
                        if "final_answer" in llm_response:
                            final_answer = llm_response["final_answer"]
                            print(f"\n✅ Final Answer: {final_answer}")
                            trajectory.append(f"Final Answer: {final_answer}")
                            break # End of this query's loop

                        # 2. ACT (Call a tool)
                        action = llm_response.get("action")
                        if not action or "tool_name" not in action:
                            print("Error: Model did not provide a valid action or final answer.")
                            break

                        tool_name = action["tool_name"]
                        arguments = action.get("arguments", {})
                        
                        if tool_name in tool_schemas:
                            print(f"🎬 Action: Calling tool '{tool_name}' with arguments: {arguments}")
                            trajectory.append(f"Action: Call tool `{tool_name}` with arguments `{arguments}`")
                            
                            result = await client.call_tool(tool_name, arguments)
                            observation = str(result.data)
                            
                            print(f"🧐 Observation: {observation}")
                            trajectory.append(f"Observation: {observation}")
                        else:
                            print(f"Error: Model chose an invalid tool: '{tool_name}'")
                            trajectory.append(f"Observation: Invalid tool '{tool_name}' selected.")
                            break
                            
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                        break
                else:
                    print("Warning: Agent reached maximum steps without finding a final answer.")


    except Exception as e:
        log.error(f"Failed to connect to the server at {server_url}: {e}")
        print(f"\nError: Could not connect to the MCP server. Is it running?")

if __name__ == "__main__":
    asyncio.run(main())
import logging
import asyncio
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, Response, stream_with_context
from fastmcp import Client
from google import genai
from google.genai import types

# --- Basic Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Agent State ---
# In-memory trajectory for conversation history.
trajectory = []

# --- Internal LLM & Parsing Helpers ---
def _generate_text(prompt: str) -> str:
    """Internal function to generate text using the Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY not set.")
        return '{"final_answer": "Error: GEMINI_API_KEY not set."}'
    try:
        client = genai.Client(api_key=api_key)
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
        return response.text
    except Exception as e:
        logging.error(f"Error generating text: {e}")
        return f'{{"final_answer": "Error generating text: {e}"}}'

def _parse_json_from_response(response_str: str) -> dict | None:
    """Tries various strategies to parse a JSON object from an LLM response string."""
    # Strategy 1: Direct parsing
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON within markdown code blocks
    if '```json' in response_str:
        start_pos = response_str.find('```json')
        end_pos = response_str.find('```', start_pos + 7)
        if start_pos != -1 and end_pos != -1:
            json_text = response_str[start_pos + 7:end_pos].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

    # Strategy 3: Find the first and last brace and parse as JSON
    try:
        start = response_str.find('{')
        end = response_str.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = response_str[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None

# --- Agent Core Logic ---
async def run_agent_steps(user_prompt: str):
    """
    Connects to the MCP, runs the ReAct agent logic, and yields each step as it happens.
    """
    global trajectory

    if user_prompt:
        trajectory.append(f"User's objective: {user_prompt}")

    server_url = 'http://127.0.0.1:8000/mcp'
    
    try:
        async with Client(server_url) as mcp_client:
            logging.info("Agent connected to MCP server.")
            tool_schemas_list = await mcp_client.list_tools()
            tool_schemas = {
                tool.name: {"description": tool.description, "input_schema": tool.inputSchema}
                for tool in tool_schemas_list
            }
            
            system_prompt = f"""
                You are a ReAct-style database management assistant. Your goal is to achieve the user's objective by thinking, acting, and observing.
                **Workflow:**
                1. **Thought:** Think step-by-step about the user's request and your plan.
                2. **Action:** Based on your thought, decide if you need to use a tool. Unless the user is just saying hello, you should almost always follow your thought with an 'action' or a 'final_answer'.
                3. **Observation:** After you act, you will be given the result of your action.
                Repeat this process until you have the final answer.
                **Data Formatting**: When presenting data to the user, especially dates and times, always format them in a human-readable way (e.g., 'May 15, 2024', '02:00 PM'). Avoid showing raw or internal formats like 'PT14H'.
                **Response Format:**
                You MUST respond with a single valid JSON object: {{"thought": "...", "action": {{"tool_name": "...", "arguments": {{...}}}}}} or {{"thought": "...", "final_answer": "..."}}.

                **Example (Final Answer with formatted text):**
                ```json
                {{
                    "thought": "I have collected the data and will now format it as a markdown table for the user.",
                    "final_answer": "Here is the list of available shows:\\n\\n| Movie Title   | Theater         | Showtime            |\\n|---------------|-----------------|---------------------|\\n| The Matrix    | Cineplex        | 2025-12-27 19:00:00 |\\n| Inception     | Grand Cinema    | 2025-12-27 20:00:00 |"
                }}
                ```

                **Available Tools:**
                {json.dumps(tool_schemas, indent=2)}
                """

            max_steps = 15
            for i in range(max_steps):
                prompt_with_history = f"{system_prompt}\n\n**Conversation Trajectory:**\n" + "\n".join(trajectory)
                llm_response_str = _generate_text(prompt_with_history)
                llm_response = _parse_json_from_response(llm_response_str)

                if not llm_response:
                    step = {
                        "type": "final_answer", 
                        "content": f"Warning: Model provided a non-JSON response. Treating it as a final answer.\n\n---\n\n{llm_response_str}"
                    }
                    yield step
                    trajectory.append(f"Final Answer: {llm_response_str}")
                    break

                thought = llm_response.get("thought", "(No thought provided)")
                yield {"type": "thought", "content": thought}
                trajectory.append(f"Thought: {thought}")

                if "final_answer" in llm_response:
                    final_answer = llm_response["final_answer"]
                    yield {"type": "final_answer", "content": final_answer}
                    trajectory.append(f"Final Answer: {final_answer}")
                    break

                action = llm_response.get("action")
                if not action or "tool_name" not in action:
                    yield {"type": "error", "content": "Model did not provide a valid action or final answer."}
                    break
                
                tool_name = action["tool_name"]
                arguments = action.get("arguments", {})
                
                if tool_name in tool_schemas:
                    yield {"type": "action", "content": f"Calling tool `{tool_name}` with arguments: `{arguments}`"}
                    trajectory.append(f"Action: Call tool `{tool_name}` with arguments `{arguments}`")

                    try:
                        result = await mcp_client.call_tool(tool_name, arguments)
                        observation = str(result.data)
                        yield {"type": "observation", "content": observation}
                        trajectory.append(f"Observation: {observation}")
                    except Exception as e:
                        error_msg = f"Error calling tool '{tool_name}': {e}"
                        logging.error(error_msg)
                        yield {"type": "error", "content": error_msg}
                        trajectory.append(f"Observation: {error_msg}")
                else:
                    error_msg = f"Model chose an invalid tool: '{tool_name}'"
                    yield {"type": "error", "content": error_msg}
                    trajectory.append(f"Observation: {error_msg}")
                    break
            else:
                yield {"type": "error", "content": "Agent reached maximum steps without finding a final answer."}
    except Exception as e:
        error_msg = f"Failed to run agent step: {e}"
        logging.error(error_msg)
        yield {"type": "error", "content": error_msg}

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_prompt = request.json.get('prompt')
    if not user_prompt:
        return Response(status=400)
    
    agent_stream = run_agent_steps(user_prompt)

    def sync_generator():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                step = loop.run_until_complete(agent_stream.__anext__())
                yield f"data: {json.dumps(step)}\n\n"
        except StopAsyncIteration:
            pass
        finally:
            loop.close()

    return Response(stream_with_context(sync_generator()), mimetype='text/event-stream')

@app.route('/status', methods=['GET'])
async def status():
    try:
        async with Client('http://127.0.0.1:8000/mcp') as mcp_client:
            status_result = await mcp_client.call_tool('get_current_database')
            return Response(json.dumps(status_result.data), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({'status': 'error', 'detail': 'MCP server not reachable'}), mimetype='application/json', status=500)

@app.route('/reset', methods=['POST'])
def reset():
    global trajectory
    trajectory = []
    return "OK"

if __name__ == '__main__':
    app.run(debug=True, port=5001)
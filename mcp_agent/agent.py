import os
import asyncio
import requests
from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from dotenv import load_dotenv
import json
from mcp import Client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
import httpx


# 1. Look for a file named '.env' in the current folder, parse it,
# and load its keys directly into the system environment memory layer.
load_dotenv()

#Get strapi admin token from environment variable
STRAPI_ADMIN_TOKEN = os.getenv("STRAPI_ADMIN_TOKEN")
STRAPI_API_URL = os.getenv("STRAPI_API_URL")

async def async_talk_to_strapi(method,params : dict =None):
    """
    Asynchronously communicate with the Strapi backend using the provided method and parameters.
    Ask the Strapi backend for the list of available tools and their schemas. Then using appropriate tools, call the Strapi backend to create a new entry in the database with the provided parameters.
    
    args:
        method (str): The method to call on the Strapi backend (e.g., "tools/list" or "tools/call").
        params (dict, optional): The parameters to pass to the method. Defaults to None.
    """
    headers = {
        "Authorization": f"Bearer {STRAPI_ADMIN_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json,text/event-stream"
    }
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1
    }
    try:
# 1. Official Step: Build a dedicated asynchronous HTTPX client with your headers
        async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {STRAPI_ADMIN_TOKEN}"},
        timeout=httpx.Timeout(30.0, read=300.0),
        ) as http_client:
            
# 2. Official Step: Hand that HTTPX client into the streamable client builder
            transport = streamable_http_client(STRAPI_API_URL, http_client=http_client)
            async with Client(transport) as client:
                loop = asyncio.get_event_loop()
                if method=="tools/list":
                    mcp_response=await client.list_tools()
                    return {"tools": [tool.model_dump() for tool in mcp_response.tools]}  
                
                elif method=="tools/call":
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    
                    #Send dynamic arguments to mcp
                    mcp_response=await client.call_tool(tool_name, tool_args)
                    clean_tools = []
                    for tool in mcp_response.tools:
                            clean_tools.append({
                                "name": tool.name,
                                "description": tool.description,
                                # Force the input schema to map only to its flat inner properties
                                "inputSchema": {
                                    "type": "object",
                                    "properties": tool.inputSchema.get("properties", {}) if isinstance(tool.inputSchema, dict) else getattr(tool.inputSchema, "properties", {})
                                }
                            })
        
    # Return the clean, standard python layout to Gemini
                    return {"tools": clean_tools}
    except Exception as e:
        print(f"Error communicating with Strapi: {e}")
        return {"error": f"Failed to communicate with Strapi MCP: {str(e)}"}
research_agent = Agent(
    model='gemini-2.5-pro',
    name='research_agent',
    description='This agent is responsible for conducting research on a given topic using the google_search tool. It gathers relevant information and returns it in a structured format to the root agent.',
    instruction='You are a research agent. Your task is to gather information about the query topic provided by the user. Use the google_search tool to find relevant information and return it in a structured format to the root_agent.Ensure you return the information to the root_agent then tell it to take over',
    tools=[google_search]
)
research_agent_tool=AgentTool(agent=research_agent)
root_agent = Agent(
    model='gemini-2.5-pro',
    name='root_agent',
    description='This is the main agent responsible for managing the overall workflow and coordinating with other agents to achieve the desired outcome.',
    instruction="""You are a backend content publisher. You have direct access to a Strapi instance via async_talk_to_strapi
                    Step 1: Always call async_talk_to_strapi with method=tools/list to figure out what content fields exist.
                    Step 2: Read the returned tool schemas. Look for tools like create_entry or structural content models.
                    Step 3: Use the research_agent_tool to gather information about the query topic and wait for its response before proceeding to the next step.Make sure you wait for response from research_agent_tool before proceeding to the next step. The research_agent will provide you with relevant information about the topic, which you will use to create a detailed blog post.
                    Step 4: Write a detailed rich text blog post matching the specific prompt given by the user.
                    Step 5: Use method=tools/call with params={name: create_entry, arguments: {...}} to write it to the database of strapi using async_talk_to_strapi tool.""",
    tools=[async_talk_to_strapi, research_agent_tool],
)
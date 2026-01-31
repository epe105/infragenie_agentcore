import os
import requests
import time
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from system_prompt import INFRAGENIE_SYSTEM_PROMPT

# Load environment variables from .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, assume environment variables are set
    pass

app = BedrockAgentCoreApp()

class OAuthTokenManager:
    """Manages OAuth token lifecycle using client credentials flow"""
    
    def __init__(self, client_id: str, client_secret: str, issuer_url: str, audience: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer_url = issuer_url.rstrip('/')
        self.audience = audience
        self.token = None
        self.token_expires_at = 0
    
    def get_token(self) -> str:
        """Get a valid OAuth token, refreshing if necessary"""
        current_time = time.time()
        
        # Check if we need to refresh the token (with 60 second buffer)
        if not self.token or current_time >= (self.token_expires_at - 60):
            self._refresh_token()
        
        return self.token
    
    def _refresh_token(self):
        """Refresh the OAuth token using client credentials flow"""
        token_url = f"{self.issuer_url}/oauth/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            # Add timeout to prevent hanging during AgentCore initialization
            response = requests.post(token_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data["access_token"]
            
            # Calculate expiration time (default to 1 hour if not provided)
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in
            
            print(f"OAuth token refreshed, expires in {expires_in} seconds")
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to obtain OAuth token: {e}")

# Create MCP client for ansible-mcp with OAuth authentication
def create_ansible_mcp_client():
    """Create MCP client with OAuth authentication for ansible-mcp server"""
    
    # Try to get OAuth configuration from environment variables first
    client_id = os.getenv('ANSIBLE_MCP_CLIENT_ID')
    client_secret = os.getenv('ANSIBLE_MCP_CLIENT_SECRET')
    issuer_url = os.getenv('ANSIBLE_MCP_ISSUER_URL')
    audience = os.getenv('ANSIBLE_MCP_AUDIENCE')
    
    # If environment variables are not available, try AWS Parameter Store
    if not all([client_id, client_secret, issuer_url, audience]):
        try:
            import boto3
            ssm = boto3.client('ssm', region_name='us-east-1')  # Specify region
            
            # Get parameters from Parameter Store
            if not client_id:
                client_id = ssm.get_parameter(Name='/infragenie/oauth/client_id', WithDecryption=True)['Parameter']['Value']
            if not client_secret:
                client_secret = ssm.get_parameter(Name='/infragenie/oauth/client_secret', WithDecryption=True)['Parameter']['Value']
            if not issuer_url:
                issuer_url = ssm.get_parameter(Name='/infragenie/oauth/issuer_url')['Parameter']['Value']
            if not audience:
                audience = ssm.get_parameter(Name='/infragenie/oauth/audience')['Parameter']['Value']
                
            print("OAuth configuration loaded from AWS Parameter Store")
            
        except Exception as e:
            print(f"Failed to load from Parameter Store: {e}")
            # Fall back to checking what's missing from env vars
            missing_vars = []
            if not client_id: missing_vars.append('ANSIBLE_MCP_CLIENT_ID')
            if not client_secret: missing_vars.append('ANSIBLE_MCP_CLIENT_SECRET')
            if not issuer_url: missing_vars.append('ANSIBLE_MCP_ISSUER_URL')
            if not audience: missing_vars.append('ANSIBLE_MCP_AUDIENCE')
            
            raise ValueError(f"Missing required OAuth configuration. Environment variables: {', '.join(missing_vars)}. Parameter Store paths: /infragenie/oauth/*")
    
    # Create OAuth token manager with shorter timeout for initialization
    token_manager = OAuthTokenManager(client_id, client_secret, issuer_url, audience)
    
    def create_authenticated_client():
        """Create streamable HTTP client with fresh OAuth token"""
        token = token_manager.get_token()
        return streamablehttp_client(
            url="https://ansible-mcp.labs.presidio-labs.com/mcp",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
    
    return MCPClient(
        create_authenticated_client,
        prefix="ansible",  # Prefix tools to avoid naming conflicts
        startup_timeout=15  # Reduce timeout to avoid AgentCore initialization timeout
    )

# Initialize agent with ansible MCP tools and system prompt
# Use lazy initialization to avoid startup timeouts
def create_agent():
    """Create agent with lazy MCP client initialization"""
    try:
        ansible_mcp_client = create_ansible_mcp_client()
        return Agent(
            tools=[ansible_mcp_client],
            system_prompt=INFRAGENIE_SYSTEM_PROMPT
        )
    except Exception as e:
        print(f"Warning: Failed to initialize MCP client: {e}")
        # Fallback to agent without MCP tools
        return Agent(system_prompt=INFRAGENIE_SYSTEM_PROMPT)

# Initialize agent (will fallback gracefully if MCP fails)
agent = create_agent()

@app.entrypoint
def invoke(payload):
    """InfraGenie AI agent function with ansible-mcp integration"""
    user_message = payload.get("prompt", "Hello! I'm InfraGenie, your agentic operations assistant. How can I help you orchestrate your infrastructure today?")
    
    try:
        result = agent(user_message)
        return {"result": result.message}
    except Exception as e:
        # Fallback response if agent fails
        return {
            "result": f"InfraGenie is currently initializing. Error: {str(e)}. Please ensure OAuth environment variables are configured in the AgentCore console.",
            "status": "initialization_error"
        }

if __name__ == "__main__":
    app.run()
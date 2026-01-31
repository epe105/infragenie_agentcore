# InfraGenie AgentCore

InfraGenie is an advanced agentic operations agent deployed on AWS AgentCore, specialized in orchestrating and managing infrastructure automation through Ansible integration.

## About InfraGenies

InfraGenie serves as your intelligent infrastructure operations assistant, capable of:

- **Infrastructure Orchestration**: Automated provisioning and configuration management
- **Ansible Automation**: Direct integration with Ansible Automation Platform
- **DevOps Workflows**: Streamlined CI/CD and deployment processes  
- **Proactive Operations**: Anticipating infrastructure needs and optimizations
- **Compliance Management**: Ensuring security and regulatory compliance

## Capabilities

Through its ansible-mcp integration, InfraGenie can:
- Execute Ansible playbooks and job templates
- Manage inventories and host configurations
- Monitor job execution and retrieve detailed logs
- Orchestrate complex multi-step infrastructure workflows
- Provide intelligent recommendations for infrastructure optimization

## Setup

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Set the required OAuth configuration:
- `ANSIBLE_MCP_CLIENT_ID`: OAuth Client ID from Auth0
- `ANSIBLE_MCP_CLIENT_SECRET`: OAuth Client Secret from Auth0
- `ANSIBLE_MCP_ISSUER_URL`: Auth0 issuer URL
- `ANSIBLE_MCP_AUDIENCE`: OAuth audience

**Important**: All four environment variables are required. No default values are provided for security reasons.

### OAuth Configuration

The agent uses OAuth 2.0 Client Credentials flow to authenticate with the ansible-mcp server:

1. **Auth0 Configuration**:
   - Issuer: 
   - Audience: 
   - Grant Type: Client Credentials

2. **Token Management**:
   - Tokens are automatically obtained and refreshed as needed
   - 60-second buffer before expiration to ensure valid tokens
   - Automatic retry on token refresh failures

3. **Environment Setup**:
   ```bash
   export ANSIBLE_MCP_CLIENT_ID="your_client_id"
   export ANSIBLE_MCP_CLIENT_SECRET="your_client_secret"
   ```

### MCP Integration

This agent integrates with an ansible-mcp server hosted at:
- URL: 
- Transport: Streamable HTTP with OAuth 2.0 authentication
- Tools: Prefixed with `ansible_` to avoid naming conflicts

The ansible-mcp server provides tools for Ansible Automation Platform integration, allowing the agent to:
- Execute Ansible playbooks
- Manage inventory
- Access Ansible Automation Platform APIs

## Project Structure

- `infragenie_agent.py` - Main agent implementation with OAuth and MCP integration
- `system_prompt.py` - InfraGenie's system prompt and identity configuration
- `.env.example` - Template for environment variables
- `requirements.txt` - Python dependencies
- `.bedrock_agentcore.yaml` - AgentCore deployment configuration

## Customization

### System Prompt
InfraGenie's personality and capabilities are defined in `system_prompt.py`. You can modify this file to:
- Adjust InfraGenie's communication style
- Add new capability descriptions
- Update operational guidelines
- Customize responses for specific use cases

The system prompt is automatically loaded when the agent starts.

## Deployment

This agent is designed to be deployed on AWS Bedrock AgentCore. The `.bedrock_agentcore.yaml` configuration file contains the deployment settings.

### AgentCore Environment Variables

When deploying to AgentCore, ensure the OAuth credentials are available as environment variables in your deployment configuration.

## Troubleshooting & Additional Configuration

### OAuth Configuration via AWS Parameter Store

If you encounter issues with OAuth authentication or need to recreate the setup in a new AWS region, follow these steps:

#### 1. Create SSM Parameters

The agent reads OAuth configuration from AWS Systems Manager Parameter Store. Create the following parameters:

```bash
# Create OAuth parameters (replace with your actual values)
aws ssm put-parameter --name "/infragenie/oauth/client_id" --value "YOUR_CLIENT_ID" --type "SecureString"
aws ssm put-parameter --name "/infragenie/oauth/client_secret" --value "YOUR_CLIENT_SECRET" --type "SecureString"  
aws ssm put-parameter --name "/infragenie/oauth/issuer_url" --value "YOUR_AUTH0_ISSUER_URL" --type "String"
aws ssm put-parameter --name "/infragenie/oauth/audience" --value "YOUR_OAUTH_AUDIENCE" --type "String"
```

#### 2. IAM Permissions

The AgentCore execution role needs permission to read from Parameter Store. Add the following policy:

```bash
# Attach SSM read permissions to the AgentCore execution role
aws iam attach-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-us-east-1-XXXXXXXXX \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

**Note**: Replace `AmazonBedrockAgentCoreSDKRuntime-us-east-1-XXXXXXXXX` with your actual AgentCore execution role name from `.bedrock_agentcore.yaml`.

#### 3. Parameter Store Path Structure

The agent expects parameters at these exact paths:
- `/infragenie/oauth/client_id` (SecureString)
- `/infragenie/oauth/client_secret` (SecureString)  
- `/infragenie/oauth/issuer_url` (String)
- `/infragenie/oauth/audience` (String)

#### 4. Verification

After configuration, check the CloudWatch logs for successful initialization:

```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR_AGENT_ID-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs" \
  --since 5m
```

Look for these success messages:
- `OAuth configuration loaded from AWS Parameter Store`
- `OAuth token refreshed, expires in XXXXX seconds`

#### 5. Common Issues

**Parameter Store Access Denied**: Ensure the AgentCore execution role has `ssm:GetParameter` permissions.

**OAuth Token Failures**: Verify your Auth0 client credentials and audience configuration.

**MCP Connection Timeouts**: Check that your ansible-mcp server is accessible and OAuth credentials are correct.

### Security Notes

- OAuth credentials are stored as SecureString parameters in Parameter Store
- The agent automatically handles token refresh (24-hour expiration)
- No sensitive credentials are stored in code or configuration files
- All authentication is handled through AWS IAM and Auth0 OAuth flows
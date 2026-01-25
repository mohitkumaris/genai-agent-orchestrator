import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration settings.
    """
    model_config = SettingsConfigDict(env_prefix="GENAI_ORCHESTRATOR_", env_file=".env", extra="ignore")

    # Service Info
    service_name: str = "genai-agent-orchestrator"
    environment: str = "local"
    log_level: str = "INFO"
    
    # API 
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # LLM (Azure OpenAI)
    azure_openai_api_key: str = "placeholder-key"
    azure_openai_endpoint: str = "https://placeholder.openai.azure.com"
    azure_openai_api_version: str = "2023-05-15"
    azure_openai_deployment_name: str = "gpt-4"
    
    # Paths
    base_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompts_dir: str = os.path.join(base_dir, "prompts")

settings = Settings()

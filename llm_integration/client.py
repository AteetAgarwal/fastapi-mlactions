# src/llm_client.py
from openai import AzureOpenAI
from crewai.llm import LLM
import os
from dotenv import load_dotenv

load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path="/home/tithi/Lutron.MLActionsApi/Lutron.MLActionsApi/config/.env")

api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_API_VERSION")
azure_endpoint = os.getenv("AZURE_API_BASE")
AZURE_OPENAI_MODEL_NAME="azure/gpt-4o-mini"
TEMPERATURE = 0.1



logger.info("Azure OpenAI credentials loaded successfully.")


def get_azure_crew_llm() -> LLM:
    """
    Set up and return a CrewAI LLM instance configured with Azure OpenAI API.

    :return: An LLM object configured with Azure OpenAI.
    """
    try:

        llm_instance = LLM(
            model=AZURE_OPENAI_MODEL_NAME,
            api_version=api_version,
            temperature=TEMPERATURE,
        )
        logger.info("CrewAI LLM initialized successfully.")
        return llm_instance
    except Exception as e:
        logger.error(f"Error initializing CrewAI LLM: {e}")
        raise


def init_azureopenai() -> AzureOpenAI:
    """
    Initialize and return an Azure OpenAI client.

    :return: AzureOpenAI client instance.
    """
    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )
        logger.info("Azure OpenAI client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Error initializing Azure OpenAI client: {e}")
        raise


import os
from dataclasses import dataclass
from streamlit import secrets
from typing import Dict, Any
import streamlit as st
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Application configuration"""
    n8n_webhook_url: str
    n8n_submit_url: str
    n8n_status_url: str
    n8n_check_images_url: str
    n8n_select_image_url: str
    n8n_base_url: str
    elevenlabs_api_key: str
    elevenlabs_voice_endpoint: str
    max_file_size_mb: int
    supported_image_types: list
    supported_audio_types: list
    polling_interval: int
    video_polling_interval: int
    max_polling_attempts: int
    request_timeout: int

def load_config() -> Config:
    """Load configuration from environment variables or Streamlit secrets"""
    
    # Default values
    defaults = {
        "N8N_BASE_URL": "https://n8n.izaan.space",
        "ELEVENLABS_API_KEY": "sk_47b068cc20e46b199461017ae1ee540751517f615975d330",
        "MAX_FILE_SIZE_MB": "10",
        "POLLING_INTERVAL": "5",
        "VIDEO_POLLING_INTERVAL": "30",  # 30 seconds for video status checks
        "MAX_POLLING_ATTEMPTS": "120",   # Max 60 minutes (120 * 30 seconds)
        "REQUEST_TIMEOUT": "60"
    }
    
    config_values = {}
    
    # Try to load from Streamlit secrets first
    try:
        if hasattr(st, 'secrets') and st.secrets:
            logger.info("Loading configuration from Streamlit secrets")
            for key in defaults.keys():
                try:
                    # Try nested access first (secrets["default"][KEY])
                    if "default" in st.secrets and key in st.secrets["default"]:
                        config_values[key] = st.secrets["default"][key]
                    # Try direct access (secrets[KEY])
                    elif key in st.secrets:
                        config_values[key] = st.secrets[key]
                    else:
                        config_values[key] = defaults[key]
                        logger.warning(f"Using default value for {key}")
                except Exception as e:
                    logger.warning(f"Error accessing secret {key}: {e}, using default")
                    config_values[key] = defaults[key]
        else:
            logger.info("Streamlit secrets not available, using environment variables")
            raise Exception("No secrets")
    except Exception:
        # Fallback to environment variables
        logger.info("Loading configuration from environment variables")
        for key in defaults.keys():
            config_values[key] = os.getenv(key, defaults[key])
    
    # Build URLs
    base_url = config_values["N8N_BASE_URL"]
    
    # Common n8n webhook URL patterns
    webhook_patterns = [
        f"{base_url}/webhook-test/hedra_auto",
        f"{base_url}/webhook/hedra_auto", 
        f"{base_url}/webhook-test/hedra-auto",
        f"{base_url}/api/webhooks/hedra_auto"
    ]
    
    # Use the first pattern as default, but we'll test them
    webhook_url = webhook_patterns[1]
    
    config = Config(
        n8n_webhook_url=webhook_url,
        n8n_submit_url  = secrets["N8N_SUBMIT_URL"],
        n8n_status_url  = secrets["N8N_STATUS_URL"],
        n8n_check_images_url=f"{base_url}/webhook/check-images",
        n8n_select_image_url=f"{base_url}/webhook/select-image",
        n8n_base_url=base_url,
        elevenlabs_api_key=config_values["ELEVENLABS_API_KEY"],
        elevenlabs_voice_endpoint="https://api.elevenlabs.io/v1/voices",
        max_file_size_mb=int(config_values["MAX_FILE_SIZE_MB"]),
        supported_image_types=["png", "jpg", "jpeg"],
        supported_audio_types=["mp3", "wav"],
        polling_interval=int(config_values["POLLING_INTERVAL"]),
        video_polling_interval=int(config_values["VIDEO_POLLING_INTERVAL"]),
        max_polling_attempts=int(config_values["MAX_POLLING_ATTEMPTS"]),
        request_timeout=int(config_values["REQUEST_TIMEOUT"]),
    )
    
    logger.info(f"Configuration loaded successfully")
    logger.info(f"N8N Base URL: {config.n8n_base_url}")
    logger.info(f"Video polling interval: {config.video_polling_interval}s")
    logger.info(f"Max polling attempts: {config.max_polling_attempts}")
    
    return config
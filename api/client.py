from typing import Dict, Any, Optional, Tuple
import requests
import logging
from config.settings import Config
import time

logger = logging.getLogger(__name__)

class APIClient:
    """Handles all API communications"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        # Log configuration status
        logger.info(f"APIClient initialized with ElevenLabs API key: {'Yes' if config.elevenlabs_api_key else 'No'}")
    
    def get_elevenlabs_voices(self) -> Optional[Dict[str, str]]:
        """Fetch available voices from ElevenLabs"""
        if not self.config.elevenlabs_api_key or self.config.elevenlabs_api_key == "None":
            logger.error("ElevenLabs API key not configured or is None")
            return None
        
        headers = {"xi-api-key": self.config.elevenlabs_api_key}
        
        try:
            logger.info("Fetching ElevenLabs voices...")
            response = self.session.get(
                self.config.elevenlabs_voice_endpoint,
                headers=headers,
                timeout=10
            )
            
            logger.info(f"ElevenLabs API response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error("ElevenLabs API key is invalid (401 Unauthorized)")
                return None
            
            response.raise_for_status()
            
            voice_data = response.json()
            voices = {v['name']: v['voice_id'] for v in voice_data.get('voices', [])}
            logger.info(f"Successfully fetched {len(voices)} voices from ElevenLabs")
            return voices
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch ElevenLabs voices: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching voices: {str(e)}")
            return None
    
    def submit_job(self, data: Dict[str, Any], files: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Submit job to n8n webhook"""
        try:
            logger.info(f"Submitting job to {self.config.n8n_webhook_url}")
            logger.info(f"Job data keys: {list(data.keys())}")
            logger.info(f"Files: {list(files.keys())}")
            
            response = self.session.post(
                self.config.n8n_webhook_url,
                data=data,
                files=files,
                timeout=self.config.request_timeout
            )
            
            logger.info(f"Job submission response status: {response.status_code}")
            
            if response.status_code == 200:
                result = None
                if response.text.strip():
                    try:
                        result = response.json()
                    except ValueError:
                        result = {"response": response.text}
                
                logger.info("Job submitted successfully")
                return True, result, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Job submission failed: {error_msg}")
                return False, None, error_msg
                
        except requests.Timeout:
            error_msg = "Request timed out. Please try again."
            logger.error(error_msg)
            return False, None, error_msg
        except requests.ConnectionError:
            error_msg = "Connection error. Please check your internet connection."
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def check_images_status(self, session_id: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Check if images are ready for selection"""
        try:
            url = f"{self.config.n8n_check_images_url}/{session_id}"
            logger.info(f"Checking images status: {url}")
            
            response = self.session.get(url, timeout=10)
            
            logger.info(f"Images status check response: {response.status_code}")
            
            if response.status_code == 200:
                return True, response.json(), None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, None, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def select_image(self, session_id: str, selected_image_id: str) -> tuple[bool, Optional[str]]:
        """Send image selection to n8n"""
        try:
            payload = {
                "session_id": session_id,
                "selected_image_id": selected_image_id
            }
            
            logger.info(f"Selecting image: {selected_image_id} for session: {session_id}")
            
            response = self.session.post(
                self.config.n8n_select_image_url,
                json=payload,
                timeout=self.config.request_timeout
            )
            
            logger.info(f"Image selection response: {response.status_code}")
            
            if response.status_code == 200:
                return True, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Image selection failed: {error_msg}")
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def __del__(self):
        """Clean up session"""
        if hasattr(self, 'session'):
            self.session.close()


    def approve_audio(self, session_id: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Approve generated audio and continue with video generation"""
        try:
            payload = {"session_id": session_id, "approved": True}
            
            response = self.session.post(
                f"{self.config.n8n_base_url}/webhook/approve-audio",
                json=payload,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json() if response.text.strip() else None
                return True, result, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, None, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def regenerate_audio(self, session_id: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Request audio regeneration"""
        try:
            payload = {"session_id": session_id}
            
            response = self.session.post(
                f"{self.config.n8n_base_url}/webhook/regenerate-audio",
                json=payload,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json() if response.text.strip() else None
                return True, result, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, None, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def check_video_status(
        self, generation_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Check video generation status using n8n proxy."""
        try:
            url = f"{self.config.n8n_status_url}/{generation_id}"
            logger.info(f"Polling video status at {url}")
            response = self.session.get(url, timeout=self.config.request_timeout)
            if response.status_code == 200:
                return True, response.json(), None
            return False, None, f"HTTP {response.status_code}: {response.text}"
        except requests.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)
            return False, None, error_msg
from typing import Optional
import logging
from config.settings import Config

logger = logging.getLogger(__name__)

class FileValidator:
    """Validates uploaded files"""
    
    def __init__(self, config: Config):
        self.config = config
        self.max_size_bytes = config.max_file_size_mb * 1024 * 1024
    
    def validate_image(self, image_file) -> Optional[str]:
        """Validate image file"""
        if not image_file:
            return "No image file provided"
        
        # Check file extension
        if hasattr(image_file, 'name'):
            extension = image_file.name.split('.')[-1].lower()
            if extension not in self.config.supported_image_types:
                return f"Unsupported image format. Supported: {', '.join(self.config.supported_image_types)}"
        
        # Check file size
        if hasattr(image_file, 'size') and image_file.size:
            if image_file.size > self.max_size_bytes:
                return f"Image file too large. Maximum size: {self.config.max_file_size_mb}MB"
        
        return None
    
    def validate_audio(self, audio_file) -> Optional[str]:
        """Validate audio file"""
        if not audio_file:
            return None  # Audio is optional
        
        # Check file extension
        if hasattr(audio_file, 'name'):
            extension = audio_file.name.split('.')[-1].lower()
            if extension not in self.config.supported_audio_types:
                return f"Unsupported audio format. Supported: {', '.join(self.config.supported_audio_types)}"
        
        # Check file size
        if hasattr(audio_file, 'size') and audio_file.size:
            if audio_file.size > self.max_size_bytes:
                return f"Audio file too large. Maximum size: {self.config.max_file_size_mb}MB"
        
        return None
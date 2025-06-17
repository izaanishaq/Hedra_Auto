import logging
import time
from typing import Dict, Any, Optional, Tuple
from config.settings import Config
from utils.session_manager import SessionManager, JobStatus
from api.client import APIClient
from utils.validators import FileValidator

logger = logging.getLogger(__name__)

class JobManager:
    """Manages job lifecycle and state with smart polling"""
    
    def __init__(self, config: Config, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager
        self.api_client = APIClient(config)
        self.file_validator = FileValidator(config)
    
    def submit_job(self, form_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Submit a new job"""
        try:
            # Validate inputs
            validation_error = self._validate_job_data(form_data)
            if validation_error:
                return False, validation_error
            
            # Prepare files and data
            files, data = self._prepare_submission_data(form_data)
            
            # Submit to API
            success, result, error = self.api_client.submit_job(data, files)
            
            if success:
                self.session_manager.current_session_id = self.session_manager.session_id
                self.session_manager.manual_mode_active = form_data.get('manual_mode', False)
                
                if form_data.get('manual_mode'):
                    # Check if images and audio are returned directly in response
                    if result and result.get('images'):
                        self.session_manager.generated_images = result.get('images', [])
                        # Store audio data for approval
                        if result.get('audio'):
                            self.session_manager.generated_audio_data = result.get('audio')
                        self.session_manager.job_status = JobStatus.SELECTING_IMAGE
                    else:
                        self.session_manager.job_status = JobStatus.WAITING_FOR_IMAGES
                else:
                    # For non-manual mode, check if video generation started
                    if result and result.get('generation_id'):
                        self.session_manager.generation_id = result.get('generation_id')
                        self.session_manager.job_status = JobStatus.PROCESSING_FINAL
                        self.session_manager.video_status_message = "Video generation started..."
                    else:
                        self.session_manager.job_status = JobStatus.PROCESSING_FINAL
                
                return True, None
            else:
                self.session_manager.error_message = error
                self.session_manager.job_status = JobStatus.ERROR
                return False, error
                
        except Exception as e:
            error_msg = f"Job submission failed: {str(e)}"
            logger.error(error_msg)
            self.session_manager.error_message = error_msg
            self.session_manager.job_status = JobStatus.ERROR
            return False, error_msg
    
    def select_image(self, image_id: str) -> Tuple[bool, Optional[str]]:
        """Select an image and continue processing"""
        if not self.session_manager.current_session_id:
            return False, "No active session"
        
        # Send selection to n8n for continued processing
        success, result, error = self.api_client.select_image(
            self.session_manager.current_session_id,
            image_id
        )
        
        if success:
            if self.session_manager.manual_mode_active:
                # In manual mode, wait for audio approval
                self.session_manager.job_status = JobStatus.AWAITING_AUDIO_APPROVAL
            else:
                # In non-manual mode, proceed directly to final processing
                self.session_manager.job_status = JobStatus.PROCESSING_FINAL
                self.session_manager.video_status_message = "Starting video generation..."
                if result and result.get('generation_id'):
                    self.session_manager.generation_id = result.get('generation_id')
            
            self.session_manager.generated_images = []
            return True, None
        else:
            self.session_manager.error_message = error
            return False, error
    
    def approve_audio(self) -> Tuple[bool, Optional[str]]:
        """Approve the generated audio and continue with video generation"""
        if not self.session_manager.current_session_id:
            return False, "No active session"
        
        success, result, error = self.api_client.approve_audio(
            self.session_manager.current_session_id
        )
        
        if success:
            self.session_manager.job_status = JobStatus.PROCESSING_FINAL
            self.session_manager.video_status_message = "Audio approved, starting video generation..."
            if result and result.get('generation_id'):
                self.session_manager.generation_id = result.get('generation_id')
            return True, None
        else:
            self.session_manager.error_message = error
            return False, error
    
    def regenerate_audio(self) -> Tuple[bool, Optional[str]]:
        """Request audio regeneration"""
        if not self.session_manager.current_session_id:
            return False, "No active session"
        
        success, result, error = self.api_client.regenerate_audio(
            self.session_manager.current_session_id
        )
        
        if success:
            # Update audio data when regenerated
            if result and result.get('audio'):
                self.session_manager.generated_audio_data = result.get('audio')
            return True, None
        else:
            self.session_manager.error_message = error
            return False, error
    
    def check_video_status(self) -> bool:
        """Check video generation status with smart polling"""
        if not self.session_manager.generation_id:
            logger.debug("No generation ID available for video status check")
            return False
        
        # Check if we should poll based on interval
        if not self.session_manager.should_check_video_status(self.config.video_polling_interval):
            return False
        
        # Check if we've exceeded max attempts
        if self.session_manager.video_polling_attempts >= self.config.max_polling_attempts:
            logger.warning(f"Max polling attempts ({self.config.max_polling_attempts}) reached")
            self.session_manager.job_status = JobStatus.ERROR
            self.session_manager.error_message = f"Video generation timed out after {self.config.max_polling_attempts} attempts"
            return False
        
        # Update polling state
        self.session_manager.last_video_check_time = time.time()
        self.session_manager.increment_video_polling_attempts()
        
        logger.info(f"Checking video status (attempt {self.session_manager.video_polling_attempts}/{self.config.max_polling_attempts})")
        
        success, data, error = self.api_client.check_video_status(
            self.session_manager.generation_id
        )
        
        if success and data:
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0.0)
            
            # Update progress and status message
            self.session_manager.video_progress = progress
            
            if status == 'complete':
                self.session_manager.job_status = JobStatus.COMPLETED
                self.session_manager.final_video_data = data
                self.session_manager.video_status_message = "Video generation completed!"
                logger.info("Video generation completed successfully")
                return True
            elif status == 'error':
                self.session_manager.job_status = JobStatus.ERROR
                error_msg = data.get('error_message', 'Video generation failed')
                self.session_manager.error_message = error_msg
                self.session_manager.video_status_message = f"Error: {error_msg}"
                logger.error(f"Video generation failed: {error_msg}")
                return False
            elif status in ['processing', 'finalizing', 'queued', 'pending']:
                # Update status message based on current status
                status_messages = {
                    'queued': 'Video generation queued...',
                    'pending': 'Video generation pending...',
                    'processing': f'Video generation in progress... ({progress:.1%})',
                    'finalizing': 'Finalizing video generation...'
                }
                self.session_manager.video_status_message = status_messages.get(
                    status, 
                    f'Video generation {status}... ({progress:.1%})'
                )
                
                # Estimate time remaining
                elapsed_minutes = (self.session_manager.video_polling_attempts * self.config.video_polling_interval) / 60
                max_minutes = (self.config.max_polling_attempts * self.config.video_polling_interval) / 60
                
                logger.info(f"Video status: {status}, Progress: {progress:.1%}, "
                          f"Elapsed: {elapsed_minutes:.1f}min/{max_minutes:.1f}min")
                return False
            else:
                logger.warning(f"Unknown video status: {status}")
                self.session_manager.video_status_message = f"Unknown status: {status}"
                return False
        
        elif error:
            logger.error(f"Video status check failed: {error}")
            # Don't fail immediately on API errors, just log and continue polling
            self.session_manager.video_status_message = f"Status check failed: {error}"
            return False
        
        return False
    
    def get_video_progress_info(self) -> Dict[str, Any]:
        """Get detailed video generation progress information"""
        polling_info = self.session_manager.get_polling_info()
        
        elapsed_time = polling_info['attempts'] * self.config.video_polling_interval
        max_time = self.config.max_polling_attempts * self.config.video_polling_interval
        
        return {
            'status': self.session_manager.job_status.value,
            'progress': polling_info['progress'],
            'status_message': polling_info['status_message'],
            'attempts': polling_info['attempts'],
            'max_attempts': self.config.max_polling_attempts,
            'elapsed_time_seconds': elapsed_time,
            'max_time_seconds': max_time,
            'elapsed_time_formatted': self._format_duration(elapsed_time),
            'max_time_formatted': self._format_duration(max_time),
            'polling_interval': self.config.video_polling_interval,
            'generation_id': self.session_manager.generation_id
        }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def check_images_ready(self) -> bool:
        """Check if images are ready for selection"""
        # This method is for fallback/debugging - images should come directly in response
        return False
    
    def reset_job(self):
        """Reset current job"""
        self.session_manager.reset_job()
    
    def get_elevenlabs_voices(self) -> Optional[Dict[str, str]]:
        """Get available ElevenLabs voices"""
        return self.api_client.get_elevenlabs_voices()
    
    def _validate_job_data(self, form_data: Dict[str, Any]) -> Optional[str]:
        """Validate job submission data"""
        if not form_data.get('image_file'):
            return "Image file is required"
        
        if not form_data.get('script_text', '').strip():
            return "Script text is required"
        
        # Validate image file
        image_error = self.file_validator.validate_image(form_data['image_file'])
        if image_error:
            return image_error
        
        # Validate audio file if provided
        if form_data.get('audio_file'):
            audio_error = self.file_validator.validate_audio(form_data['audio_file'])
            if audio_error:
                return audio_error
        
        return None
    
    def _prepare_submission_data(self, form_data: Dict[str, Any]) -> Tuple[Dict, Dict]:
        """Prepare files and data for submission"""
        files = {}
        
        # Prepare image file
        image_file = form_data['image_file']
        image_file.seek(0)
        files['image'] = (image_file.name, image_file.getvalue(), image_file.type)
        
        # Prepare audio file if provided
        if form_data.get('audio_file'):
            audio_file = form_data['audio_file']
            audio_file.seek(0)
            files['audio'] = (audio_file.name, audio_file.getvalue(), audio_file.type)
        
        # Prepare form data
        data = {
            "session_id": self.session_manager.session_id,
            "script": form_data['script_text'],
            "manual_mode": str(form_data.get('manual_mode', False)).lower(),
            "use_elevenlabs": str(form_data.get('use_elevenlabs', False)).lower()
        }
        
        # Add ElevenLabs settings if applicable
        if form_data.get('use_elevenlabs') and form_data.get('voice_id'):
            elevenlabs_data = {
                "voice_id": form_data.get('voice_id', ''),
                "stability": str(form_data.get('stability', 0.5)),
                "similarity_boost": str(form_data.get('similarity', 0.5)),
                "style": str(form_data.get('style', 0.5))
            }
            data.update(elevenlabs_data)
        else:
            # If not using elevenlabs, we still need a voice_id for the n8n workflow filename
            # Use session_id as fallback
            data["voice_id"] = self.session_manager.session_id[:8]  # Use first 8 chars of session ID
        
        return files, data
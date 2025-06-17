import streamlit as st
import uuid
import time
from typing import Optional, List, Dict, Any
from enum import Enum

class JobStatus(Enum):
    """Job status enumeration"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_IMAGES = "waiting_for_images"
    SELECTING_IMAGE = "selecting_image"
    AWAITING_AUDIO_APPROVAL = "awaiting_audio_approval"
    PROCESSING_FINAL = "processing_final"
    COMPLETED = "completed"
    ERROR = "error"

class SessionManager:
    """Manages Streamlit session state"""
    
    def __init__(self):
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'session_id': str(uuid.uuid4()),
            'job_status': JobStatus.IDLE,
            'generated_images': [],
            'generated_audio_data': None,
            'final_video_data': None,
            'generation_id': None,
            'current_session_id': None,
            'manual_mode_active': False,
            'last_check_time': 0,
            'last_video_check_time': 0,
            'video_polling_attempts': 0,
            'video_progress': 0.0,
            'video_status_message': '',
            'error_message': None,
            'job_result': None,
            'polling_active': False
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    @property
    def session_id(self) -> str:
        return st.session_state.session_id
    
    @property
    def job_status(self) -> JobStatus:
        return st.session_state.job_status
    
    @job_status.setter
    def job_status(self, status: JobStatus):
        st.session_state.job_status = status
        # Reset polling when status changes
        if status == JobStatus.PROCESSING_FINAL:
            st.session_state.polling_active = True
            st.session_state.video_polling_attempts = 0
            st.session_state.last_video_check_time = 0
        elif status in [JobStatus.COMPLETED, JobStatus.ERROR]:
            st.session_state.polling_active = False
    
    @property
    def generated_images(self) -> List[Dict[str, Any]]:
        return st.session_state.generated_images
    
    @generated_images.setter
    def generated_images(self, images: List[Dict[str, Any]]):
        st.session_state.generated_images = images
    
    @property
    def generated_audio_data(self) -> Optional[Dict[str, Any]]:
        return st.session_state.generated_audio_data
    
    @generated_audio_data.setter
    def generated_audio_data(self, data: Optional[Dict[str, Any]]):
        st.session_state.generated_audio_data = data
    
    @property
    def final_video_data(self) -> Optional[Dict[str, Any]]:
        return st.session_state.final_video_data
    
    @final_video_data.setter
    def final_video_data(self, data: Optional[Dict[str, Any]]):
        st.session_state.final_video_data = data
    
    @property
    def generation_id(self) -> Optional[str]:
        return st.session_state.generation_id
    
    @generation_id.setter
    def generation_id(self, gen_id: Optional[str]):
        st.session_state.generation_id = gen_id
    
    @property
    def current_session_id(self) -> Optional[str]:
        return st.session_state.current_session_id
    
    @current_session_id.setter
    def current_session_id(self, session_id: Optional[str]):
        st.session_state.current_session_id = session_id
    
    @property
    def manual_mode_active(self) -> bool:
        return st.session_state.manual_mode_active
    
    @manual_mode_active.setter
    def manual_mode_active(self, active: bool):
        st.session_state.manual_mode_active = active
    
    @property
    def last_check_time(self) -> float:
        return st.session_state.last_check_time
    
    @last_check_time.setter
    def last_check_time(self, timestamp: float):
        st.session_state.last_check_time = timestamp
    
    @property
    def last_video_check_time(self) -> float:
        return st.session_state.last_video_check_time
    
    @last_video_check_time.setter
    def last_video_check_time(self, timestamp: float):
        st.session_state.last_video_check_time = timestamp
    
    @property
    def video_polling_attempts(self) -> int:
        return st.session_state.video_polling_attempts
    
    @video_polling_attempts.setter
    def video_polling_attempts(self, attempts: int):
        st.session_state.video_polling_attempts = attempts
    
    @property
    def video_progress(self) -> float:
        return st.session_state.video_progress
    
    @video_progress.setter
    def video_progress(self, progress: float):
        st.session_state.video_progress = progress
    
    @property
    def video_status_message(self) -> str:
        return st.session_state.video_status_message
    
    @video_status_message.setter
    def video_status_message(self, message: str):
        st.session_state.video_status_message = message
    
    @property
    def error_message(self) -> Optional[str]:
        return st.session_state.error_message
    
    @error_message.setter
    def error_message(self, message: Optional[str]):
        st.session_state.error_message = message
    
    @property
    def job_result(self) -> Optional[Dict[str, Any]]:
        return st.session_state.job_result
    
    @job_result.setter
    def job_result(self, result: Optional[Dict[str, Any]]):
        st.session_state.job_result = result
    
    @property
    def polling_active(self) -> bool:
        return st.session_state.polling_active
    
    @polling_active.setter
    def polling_active(self, active: bool):
        st.session_state.polling_active = active
    
    def should_check_video_status(self, polling_interval: int) -> bool:
        """Check if it's time to poll video status"""
        if not self.polling_active or not self.generation_id:
            return False
        
        current_time = time.time()
        return (current_time - self.last_video_check_time) >= polling_interval
    
    def increment_video_polling_attempts(self):
        """Increment video polling attempts counter"""
        st.session_state.video_polling_attempts += 1
    
    def get_polling_info(self) -> Dict[str, Any]:
        """Get current polling information"""
        return {
            'attempts': self.video_polling_attempts,
            'progress': self.video_progress,
            'status_message': self.video_status_message,
            'last_check': self.last_video_check_time,
            'active': self.polling_active
        }
    
    def reset_job(self):
        """Reset job-related session state"""
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.job_status = JobStatus.IDLE
        st.session_state.generated_images = []
        st.session_state.generated_audio_data = None
        st.session_state.final_video_data = None
        st.session_state.generation_id = None
        st.session_state.current_session_id = None
        st.session_state.manual_mode_active = False
        st.session_state.last_check_time = 0
        st.session_state.last_video_check_time = 0
        st.session_state.video_polling_attempts = 0
        st.session_state.video_progress = 0.0
        st.session_state.video_status_message = ''
        st.session_state.error_message = None
        st.session_state.job_result = None
        st.session_state.polling_active = False
    
    def is_job_active(self) -> bool:
        """Check if there's an active job"""
        return self.job_status not in [JobStatus.IDLE, JobStatus.COMPLETED, JobStatus.ERROR]
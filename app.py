import streamlit as st
import os
import sys
from pathlib import Path
from components.ui_components import render_main_interface
from components.job_manager import JobManager
from utils.session_manager import SessionManager
from config.settings import load_config
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables if not set (temporary solution)
if not os.getenv('ELEVENLABS_API_KEY'):
    os.environ['ELEVENLABS_API_KEY'] = ''
if not os.getenv('N8N_BASE_URL'):
    os.environ['N8N_BASE_URL'] = 'https://n8n.i.space/webhook-test'

def main():
    """Main Streamlit application"""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize session manager
        session_manager = SessionManager()
        
        # Initialize job manager
        job_manager = JobManager(config, session_manager)
        
        # Set page config
        st.set_page_config(
            page_title="AI Reel Automation",
            page_icon="🎬",
            
            initial_sidebar_state="collapsed"
        )
        
        # Render main interface
        render_main_interface(job_manager, session_manager)
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An unexpected error occurred. Please refresh the page.")

if __name__ == "__main__":
    main()

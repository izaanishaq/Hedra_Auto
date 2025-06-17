import streamlit as st
import time
from typing import Dict, Any, Optional
from components.job_manager import JobManager
from utils.session_manager import SessionManager, JobStatus
from streamlit.components.v1 import html



def render_main_interface(job_manager: JobManager, session_manager: SessionManager):
    """Render the main application interface"""
    st.title("🎬 AI Reel Automation")
    
    # Show status banner
    _render_status_banner(session_manager)
    
    # Show reset button if job is active
    if session_manager.is_job_active():
        if st.button("🔄 Start New Job", help="Reset and start a new job"):
            job_manager.reset_job()
            st.rerun()
    
    # Auto-check for images if waiting
    if session_manager.job_status == JobStatus.WAITING_FOR_IMAGES:
        if job_manager.check_images_ready():
            st.rerun()
    
    # Auto-check for video status if processing final with smart polling
    if session_manager.job_status == JobStatus.PROCESSING_FINAL:
        if job_manager.check_video_status():
            st.rerun()
        else:
            # Show progress even if not complete
            _render_video_generation_progress(job_manager, session_manager)
            # Auto-refresh the page to continue polling
            time.sleep(2)
            st.rerun()
    
    # Render appropriate interface based on job status
    if session_manager.job_status == JobStatus.SELECTING_IMAGE:
        _render_image_selection(job_manager, session_manager)
    elif session_manager.job_status == JobStatus.AWAITING_AUDIO_APPROVAL:
        _render_audio_approval(job_manager, session_manager)
    elif session_manager.job_status == JobStatus.PROCESSING_FINAL:
        _render_video_generation_progress(job_manager, session_manager)
    elif session_manager.job_status == JobStatus.COMPLETED:
        _render_completion(session_manager)
    elif not session_manager.is_job_active():
        _render_job_form(job_manager, session_manager)
    
    # Show debug info if enabled
    if st.checkbox("🐛 Show Debug Info", help="Show technical details for troubleshooting"):
        _render_debug_info(session_manager, job_manager)
    
    # Show help
    _render_help_section()

def _render_video_generation_progress(job_manager: JobManager, session_manager: SessionManager):
    """Render video generation progress with detailed information"""
    st.subheader("🎬 Video Generation in Progress")
    
    progress_info = job_manager.get_video_progress_info()
    
    # Main progress bar
    progress_value = progress_info['progress']
    st.progress(progress_value, text=f"Progress: {progress_value:.1%}")
    
    # Status message
    st.info(progress_info['status_message'])
    
    # Detailed progress information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Status Checks",
            f"{progress_info['attempts']}/{progress_info['max_attempts']}",
            help="Number of status checks performed"
        )
    
    with col2:
        st.metric(
            "Elapsed Time",
            progress_info['elapsed_time_formatted'],
            help="Time since video generation started"
        )
    
    with col3:
        # Calculate estimated time remaining
        if progress_info['progress'] > 0:
            elapsed_seconds = progress_info['elapsed_time_seconds']
            estimated_total_seconds = elapsed_seconds / progress_info['progress']
            remaining_seconds = max(0, estimated_total_seconds - elapsed_seconds)
            remaining_formatted = job_manager._format_duration(int(remaining_seconds))
        else:
            remaining_formatted = "Calculating..."
            
        st.metric(
            "Est. Time Left",
            remaining_formatted,
            help="Estimated time remaining for video generation"
        )
    
    # Additional info in expandable section
    with st.expander("📊 Generation Details"):
        st.write("**Generation ID:**", progress_info.get('generation_id', 'N/A'))
        st.write("**Polling Interval:**", f"{progress_info['polling_interval']} seconds")
        st.write("**Status:**", progress_info['status'])
        
        # Time remaining estimate
        if progress_value > 0:
            elapsed_seconds = progress_info['elapsed_time_seconds']
            estimated_total = elapsed_seconds / progress_value if progress_value > 0 else 0
            remaining_seconds = max(0, estimated_total - elapsed_seconds)
            remaining_formatted = job_manager._format_duration(int(remaining_seconds))
            st.write("**Estimated Time Remaining:**", remaining_formatted)
        
        # # Progress chart (simple visualization)
        # if progress_info['attempts'] > 1:
        #     chart_data = {
        #         'Check': list(range(1, progress_info['attempts'] + 1)),
        #         'Progress': [0.1 * i for i in range(progress_info['attempts'])]  # Placeholder data
        #     }
        #     st.line_chart(chart_data, x='Check', y='Progress')
    
    # Warning if taking too long
    if progress_info['attempts'] > progress_info['max_attempts'] * 0.8:
        st.warning(
            f"⚠️ Video generation is taking longer than usual. "
            f"This may take up to {progress_info['max_time_formatted']} total."
        )
    
    # Manual refresh button
    if st.button("🔄 Check Status Now", help="Force an immediate status check"):
        # Reset the last check time to force immediate check
        session_manager.last_video_check_time = 0
        st.rerun()

def _render_status_banner(session_manager: SessionManager):
    """Render status banner based on current job status"""
    status_config = {
        JobStatus.IDLE: {"color": "blue", "icon": "💤", "message": "Ready to start"},
        JobStatus.PROCESSING: {"color": "orange", "icon": "⚡", "message": "Processing..."},
        JobStatus.WAITING_FOR_IMAGES: {"color": "orange", "icon": "🖼️", "message": "Generating images..."},
        JobStatus.SELECTING_IMAGE: {"color": "blue", "icon": "🎨", "message": "Please select an image"},
        JobStatus.AWAITING_AUDIO_APPROVAL: {"color": "blue", "icon": "🎵", "message": "Please approve audio"},
        JobStatus.PROCESSING_FINAL: {"color": "orange", "icon": "🎬", "message": "Generating video..."},
        JobStatus.COMPLETED: {"color": "green", "icon": "✅", "message": "Completed successfully!"},
        JobStatus.ERROR: {"color": "red", "icon": "❌", "message": "Error occurred"}
    }
    
    config = status_config.get(session_manager.job_status, {"color": "gray", "icon": "❓", "message": "Refresh Please"})
    
    if config["color"] == "green":
        st.success(f"{config['icon']} {config['message']}")
    elif config["color"] == "red":
        st.error(f"{config['icon']} {config['message']}")
        if session_manager.error_message:
            st.error(f"Error details: {session_manager.error_message}")
    elif config["color"] == "orange":
        st.warning(f"{config['icon']} {config['message']}")
    else:
        st.info(f"{config['icon']} {config['message']}")

def _render_debug_info(session_manager: SessionManager, job_manager: JobManager):
    """Render debug information"""
    st.subheader("🐛 Debug Information")
    
    debug_data = {
        "Session ID": session_manager.session_id,
        "Current Session ID": session_manager.current_session_id,
        "Job Status": session_manager.job_status.value,
        "Manual Mode": session_manager.manual_mode_active,
        "Generation ID": session_manager.generation_id,
        "Polling Active": session_manager.polling_active,
        "Video Progress": f"{session_manager.video_progress:.1%}",
        "Polling Attempts": session_manager.video_polling_attempts,
        "Last Video Check": time.ctime(session_manager.last_video_check_time) if session_manager.last_video_check_time > 0 else "Never",
        "Error Message": session_manager.error_message
    }
    
    # Progress information
    if session_manager.job_status == JobStatus.PROCESSING_FINAL:
        progress_info = job_manager.get_video_progress_info()
        debug_data.update({
            "Progress Info": progress_info,
            "Video Status Message": session_manager.video_status_message
        })
    
    st.json(debug_data)

# ... existing functions remain the same ...

def _render_audio_approval(job_manager: JobManager, session_manager: SessionManager):
    """Render audio approval interface for manual mode"""
    st.subheader("🎵 Audio Approval")
    st.write("Please listen to the generated audio and approve or request regeneration:")
    
    # Get audio data from session state
    audio_data = st.session_state.get('generated_audio_data')
    if audio_data and audio_data.get('url'):
        st.audio(audio_data['url'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Approve Audio", key="approve_audio", use_container_width=True):
                success, error = job_manager.approve_audio()
                if success:
                    st.success("Audio approved! Starting video generation...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to approve audio: {error}")
        
        with col2:
            if st.button("🔄 Regenerate Audio", key="regenerate_audio", use_container_width=True):
                with st.spinner("Regenerating audio..."):
                    success, error = job_manager.regenerate_audio()
                    if success:
                        st.info("Audio regeneration started...")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Failed to regenerate audio: {error}")
    else:
        st.warning("Audio data not available. Please try refreshing.")

def _render_image_selection(job_manager: JobManager, session_manager: SessionManager):
    """Render image selection interface"""
    st.subheader("🎨 Select Your Preferred Image")
    st.write("Choose one of the generated images to proceed with video creation:")
    
    images = session_manager.generated_images
    audio_data = st.session_state.get('generated_audio_data')
    
    # Show audio preview if available
    if audio_data and audio_data.get('url'):
        st.subheader("🎵 Generated Audio Preview")
        st.audio(audio_data['url'])
        
        if session_manager.manual_mode_active:
            st.info("You'll be able to approve or regenerate this audio after selecting an image.")
    
    if len(images) >= 2:
        col1, col2 = st.columns(2)
        
        for i, (col, image_data) in enumerate(zip([col1, col2], images[:2])):
            with col:
                st.write(f"**Option {i+1}**")
                
                # Try to display image
                try:
                    st.image(
                        image_data['url'],
                        caption=f"Generated Image Option {i+1}",
                        use_column_width=True
                    )
                except Exception as e:
                    st.error(f"Error loading image {i+1}: {str(e)}")
                    st.write("Image URL:", image_data.get('url', 'N/A'))
                
                # Selection button
                if st.button(
                    f"✅ Select Option {i+1}",
                    key=f"select_{i}",
                    use_container_width=True
                ):
                    with st.spinner("Processing your selection..."):
                        success, error = job_manager.select_image(image_data['id'])
                        
                        if success:
                            st.success(f"✅ Option {i+1} selected!")
                            if session_manager.manual_mode_active:
                                st.info("Please approve the audio to continue...")
                            else:
                                st.info("Starting video generation...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to process selection: {error}")
    else:
        st.warning("Waiting for images to be generated...")

def _render_completion(session_manager: SessionManager):
    """Render completion interface"""
    st.success("🎉 Video generation completed!")
    
    video_data = st.session_state.get('final_video_data')
    if video_data and video_data.get('url'):
        # center in a constrained middle column
        left, center, right = st.columns([1,4,1])
        with center:
            st.subheader("Preview")
            st.video(video_data["url"])
        
        # Download button stays the same
        if video_data.get('download_url'):
            st.download_button(
                label="📥 Download Video",
                data=video_data.get('video_data', b''),
                file_name=f"generated_video_{session_manager.session_id[:8]}.mp4",
                mime="video/mp4"
            )
        
        # Show details
        with st.expander("📊 Generation Details"):
            st.json(video_data)
    else:
        st.info("Video data not available. Please check the generation status.")

def _render_job_form(job_manager: JobManager, session_manager: SessionManager):
    """Render job submission form"""
    st.subheader("📝 Create Your Video")
    
    with st.form("job_form"):
        # Image upload
        st.write("**1. Upload Image**")
        image_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a portrait image (9:16 aspect ratio recommended)"
        )
        
        # Script input
        st.write("**2. Enter Script**")
        script_text = st.text_area(
            "Script/Dialogue",
            height=100,
            placeholder="Enter your script here...",
            help="The text that will be converted to speech and used for video generation"
        )
        
        # Audio options
        st.write("**3. Audio Options**")
        use_elevenlabs = st.checkbox("Use ElevenLabs TTS", value=True)
        
        audio_file = None
        voice_settings = {}
        
        if use_elevenlabs:
            # ElevenLabs voice settings
            voices = job_manager.get_elevenlabs_voices()
            if voices:
                voice_id = st.selectbox("Select Voice", options=list(voices.keys()))
                voice_settings = {
                    'voice_id': voices[voice_id],
                    'stability': st.slider("Stability", 0.0, 1.0, 0.5, 0.1),
                    'similarity': st.slider("Similarity Boost", 0.0, 1.0, 0.5, 0.1),
                    'style': st.slider("Style", 0.0, 1.0, 0.5, 0.1)
                }
            else:
                st.error("Failed to load ElevenLabs voices")
        else:
            # Audio file upload
            audio_file = st.file_uploader(
                "Upload Audio File (optional)",
                type=['mp3', 'wav'],
                help="Upload your own audio file instead of using TTS"
            )
        
        # Generation options
        st.write("**4. Generation Options**")
        manual_mode = st.checkbox(
            "Manual Mode",
            value=False,
            help="Enable manual approval of images and audio before final video generation"
        )
        
        # Submit button
        submitted = st.form_submit_button("🚀 Generate Video")
        
        if submitted:
            form_data = {
                'image_file': image_file,
                'script_text': script_text,
                'use_elevenlabs': use_elevenlabs,
                'audio_file': audio_file,
                'manual_mode': manual_mode,
                **voice_settings
            }
            
            with st.spinner("Submitting job..."):
                success, error = job_manager.submit_job(form_data)
                
                if success:
                    st.success("Job submitted successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to submit job: {error}")

def _render_help_section():
    """Render help section"""
    with st.expander("❓ Help & Tips"):
        st.markdown("""
        ### How to Use:
        1. **Upload Image**: Choose a clear portrait image (9:16 aspect ratio works best)
        2. **Enter Script**: Write the dialogue or text you want the character to speak
        3. **Audio Options**: Choose ElevenLabs TTS or upload your own audio
        4. **Generation Options**: Enable manual mode for more control over the process
        
        ### Tips:
        - Use high-quality images for better results
        - Keep scripts concise for better lip-sync
        - Manual mode allows you to approve images and audio before final generation
        - Video generation typically takes 2-5 minutes depending on length
        
        ### Troubleshooting:
        - If generation fails, try with a different image or shorter script
        - Check the debug info for technical details
        - Large files may take longer to process
        """)
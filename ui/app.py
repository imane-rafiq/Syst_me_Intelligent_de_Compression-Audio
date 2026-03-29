"""
PROFESSIONAL AUDIO COMPRESSION SYSTEM - WEB UI
==============================================

Modern, professional Streamlit interface for audio compression.
Features:
- Compress audio with AI-driven decisions
- Convert audio to text (transcription)
- Convert text to audio (synthesis) - Coming soon
- Professional design with sidebar navigation
- University branding

Run with:
    streamlit run app.py
"""

import streamlit as st
import requests
import json
import os
from pathlib import Path
from datetime import datetime
import time

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Audio Compression System",
    page_icon="audio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM STYLING - PROFESSIONAL THEME
# ============================================================================

st.markdown("""
    <style>
    :root {
        --brand-gradient: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        --sidebar-text: #f3f7ff;
    }

    /* Remove default padding and margins */
    .main {
        padding: 0.5rem 3rem 2rem 3rem;
        background-color: #f8f9fa;
    }
    
    /* Navbar styling */
    .navbar {
        background: var(--brand-gradient);
        padding: 1.5rem;
        border-radius: 0 0 12px 0;
        margin-left: -3rem;
        margin-right: -3rem;
        padding-left: 3rem;
        padding-right: 3rem;
        margin-bottom: 2rem;
        box-shadow: 0 6px 14px rgba(16, 33, 62, 0.18);
        color: white;
        text-align: center;
    }
    
    .navbar h1 {
        margin: 0;
        font-size: 2em;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-align: center;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--brand-gradient);
        border-right: none;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: var(--brand-gradient);
        box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.12);
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 0.5rem;
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--sidebar-text) !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border: 1px solid rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.14);
        color: #ffffff;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: rgba(255, 255, 255, 0.6);
        background: rgba(255, 255, 255, 0.24);
    }
    
    /* Button styling */
    .nav-button {
        background-color: #f0f2f6;
        border: 2px solid #ddd;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        font-weight: 600;
        color: #333;
    }
    
    .nav-button:hover {
        background-color: #e8eef7;
        border-color: #1e3c72;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 60, 114, 0.15);
    }
    
    .nav-button.active {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border-color: #1e3c72;
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: box-shadow 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    
    /* Success message */
    .success-message {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        margin: 1rem 0;
        color: #2e7d32;
    }
    
    /* Info message */
    .info-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        margin: 1rem 0;
        color: #1565c0;
    }
    
    /* Error message */
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        margin: 1rem 0;
        color: #c62828;
    }
    
    /* Metric cards */
    .metric-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .metric-value {
        font-size: 2.5em;
        font-weight: 700;
        color: #1e3c72;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9em;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed #1e3c72;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f8f9fa;
    }
    
    /* Results section */
    .results-section {
        margin-top: 2rem;
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* University logo */
    .logo-container {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.24);
        margin-bottom: 2rem;
    }
    
    .logo-container img {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 3px solid #1e3c72;
        object-fit: cover;
    }
    
    /* Navigation section */
    .nav-section {
        margin-top: 1rem;
    }
    
    .nav-section h3 {
        font-size: 0.9em;
        color: #d4e2ff;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    /* Main heading */
    h1, h2, h3 {
        color: #1e3c72;
        font-weight: 700;
    }
    
    /* Streamlit elements customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #1e3c72;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
    }
    
    /* Divider */
    .divider {
        border-top: 1px solid #e0e0e0;
        margin: 2rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
UPLOAD_DIR = Path("./data/audio_files")
OUTPUT_DIR = Path("./data/outputs")

# Create directories
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'compress'
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result' not in st.session_state:
    st.session_state.result = None
if 'error' not in st.session_state:
    st.session_state.error = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_api_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def format_file_size(bytes_size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location."""
    try:
        file_path = UPLOAD_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return str(file_path)
    except Exception as e:
        return None


def call_api_endpoint(endpoint, payload=None, files=None, timeout=60):
    """Call API endpoint."""
    try:
        if files:
            response = requests.post(
                f"{API_BASE_URL}{endpoint}",
                files=files,
                timeout=timeout
            )
        else:
            response = requests.post(
                f"{API_BASE_URL}{endpoint}",
                json=payload,
                timeout=timeout
            )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return None, f"API Error: {error_detail}"
    
    except requests.Timeout:
        return None, f"Request timeout (>{timeout}s). Please try again."
    except Exception as e:
        return None, f"Connection error: {str(e)}"


# ============================================================================
# PAGE CONTENT
# ============================================================================

def page_compress():
    """Compression page."""
    st.markdown('<div class="navbar"><h1>Audio Compression</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("Upload an audio file and our AI will automatically choose the best compression settings for you.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div style="color: #000000 !important; font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem;">Upload Audio File</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "mp3", "flac", "m4a", "ogg", "opus", "aiff", "aac"],
            label_visibility="collapsed"
        )
    
    with col2:
        if uploaded_file:
            st.subheader("File Details")
            st.write(f"**Name:** {uploaded_file.name}")
            st.write(f"**Size:** {format_file_size(uploaded_file.size)}")
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    if uploaded_file:
        if st.button("Start Compression", type="primary", use_container_width=True):
            st.session_state.processing = True
            
            file_path = save_uploaded_file(uploaded_file)
            if not file_path:
                st.markdown('<div class="error-message">Failed to save uploaded file</div>', unsafe_allow_html=True)
                return
            
            # Process using pipeline
            progress_bar = st.progress(0)
            status_container = st.container()
            
            try:
                with status_container:
                    st.write("Processing audio file...")
                
                progress_bar.progress(50)
                
                # Call pipeline endpoint
                with open(file_path, 'rb') as f:
                    files = {'file': (uploaded_file.name, f, uploaded_file.type)}
                    result, error = call_api_endpoint("/pipeline", files=files, timeout=300)
                
                progress_bar.progress(100)
                
                if error:
                    st.markdown(f'<div class="error-message">{error}</div>', unsafe_allow_html=True)
                else:
                    st.session_state.result = result
                    display_compression_results(result)
            
            except Exception as e:
                st.markdown(f'<div class="error-message">Error: {str(e)}</div>', unsafe_allow_html=True)
            
            finally:
                st.session_state.processing = False


def page_audio_to_text():
    """Audio to text (transcription) page."""
    st.markdown('<div class="navbar"><h1>Audio to Text</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("Convert audio files to text using advanced speech recognition powered by AI.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div style="color: #000000 !important; font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem;">Upload Audio File</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choose an audio file to transcribe",
            type=["wav", "mp3", "flac", "m4a", "ogg", "opus"],
            key="audio_to_text_uploader",
            label_visibility="collapsed"
        )
    
    with col2:
        if uploaded_file:
            st.subheader("File Details")
            st.write(f"**Name:** {uploaded_file.name}")
            st.write(f"**Size:** {format_file_size(uploaded_file.size)}")
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    if uploaded_file:
        if st.button("Convert to Text", type="primary", use_container_width=True):
            file_path = save_uploaded_file(uploaded_file)
            if not file_path:
                st.markdown('<div class="error-message">Failed to save uploaded file</div>', unsafe_allow_html=True)
                return
            
            progress_bar = st.progress(0)
            
            try:
                with st.status("Processing audio transcription...", expanded=True) as status:
                    st.write("Analyzing audio file...")
                
                progress_bar.progress(33)
                
                # Call transcribe endpoint (new)
                with open(file_path, 'rb') as f:
                    files = {'file': (uploaded_file.name, f, uploaded_file.type)}
                    result, error = call_api_endpoint("/transcribe", files=files, timeout=300)
                
                progress_bar.progress(100)
                
                if error:
                    st.markdown(f'<div class="error-message">{error}</div>', unsafe_allow_html=True)
                else:
                    display_transcription_results(result)
            
            except Exception as e:
                st.markdown(f'<div class="error-message">Error: {str(e)}</div>', unsafe_allow_html=True)


def page_text_to_audio():
    """Text to audio (synthesis) page."""
    st.markdown('<div class="navbar"><h1>Text to Audio</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("Coming soon: Convert text to natural-sounding audio using advanced synthesis.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.info("This feature is currently in development. Check back soon!")


def display_compression_results(result):
    """Display compression results beautifully."""
    
    st.markdown('<div class="success-message">Compression completed successfully</div>', unsafe_allow_html=True)
    
    execution = result['result']['execution']
    decision = result['result']['decision']
    report = result['result']['report']
    
    # Metrics row
    st.subheader("Compression Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        compression_pct = (1 - execution['compression_ratio']) * 100
        st.markdown(f'<div class="metric-value">{compression_pct:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Size Reduced</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{decision["codec"].upper()}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Codec</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{decision["bitrate"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Bitrate (kbps)</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        snr = report.get('snr_db')
        snr_display = f"{snr:.1f}" if snr is not None else "N/A"
        st.markdown(f'<div class="metric-value">{snr_display}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Quality (SNR dB)</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed information
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["File Details", "Decision Reasoning", "Download"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("**Original File**")
            st.write(f"Size: {format_file_size(execution['original_size'])}")
            st.write(f"Duration: {execution.get('duration', 'N/A')} seconds")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("**Compressed File**")
            st.write(f"Size: {format_file_size(execution['compressed_size'])}")
            st.write(f"Format: {decision['codec'].upper()}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**AI Compression Decision**")
        st.write(decision['reasoning'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        # Download compressed file
        if Path(execution['output_filepath']).exists():
            with open(execution['output_filepath'], 'rb') as f:
                st.download_button(
                    label="Download Compressed Audio",
                    data=f.read(),
                    file_name=Path(execution['output_filepath']).name,
                    mime="audio/mpeg",
                    use_container_width=True
                )
        
        # Download report
        st.download_button(
            label="Download Report (JSON)",
            data=json.dumps(result, indent=2),
            file_name="compression_report.json",
            mime="application/json",
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)


def display_transcription_results(result):
    """Display transcription results."""
    
    st.markdown('<div class="success-message">Transcription completed successfully</div>', unsafe_allow_html=True)
    
    # The API returns `transcription` containing a `transcription` dict which contains `text`
    transcription_data = result.get('transcription', {})
    transcription_text = transcription_data.get('transcription', {}).get('text', '')
    analysis_text = transcription_data.get('analysis', {}).get('analysis', '')
    
    st.subheader("Transcription Results")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.text_area("Transcribed Text", transcription_text, height=300, disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Download transcription
    st.download_button(
        label="Download Transcription (TXT)",
        data=transcription_text,
        file_name="transcription.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    # Download JSON report
    st.download_button(
        label="Download Full Report (JSON)",
        data=json.dumps(result, indent=2),
        file_name="transcription_report.json",
        mime="application/json",
        use_container_width=True
    )


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

with st.sidebar:
    # Logo placeholder
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    logo_path = Path(__file__).parent / "logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    st.markdown(
        '<p style="text-align: center; font-weight: 700; margin: 0.5rem 0 0.25rem 0;">AUDIO COMPRESSION</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="text-align: center; font-style: italic; margin: 0;">University Project</p>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    st.markdown('<div class="nav-section">', unsafe_allow_html=True)
    
    if st.button(
        "Compress Audio",
        key="nav_compress",
        use_container_width=True,
        type="primary" if st.session_state.current_page == 'compress' else "secondary"
    ):
        st.session_state.current_page = 'compress'
        st.rerun()
    
    if st.button(
        "Audio to Text",
        key="nav_transcribe",
        use_container_width=True,
        type="primary" if st.session_state.current_page == 'transcribe' else "secondary"
    ):
        st.session_state.current_page = 'transcribe'
        st.rerun()
    
    if st.button(
        "Text to Audio",
        key="nav_synthesis",
        use_container_width=True,
        type="primary" if st.session_state.current_page == 'synthesis' else "secondary"
    ):
        st.session_state.current_page = 'synthesis'
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Help section
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    st.markdown('<div class="nav-section">', unsafe_allow_html=True)
    st.write("**About**")
    
    with st.expander("How it works"):
        st.write("""
        Our system uses advanced AI to intelligently process audio:
        
        - **Compress**: AI selects optimal codec and bitrate
        - **Transcribe**: Converts audio to text
        - **Synthesize**: Converts text to audio (coming soon)
        """)
    
    with st.expander("Supported Formats"):
        st.write("""
        - WAV
        - MP3
        - FLAC
        - M4A
        - OGG
        - Opus
        - AIFF
        - AAC
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# MAIN CONTENT
# ============================================================================

# Check API health
if not check_api_health():
    st.error("""
    API Server is not running. Please start the backend server:
    ```bash
    python -m uvicorn api:app --reload
    ```
    """)
else:
    # Route to appropriate page
    if st.session_state.current_page == 'compress':
        page_compress()
    elif st.session_state.current_page == 'transcribe':
        page_audio_to_text()
    elif st.session_state.current_page == 'synthesis':
        page_text_to_audio()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #999; font-size: 0.9em; margin-top: 3rem;'>
<p>Audio Compression System | University Project </p>
</div>
""", unsafe_allow_html=True)
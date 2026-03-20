"""
STREAMLIT WEB UI - Audio Compression System
============================================

A beautiful, user-friendly web interface for the audio compression system.

Features:
- Drag-drop audio file upload
- Real-time processing with progress bar
- Beautiful metrics display
- Download compressed audio
- Process multiple files

Run with:
    streamlit run app.py

Then visit:
    http://localhost:8501
"""

import streamlit as st
import requests
import json
import os
from pathlib import Path
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="🎵 Audio Compression System",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
UPLOAD_DIR = Path("./data/audio_files")
OUTPUT_DIR = Path("./data/outputs")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize session state
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


def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location."""
    try:
        file_path = UPLOAD_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return str(file_path)
    except Exception as e:
        st.error(f"❌ Error saving file: {str(e)}")
        return None


def call_agent(endpoint, payload, timeout=60):
    """Call an agent endpoint."""
    try:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.json().get('detail', 'Unknown error')}"
    
    except requests.Timeout:
        return None, f"⏱️  Request timeout (>{timeout}s). File might be too large."
    except Exception as e:
        return None, f"API Error: {str(e)}"


def process_audio_workflow(file_path):
    """Run complete audio processing workflow."""
    
    progress_bar = st.progress(0)
    status = st.status("Processing audio...", expanded=True)
    
    try:
        # Step 1: Load audio
        with status:
            st.write("🔍 Step 1/5: Loading audio file...")
        progress_bar.progress(20)
        
        metadata, error = call_agent("/input/load", {"filepath": file_path})
        if error:
            return None, error
        
        time.sleep(0.5)  # Small delay for UX
        
        # Step 2: Extract features
        with status:
            st.write("📊 Step 2/5: Extracting audio features...")
        progress_bar.progress(40)
        
        features, error = call_agent("/features/extract", {"filepath": file_path}, timeout=60)
        if error:
            return None, error
        
        time.sleep(0.5)
        
        # Step 3: Make decision (LLM)
        with status:
            st.write("🧠 Step 3/5: Using AI to decide compression...")
        progress_bar.progress(60)
        
        decision, error = call_agent(
            "/decision/decide",
            {
                "filepath": file_path,
                "metadata": metadata,
                "features": features
            },
            timeout=30
        )
        if error:
            return None, error
        
        time.sleep(0.5)
        
        # Step 4: Compress
        with status:
            st.write("⚙️  Step 4/5: Compressing audio...")
        progress_bar.progress(80)
        
        compression, error = call_agent(
            "/execution/compress",
            {
                "filepath": file_path,
                "codec": decision['codec'],
                "bitrate": decision['bitrate'],
                "sample_rate": decision['sample_rate'],
                "channels": metadata['channels']
            },
            timeout=120
        )
        if error:
            return None, error
        
        time.sleep(0.5)
        
        # Step 5: Generate report
        with status:
            st.write("📈 Step 5/5: Generating quality report...")
        progress_bar.progress(100)
        
        report, error = call_agent(
            "/report/generate",
            {
                "original_filepath": file_path,
                "compressed_filepath": compression['output_filepath']
            },
            timeout=30
        )
        if error:
            return None, error
        
        # Combine all results
        result = {
            'metadata': metadata,
            'features': features,
            'decision': decision,
            'compression': compression,
            'report': report,
            'timestamp': datetime.now().isoformat()
        }
        
        return result, None
    
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def format_file_size(bytes_size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def display_results(result):
    """Display processing results beautifully."""
    
    metadata = result['metadata']
    features = result['features']
    decision = result['decision']
    compression = result['compression']
    report = result['report']
    
    # Success message
    st.markdown(
        '<div class="success-box">✅ Processing complete! Compression successful.</div>',
        unsafe_allow_html=True
    )
    
    # Tabs for different information
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Metrics", "🎵 Audio Info", "🧠 AI Decision", "📈 Details"]
    )
    
    # Tab 1: Key Metrics
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            compression_pct = report['compression_ratio'] * 100
            st.metric(
                "Compression",
                f"{compression_pct:.1f}%",
                help="% of original size reduction"
            )
        
        with col2:
            st.metric(
                "Codec",
                decision['codec'].upper(),
                help=f"Audio format"
            )
        
        with col3:
            st.metric(
                "Bitrate",
                f"{report['bitrate_kbps']} kbps",
                help="Data rate"
            )
        
        with col4:
            if report['snr_db']:
                st.metric(
                    "Quality (SNR)",
                    f"{report['snr_db']:.1f} dB",
                    help="Signal-to-Noise Ratio (higher = better)"
                )
            else:
                st.metric("Quality", "N/A")
        
        # File sizes comparison
        st.subheader("File Sizes")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **Original File**
            - Size: {format_file_size(report['original_size_mb'] * 1024 * 1024)}
            - Duration: {report['duration']:.1f} seconds
            - Format: {metadata['codec']}
            """)
        
        with col2:
            st.success(f"""
            **Compressed File**
            - Size: {format_file_size(report['compressed_size_mb'] * 1024 * 1024)}
            - Duration: {report['duration']:.1f} seconds
            - Format: {decision['codec'].upper()}
            """)
    
    # Tab 2: Audio Information
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Metadata")
            st.write(f"**Filename:** {metadata['filename']}")
            st.write(f"**Duration:** {metadata['duration']:.2f} seconds")
            st.write(f"**Sample Rate:** {metadata['sample_rate']} Hz")
            st.write(f"**Channels:** {metadata['channels']} ({'Mono' if metadata['channels'] == 1 else 'Stereo'})")
            st.write(f"**Original Codec:** {metadata['codec']}")
        
        with col2:
            st.subheader("🎚️ Audio Features")
            st.write(f"**Content Type:** {features['content_type'].capitalize()}")
            st.write(f"**Spectral Centroid:** {features['centroid']:.0f} Hz")
            st.write(f"**Spectral Entropy:** {features['entropy']:.2f}")
            st.write(f"**Zero Crossing Rate:** {features['zero_crossing_rate']:.4f}")
            st.write(f"**RMS Energy:** {features['rms_energy']:.4f}")
    
    # Tab 3: AI Decision
    with tab3:
        st.subheader("🧠 AI Compression Decision")
        
        decision_box = f"""
        **Codec:** {decision['codec'].upper()}
        **Bitrate:** {decision['bitrate']} kbps
        **Sample Rate:** {decision['sample_rate']} Hz
        **Channels:** {decision['channels']}
        
        **Reasoning:**
        {decision['reasoning']}
        """
        
        st.markdown(
            f'<div class="info-box">{decision_box}</div>',
            unsafe_allow_html=True
        )
    
    # Tab 4: Detailed Results
    with tab4:
        st.subheader("📄 Raw Results (JSON)")
        
        # Create downloadable JSON
        json_results = {
            'metadata': metadata,
            'features': features,
            'decision': decision,
            'compression': compression,
            'report': report
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Display JSON (collapsible)
            with st.expander("View Full JSON Results"):
                st.json(json_results)
        
        with col2:
            # Download buttons
            st.subheader("⬇️ Downloads")
            
            # Download compressed audio
            if Path(compression['output_filepath']).exists():
                with open(compression['output_filepath'], 'rb') as f:
                    st.download_button(
                        label=f"📥 Download Compressed Audio ({format_file_size(compression['compressed_size'])})",
                        data=f.read(),
                        file_name=Path(compression['output_filepath']).name,
                        mime="audio/mpeg"
                    )
            
            # Download report as JSON
            st.download_button(
                label="📊 Download Report (JSON)",
                data=json.dumps(json_results, indent=2),
                file_name=f"{Path(metadata['filename']).stem}_report.json",
                mime="application/json"
            )


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit app."""
    
    # Header
    st.title("🎵 Intelligent Audio Compression")
    st.markdown("*Powered by AI-driven compression decisions*")
    
    # Check API health
    if not check_api_health():
        st.error("""
        ❌ **API Server Not Running**
        
        The audio compression API is not available. Please start it first:
        
        ```bash
        python agents_main.py
        ```
        
        Then refresh this page.
        """)
        return
    
    st.success("✅ API Server Connected")
    
    # Sidebar information
    with st.sidebar:
        st.header("ℹ️ About")
        st.write("""
        This system uses AI to intelligently compress audio files.
        
        **How it works:**
        1. 🔍 Load & analyze audio
        2. 📊 Extract audio features
        3. 🧠 AI decides best codec & bitrate
        4. ⚙️ Compress with optimal settings
        5. 📈 Generate quality report
        
        **Supported Codecs:**
        - MP3
        - AAC
        - Opus
        - OGG Vorbis
        - FLAC (lossless)
        """)
        
        st.divider()
        
        st.header("📚 Documentation")
        st.markdown("""
        - [QUICKSTART](../QUICKSTART.md)
        - [Implementation Guide](../IMPLEMENTATION_GUIDE.md)
        - [Code Summary](../CODE_SUMMARY.md)
        """)
    
    # Main content
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📤 Upload Audio File")
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "mp3", "flac", "m4a", "ogg", "opus", "aiff", "aac"],
            help="Select any audio file up to 500MB"
        )
    
    with col2:
        st.subheader("ℹ️ File Info")
        if uploaded_file:
            st.write(f"**Name:** {uploaded_file.name}")
            st.write(f"**Size:** {format_file_size(uploaded_file.size)}")
            st.write(f"**Type:** {uploaded_file.type}")
    
    st.divider()
    
    # Process button
    if uploaded_file:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            process_button = st.button(
                "🚀 Process & Compress",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            show_details = st.checkbox("Show details", value=False)
        
        if process_button:
            st.session_state.processing = True
            st.session_state.error = None
            st.session_state.result = None
            
            # Save file
            file_path = save_uploaded_file(uploaded_file)
            
            if file_path:
                if show_details:
                    st.info(f"📁 File saved to: `{file_path}`")
                
                # Process audio
                result, error = process_audio_workflow(file_path)
                
                if error:
                    st.session_state.error = error
                else:
                    st.session_state.result = result
            
            st.session_state.processing = False
    
    st.divider()
    
    # Display results
    if st.session_state.result:
        st.subheader("✨ Results")
        display_results(st.session_state.result)
    
    if st.session_state.error:
        st.error(f"❌ {st.session_state.error}")
    
    # Footer
    st.divider()
    st.markdown("""
    ---
    **Audio Compression System** | Built with FastAPI + Streamlit | Powered by Claude AI
    """)


if __name__ == "__main__":
    main()
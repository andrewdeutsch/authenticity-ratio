"""
Brand Guidelines Management Page for Webapp
Separate module to keep app.py clean
"""
import streamlit as st
import os
import tempfile
from pathlib import Path
from utils.document_processor import BrandGuidelinesProcessor


def show_brand_guidelines_page():
    """Display brand guidelines management interface"""
    
    st.markdown('<div class="main-header">📋 Brand Guidelines Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload and manage brand voice & style guidelines</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Initialize processor
    processor = BrandGuidelinesProcessor()
    
    # Brand selection
    st.markdown("### Select Brand")
    brand_id = st.text_input(
        "Brand ID",
        value="",
        help="Enter the brand identifier (e.g., 'mastercard', 'nike')",
        placeholder="e.g., mastercard"
    )
    
    if not brand_id:
        st.info("👆 Enter a brand ID to manage guidelines")
        return
    
    # Normalize brand ID
    brand_id = brand_id.lower().strip().replace(" ", "_")
    
    st.divider()
    
    # Check if guidelines exist
    current_guidelines = processor.load_guidelines(brand_id)
    current_metadata = processor.load_metadata(brand_id)
    
    # Two columns: Upload | Current Status
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Upload Guidelines")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'txt'],
            help="Upload your brand voice and style guidelines document",
            key="guidelines_uploader"
        )
        
        if uploaded_file:
            st.write(f"**File**: {uploaded_file.name}")
            st.write(f"**Size**: {uploaded_file.size:,} bytes")
            
            if st.button("🚀 Process and Upload", type="primary"):
                with st.spinner("Processing document..."):
                    try:
                        # Save uploaded file to temp location
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        # Extract text
                        text = processor.extract_text(tmp_path)
                        
                        # Clean up temp file
                        os.unlink(tmp_path)
                        
                        # Save guidelines
                        metadata = processor.save_guidelines(
                            brand_id=brand_id,
                            text=text,
                            original_filename=uploaded_file.name,
                            file_size=uploaded_file.size
                        )
                        
                        st.success(f"✅ Guidelines uploaded successfully!")
                        st.write(f"**Words extracted**: {metadata['word_count']:,}")
                        st.write(f"**Characters**: {metadata['character_count']:,}")
                        
                        # Refresh page to show new guidelines
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error processing document: {str(e)}")
                        st.exception(e)
    
    with col2:
        st.markdown("### 📊 Current Status")
        
        if current_guidelines:
            st.success("✅ Guidelines uploaded")
            
            if current_metadata:
                st.write(f"**File**: {current_metadata.get('original_filename', 'Unknown')}")
                st.write(f"**Uploaded**: {current_metadata.get('upload_date', 'Unknown')[:10]}")
                st.write(f"**Words**: {current_metadata.get('word_count', 0):,}")
                st.write(f"**Characters**: {current_metadata.get('character_count', 0):,}")
            
            # Delete button
            if st.button("🗑️ Delete Guidelines", type="secondary"):
                if processor.delete_guidelines(brand_id):
                    st.success("Guidelines deleted successfully")
                    st.rerun()
                else:
                    st.error("Failed to delete guidelines")
        else:
            st.warning("⚠️ No guidelines uploaded yet")
            st.caption("Upload a document to get started")
    
    st.divider()
    
    # Preview section
    if current_guidelines:
        st.markdown("### 📖 Preview Guidelines")
        
        with st.expander("View Full Text", expanded=False):
            # Show first 5000 characters with option to see more
            preview_length = 5000
            if len(current_guidelines) > preview_length:
                st.text_area(
                    "Guidelines (first 5000 characters)",
                    current_guidelines[:preview_length] + "\n\n... [truncated]",
                    height=400,
                    disabled=True
                )
                st.caption(f"Total length: {len(current_guidelines):,} characters")
            else:
                st.text_area(
                    "Guidelines",
                    current_guidelines,
                    height=400,
                    disabled=True
                )
    
    st.divider()
    
    # Usage information
    st.markdown("### ℹ️ How It Works")
    
    st.markdown("""
    **Brand guidelines are used during Coherence scoring to:**
    
    1. 🎯 **Accurate Assessment**: Compare content against your specific brand voice, not generic standards
    2. 📝 **Better Suggestions**: Recommendations reference your actual guidelines
    3. 🔍 **Consistency Checks**: Flag deviations from documented voice, tone, and vocabulary
    
    **Example**:
    
    Without guidelines:
    > "Change 'Find the right card' → 'Discover your card'" (generic advice)
    
    With guidelines:
    > "Change 'Find the right card' → 'Discover your card'. This aligns with your brand guideline (p.12): 'Use "discover" over "find" to convey empowerment.'"
    
    **Supported Formats**: PDF, DOCX, TXT
    """)
    
    # Show all brands with guidelines
    st.divider()
    st.markdown("### 📚 All Brands with Guidelines")
    
    brands_with_guidelines = processor.list_brands_with_guidelines()
    if brands_with_guidelines:
        for brand in brands_with_guidelines:
            metadata = processor.load_metadata(brand)
            if metadata:
                st.write(f"**{brand}** - {metadata.get('word_count', 0):,} words - Uploaded {metadata.get('upload_date', 'Unknown')[:10]}")
    else:
        st.caption("No brands have uploaded guidelines yet")

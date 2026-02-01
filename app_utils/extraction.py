import zipfile
import os
from PIL import Image
import pytesseract
import streamlit as st

# Absolute path resolution for the Ubuntu host
UPLOAD_BASE = os.path.join(os.path.dirname(__file__), "..", "user_data", "uploads")

def process_uploads(uploaded_files, user_key="default"):
    """Processes files and sandboxes them into user-specific directories."""
    file_context = ""
    image_bytes_list = []
    
    # 1. Create a private sandbox for this specific GitHub ID
    user_upload_path = os.path.join(UPLOAD_BASE, str(user_key))
    os.makedirs(user_upload_path, exist_ok=True)
    
    for f in uploaded_files:
        name = f.name.lower()
        
        # Save a physical copy to the Ubuntu drive
        saved_path = os.path.join(user_upload_path, name)
        with open(saved_path, "wb") as temp_file:
            temp_file.write(f.getbuffer())

        # 2. Extract Text
        if name.endswith(('.txt', '.md', '.py', '.log')):
            content = f.read().decode('utf-8', errors='ignore')
            file_context += f"\n[DOC: {name}]\n{content}\n"
            
        # 3. Handle ZIPs
        elif name.endswith('.zip'):
            with zipfile.ZipFile(f) as z:
                for zname in z.namelist():
                    if zname.lower().endswith(('.txt', '.md', '.py', '.log')):
                        with z.open(zname) as iz:
                            content = iz.read().decode('utf-8', errors='ignore')
                            file_context += f"\n[ZIP_DOC: {zname}]\n{content}\n"
        
        # 4. Handle Images (Vision + OCR Fallback)
        elif name.endswith(('.png', '.jpg', '.jpeg')):
            img_data = f.getvalue()
            image_bytes_list.append(img_data)
            img = Image.open(f)
            ocr_text = pytesseract.image_to_string(img)
            file_context += f"\n[IMAGE_OCR: {name}]\n{ocr_text}\n"
            
    return file_context, image_bytes_list
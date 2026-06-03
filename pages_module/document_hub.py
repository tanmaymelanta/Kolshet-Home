import streamlit as st
import boto3
from datetime import datetime
from aws_helpers import get_s3_client, BUCKET_NAME, DOCUMENT_CATEGORIES, DOCUMENT_PREFIX


# ── S3 helpers ────────────────────────────────────────────────────────────────

def list_documents(category=None):
    s3 = get_s3_client()
    prefix = DOCUMENT_PREFIX
    if category:
        prefix = f"{DOCUMENT_PREFIX}{category}"
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
        docs = []
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                parts = key.replace(DOCUMENT_PREFIX, '').split('/')
                if len(parts) == 2 and parts[1]:
                    docs.append({'key': key, 'category': parts[0], 'filename': parts[1], 'size_kb': round(obj['Size'] / 1024, 1)})
        return docs
    except Exception as e:
        st.error(f"Could not list documents: {e}")
        return []

def upload_document(category, filename, file_bytes, content_type):
    s3 = get_s3_client()
    key = f"{DOCUMENT_PREFIX}{category}/{filename}"
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=file_bytes,
            ContentType=content_type
        )
        return True
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return False

def generate_download_url(key):
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=300
        )
        return url
    except Exception as e:
        st.error(f"Could not generate download link: {e}")
        return None

def get_content_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    mapping = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return mapping.get(ext, 'application/octet-stream')

def render():
    st.title("📁 Document Hub")
    st.caption("Store and access important property documents — SDR, bank letters, registration papers, etc.")
    tab_view, tab_upload = st.tabs(["📂 My Documents", "⬆️ Upload Document"])
    
    with tab_view:
        col_filter, _ = st.columns([1, 3])
        with col_filter:
            selected_category = st.selectbox("Filter by category", ["All"] + DOCUMENT_CATEGORIES)
        category_filter = None if selected_category == "All" else selected_category
        docs = list_documents(category_filter)
        if not docs:
            st.info("No documents found. Upload your first document in the 'Upload Document' tab.")
        else:
            from itertools import groupby
            docs_sorted = sorted(docs, key=lambda d: d['category'])
            for category, group in groupby(docs_sorted, key=lambda d: d['category']):
                group_list = list(group)
                st.markdown(f"#### 📂 {category} ({len(group_list)} file{'s' if len(group_list) > 1 else ''})")

                for doc in group_list:
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        ext = doc['filename'].rsplit('.', 1)[-1].upper()
                        icon = {'PDF': '📄', 'JPG': '🖼️', 'JPEG': '🖼️', 'PNG': '🖼️', 'DOC': '📝', 'DOCX': '📝'}.get(ext, '📎')
                        st.markdown(f"{icon} **{doc['filename']}**")
                        st.caption(f"{doc['size_kb']} KB")
                    with col2:
                        download_url = generate_download_url(doc['key'])
                        if download_url:
                            st.link_button("⬇️ Download", download_url)
                    with col3:
                        ext_lower = doc['filename'].rsplit('.', 1)[-1].lower()
                        if ext_lower in ['jpg', 'jpeg', 'png', 'pdf']:
                            if st.button("👁️ View", key=f"view_{doc['key']}"):
                                st.session_state[f"preview_{doc['key']}"] = True

                    if st.session_state.get(f"preview_{doc['key']}"):
                        preview_url = generate_download_url(doc['key'])
                        ext_lower = doc['filename'].rsplit('.', 1)[-1].lower()
                        if ext_lower in ['jpg', 'jpeg', 'png']:
                            st.image(preview_url, caption=doc['filename'])
                        elif ext_lower == 'pdf':
                            st.markdown(f"[Open PDF in new tab]({preview_url})")
                        if st.button("Close preview", key=f"close_{doc['key']}"):
                            st.session_state[f"preview_{doc['key']}"] = False
                            st.rerun()
                st.markdown("---")

        # ── Upload tab ────────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown("### Upload a Document")
        with st.form("upload_doc_form", clear_on_submit=True):
            category = st.selectbox("Category *", DOCUMENT_CATEGORIES)
            custom_name = st.text_input("Save as *", placeholder="yyyy-mm-dd filename amount if any")
            uploaded_file = st.file_uploader("Choose file *", type=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])
            submitted = st.form_submit_button("📤 Upload", use_container_width=True)
        if submitted:
            if not uploaded_file:
                st.error("Please select a file to upload.")
            elif not custom_name:
                st.error("Please give filename in mentioned format.")
            else:
                filename = custom_name.strip() if custom_name.strip() else uploaded_file.name
                if custom_name.strip() and '.' not in custom_name:
                    ext = uploaded_file.name.rsplit('.', 1)[-1]
                    filename = f"{filename}.{ext}"
                content_type = get_content_type(filename)
                file_bytes = uploaded_file.read()
                with st.spinner(f"Uploading {filename}..."):
                    success = upload_document(category, filename, file_bytes, content_type)
                if success:
                    st.success(f"✅ **{custom_name}** uploaded to **{category}** successfully!")
                    st.info("Switch to 'My Documents' tab to view it.")

"""
基于 Streamlit 完成WEB 网页上传
"""
import streamlit as st

from rag.knowledge_base import KnowledgeBaseService

st.title("知识库更新")
uploader_file =  st.file_uploader(
    "请上传文件",
    type=['md','txt','pdf'],
    accept_multiple_files=False,
)

if "service" not in st.session_state:
    st.session_state.service = KnowledgeBaseService()

if uploader_file is not None:
    file_name = uploader_file.name
    file_type = uploader_file.type
    file_size = uploader_file.size / 1024
    st.subheader(f"文件名：{file_name}")
    st.write(f"格式：{file_type} | 大小 {file_size:.2f} KB")

    # 展示内容
    text = uploader_file.getvalue().decode("utf-8")
    # sl.write(text)
    res = st.session_state["service"].upload_by_str(text, file_name)
    st.write(res)
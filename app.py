import os
import io
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from database import (
    init_db, register_user, login_user, get_username,
    save_pdf, get_user_pdfs, get_pdf_bytes, delete_pdf,
    save_message
)

load_dotenv()
init_db()

def get_pdf_text_from_bytes(pdf_bytes):
    text = ""
    reader =  PdfReader(io.BytesIO(pdf_bytes))
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def get_page_count_from_bytes(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    return text_splitter.split_text(text)

def get_vectorstore(text_chunks):
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return FAISS.from_texts(texts=text_chunks, embedding=embeddings)


def get_conversation_chain(vectorstore):
    llm = ChatGroq(
        temperature=0,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile"
    )
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    return ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            if i == len(st.session_state.chat_history) - 2:
                save_message(st.session_state.user_id, "user", message.content)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            if i == len(st.session_state.chat_history) - 1:
                save_message(st.session_state.user_id, "assistant", message.content)

def generate_summary(text):
    from groq import Groq as GroqClient
    client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
    snippet = text[:4000]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user",
                   "content": f"Give a concise 3-4 sentence summary of this document:\n\n{snippet}"}],
        max_tokens=300
    )
    return response.choices[0].message.content

def show_auth_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 📚 Chat with Multiple PDFs")
        st.markdown("Upload your PDFs and ask questions using AI")
        st.markdown("---")
        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            username = st.text_input("Username", key="login_user", autocomplete="off")
            password = st.text_input("Password", type="password", key="login_pass", autocomplete="off")
            if st.button("Login", use_container_width=True, type="primary"):
                if username and password:
                    ok, user_id = login_user(username, password)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = get_username(user_id)
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please fill in all fields.")

        with tab_register:
            new_user = st.text_input("Choose a username", key="reg_user", autocomplete="username")
            new_pass = st.text_input("Choose a password (min 6 chars)", type="password", key="reg_pass", autocomplete="new-password")
            new_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2", autocomplete="new-password")
            if st.button("Create Account", use_container_width=True, type="primary"):
                if new_user and new_pass and new_pass2:
                    if new_pass != new_pass2:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = register_user(new_user, new_pass)
                        if ok:
                            st.success(msg + " Please login.")
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill in all fields.")

def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon="📚", layout="wide")
    st.write(css, unsafe_allow_html=True)

    for key, val in {
        "logged_in": False, "user_id": None, "username": None,
        "conversation": None, "chat_history": None, "input_key": 0
    }.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if not st.session_state.logged_in:
        show_auth_page()
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("# 📚 Chat with Multiple PDFs")
        st.markdown(f"👤 Logged in as **{st.session_state.username}**")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.markdown("---")

    if st.session_state.chat_history:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for i, message in enumerate(st.session_state.chat_history):
            if i % 2 == 0:
                st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            else:
                st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if st.session_state.conversation:
            st.info("💬 Your PDFs are ready! Ask a question below.")
        else:
            st.info("👈 Upload PDFs from the sidebar, save them to your library, then select and process them to start chatting.")

    input_container = st.container()
    with input_container:
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_question = st.text_input(
                "question",
                placeholder="Ask a question about your documents...",
                key=f"q_{st.session_state.input_key}",
                label_visibility="collapsed"
            )
        with col_btn:
            send_clicked = st.button("Send 📨", use_container_width=True, type="primary")

    if send_clicked:
        if not user_question.strip():
            st.warning("Please type a question first.")
        elif not st.session_state.conversation:
            st.warning("Please select and process PDFs from your library first!")
        else:
            with st.spinner("Thinking..."):
                handle_userinput(user_question)
            st.session_state.input_key += 1
            st.rerun()

    st.markdown("""
    <script>
    function moveInputToBottom() {
        const inputRow = window.parent.document.querySelectorAll('.stHorizontalBlock');
        if (inputRow.length > 0) {
            const lastRow = inputRow[inputRow.length - 1];
            lastRow.style.position = 'fixed';
            lastRow.style.bottom = '0';
            lastRow.style.left = '320px';
            lastRow.style.right = '0';
            lastRow.style.background = 'white';
            lastRow.style.padding = '14px 24px';
            lastRow.style.borderTop = '1px solid #e0e0e0';
            lastRow.style.zIndex = '999';
            lastRow.style.boxShadow = '0 -2px 12px rgba(0,0,0,0.06)';
        }
    }
    setTimeout(moveInputToBottom, 300);
    </script>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 📤 Add New PDFs")
        st.caption("Upload PDFs here to save them permanently to your library")
        uploaded_files = st.file_uploader(
            "Choose PDF files", type="pdf", accept_multiple_files=True, key="uploader"
        )
        if st.button("💾 Save to Library", use_container_width=True, type="primary"):
            if uploaded_files:
                with st.spinner("Saving & generating summaries..."):
                    for uf in uploaded_files:
                        pdf_bytes = uf.getvalue()
                        pages = get_page_count_from_bytes(pdf_bytes)
                        text = get_pdf_text_from_bytes(pdf_bytes)
                        summary = generate_summary(text)
                        save_pdf(st.session_state.user_id, uf, pages, summary)
                st.success(f"✅ {len(uploaded_files)} PDF(s) saved!")
                st.rerun()
            else:
                st.warning("Please select files first.")

        st.markdown("---")

        st.markdown("## 📚 Your PDF Library")
        st.caption("Tick PDFs you want to chat with, then click Process")
        pdfs = get_user_pdfs(st.session_state.user_id)

        if not pdfs:
            st.info("No PDFs yet. Upload some above!")
        else:
            selected = []
            for pdf_id, filename, file_size, page_count, summary, uploaded_at in pdfs:
                col1, col2 = st.columns([0.12, 0.88])
                with col1:
                    checked = st.checkbox("", key=f"chk_{pdf_id}")
                    if checked:
                        selected.append(filename)
                with col2:
                    size_kb = round(file_size / 1024, 1) if file_size else 0
                    st.markdown(f"**{filename}**")
                    st.caption(f"📄 {page_count} pages · {size_kb} KB · {uploaded_at[:10]}")
                    if summary:
                        with st.expander("📝 Summary"):
                            st.write(summary)
                    if st.button("🗑️ Delete", key=f"del_{pdf_id}"):
                        delete_pdf(st.session_state.user_id, pdf_id)
                        st.rerun()
                st.markdown("---")

            if selected:
                st.success(f"✅ {len(selected)} PDF(s) selected")
            if st.button("⚡ Process Selected PDFs", use_container_width=True, type="primary", disabled=len(selected) == 0):
                with st.spinner("Building knowledge base..."):
                    all_text = ""
                    for fname in selected:
                        pdf_bytes = get_pdf_bytes(st.session_state.user_id, fname)
                        if pdf_bytes:
                            all_text += get_pdf_text_from_bytes(pdf_bytes)
                    chunks = get_text_chunks(all_text)
                    vectorstore = get_vectorstore(chunks)
                    st.session_state.conversation = get_conversation_chain(vectorstore)
                    st.session_state.chat_history = None
                st.success("✅ Ready! Ask your questions.")


if __name__ == '__main__':
    main()
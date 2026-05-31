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
    save_message, export_chat
)

load_dotenv()
init_db()


# ── These are your original functions, unchanged ──────────────────────────────

def get_pdf_text(pdf_docs):
    """Original function — reads from uploaded file objects."""
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_pdf_text_from_bytes(pdf_bytes):
    """New function — reads from bytes stored in DB."""
    text = ""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def get_page_count_from_bytes(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    return text_splitter.split_text(text)


def get_vectorstore(text_chunks):
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return FAISS.from_texts(texts=text_chunks, embedding=embeddings)


def get_conversation_chain(vectorstore):
    llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.3-70b-versatile")
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )


def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            save_message(st.session_state.user_id, "user", message.content)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            save_message(st.session_state.user_id, "assistant", message.content)


def generate_summary(text):
    """Generate a short summary using Groq."""
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


# ── Auth Page ─────────────────────────────────────────────────────────────────

def show_auth_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 📚 Chat with Multiple PDFs")
        st.markdown("---")
        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
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
            new_user = st.text_input("Choose a username", key="reg_user")
            new_pass = st.text_input("Choose a password (min 6 chars)", type="password", key="reg_pass")
            new_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2")
            if st.button("Create Account", use_container_width=True):
                if new_user and new_pass and new_pass2:
                    if new_pass != new_pass2:
                        st.error("Passwords don't match.")
                    else:
                        ok, msg = register_user(new_user, new_pass)
                        if ok:
                            st.success(msg + " Please login.")
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill in all fields.")


# ── Main App (your original app + new features) ───────────────────────────────

def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    # Session state init
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    # Show login page if not logged in
    if not st.session_state.logged_in:
        show_auth_page()
        return

    # ── Your original header & chat input ────────────────────────────────────
    st.header("Chat with multiple PDFs :books:")

    # Logout button top right
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with col1:
        st.markdown(f"👤 Logged in as **{st.session_state.username}**")

    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        if st.session_state.conversation:
            handle_userinput(user_question)
        else:
            st.warning("Please select and process PDFs from your library first!")

    # Export chat history button
    if st.session_state.chat_history:
        export_text = export_chat(st.session_state.user_id)
        st.download_button(
            "⬇️ Export Chat History",
            data=export_text,
            file_name="chat_history.txt",
            mime="text/plain"
        )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:

        # ── Section 1: Upload new PDFs to library ────────────────────────────
        st.subheader("📤 Upload to Library")
        uploaded_files = st.file_uploader(
            "Upload PDFs to save to your library",
            accept_multiple_files=True,
            key="uploader"
        )
        if st.button("Save to Library"):
            if uploaded_files:
                with st.spinner("Saving PDFs..."):
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

        # ── Section 2: PDF Library — select & process ────────────────────────
        st.subheader("📚 Your PDF Library")
        pdfs = get_user_pdfs(st.session_state.user_id)

        if not pdfs:
            st.info("No PDFs yet. Upload some above!")
        else:
            selected = []
            for pdf_id, filename, file_size, page_count, summary, uploaded_at in pdfs:
                col1, col2 = st.columns([0.15, 0.85])
                with col1:
                    checked = st.checkbox("", key=f"chk_{pdf_id}")
                    if checked:
                        selected.append(filename)
                with col2:
                    size_kb = round(file_size / 1024, 1) if file_size else 0
                    st.markdown(f"**{filename}**")
                    st.caption(f"{page_count} pages · {size_kb} KB · {uploaded_at[:10]}")
                    if summary:
                        with st.expander("📝 Summary"):
                            st.write(summary)
                    if st.button("🗑️", key=f"del_{pdf_id}", help="Delete this PDF"):
                        delete_pdf(st.session_state.user_id, pdf_id)
                        st.rerun()

            if selected:
                if st.button("⚡ Process Selected PDFs", use_container_width=True, type="primary"):
                    with st.spinner("Processing..."):
                        all_text = ""
                        for fname in selected:
                            pdf_bytes = get_pdf_bytes(st.session_state.user_id, fname)
                            if pdf_bytes:
                                all_text += get_pdf_text_from_bytes(pdf_bytes)
                        text_chunks = get_text_chunks(all_text)
                        vectorstore = get_vectorstore(text_chunks)
                        st.session_state.conversation = get_conversation_chain(vectorstore)
                        st.session_state.chat_history = None
                    st.success("✅ Done! Ask your questions above.")


if __name__ == '__main__':
    main()
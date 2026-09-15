import streamlit as st
from openai import OpenAI
import sys

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

from pathlib import Path
from pypdf import PdfReader


st.title("Lab 4 - Chatbot using RAG")

st.write(
    "This chatbot uses a ChromaDB vector database containing the provided PDF files. "
    "When you ask a question, the app searches the database for the most relevant "
    "documents and gives that information to the chatbot as additional context."
)


if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


def add_to_collection(collection, text, file_name):

    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )

    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[file_name],
        embeddings=[embedding],
        metadatas=[
            {
                "filename": file_name
            }
        ]
    )


def extract_text_from_pdf(pdf_path):

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def load_pdfs_to_collection(folder_path, collection):

    folder = Path(folder_path)

    pdf_files = list(folder.glob("*.pdf"))

    for pdf_file in pdf_files:

        text = extract_text_from_pdf(pdf_file)

        if text:

            add_to_collection(
                collection,
                text,
                pdf_file.name
            )

    return len(pdf_files)


def create_vector_db():

    chroma_client = chromadb.PersistentClient(
        path="./ChromaDB_for_Lab"
    )

    collection = chroma_client.get_or_create_collection(
        "Lab4Collection"
    )

    if collection.count() == 0:

        load_pdfs_to_collection(
            "./Lab-04-Data/",
            collection
        )

    return collection


if "Lab4_VectorDB" not in st.session_state:

    st.session_state.Lab4_VectorDB = create_vector_db()


collection = st.session_state.Lab4_VectorDB


def get_info_from_vectorDB(collection, prompt):

    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=prompt,
        model="text-embedding-3-small"
    )

    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    extra_info = ""

    for i in range(len(results["documents"][0])):

        document = results["documents"][0][i]

        file_name = results["ids"][0][i]

        extra_info += (
            f"\nDocument: {file_name}\n"
            f"{document}\n"
        )

    return extra_info


topic = st.sidebar.text_input(
    "Topic",
    placeholder="Type your topic"
)


if topic:

    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=topic,
        model="text-embedding-3-small"
    )

    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    st.sidebar.subheader(
        f"Results for: {topic}"
    )

    for i in range(len(results["documents"][0])):

        doc_id = results["ids"][0][i]

        st.sidebar.write(
            f"{i + 1}. {doc_id}"
        )


if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Use the provided document context when answering questions."
            )
        },
        {
            "role": "assistant",
            "content": "How can I help you?"
        }
    ]


for msg in st.session_state.messages:

    if msg["role"] != "system":

        chat_msg = st.chat_message(
            msg["role"]
        )

        chat_msg.write(
            msg["content"]
        )


def get_conversation_buffer(messages):

    system_message = messages[0]

    conversation_messages = messages[1:]

    conversation_buffer = conversation_messages[-6:]

    return [system_message] + conversation_buffer


model_to_use = "gpt-5-nano"


if prompt := st.chat_input("Ask a question about the documents"):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):

        st.markdown(prompt)


    extra_info = get_info_from_vectorDB(
        st.session_state.Lab4_VectorDB,
        prompt
    )


    messages_to_send = get_conversation_buffer(
        st.session_state.messages
    )


    messages_to_send.insert(
        1,
        {
            "role": "system",
            "content": (
                "Use the following context to answer the user's question:\n\n"
                + extra_info
            )
        }
    )


    stream = st.session_state.openai_client.chat.completions.create(
        model=model_to_use,
        messages=messages_to_send,
        stream=True
    )


    with st.chat_message("assistant"):

        response = st.write_stream(stream)


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )
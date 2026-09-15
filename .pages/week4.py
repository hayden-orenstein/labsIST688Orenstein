import streamlit as st
from openai import OpenAI
import sys
from pathlib import Path
from pypdf import PdfReader

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb


st.title("Lab 4 - Course Information Chatbot")

st.write(
    "Ask questions about the course information contained in the provided documents. "
    "The chatbot searches the documents for information related to your question and "
    "uses the most relevant documents as context when creating its answer."
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

    source_files = []

    for i in range(len(results["documents"][0])):

        document = results["documents"][0][i]

        file_name = results["ids"][0][i]

        source_files.append(file_name)

        extra_info += (
            f"\nDOCUMENT: {file_name}\n"
            f"{document}\n"
        )

    return extra_info, source_files


if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful course information chatbot. "
                "When information from the retrieved course documents is "
                "provided, use that information to answer the user's question. "
                "Be clear when your answer uses information retrieved from "
                "the course documents."
            )
        },
        {
            "role": "assistant",
            "content": "How can I help you with your course information?"
        }
    ]


for msg in st.session_state.messages:

    if msg["role"] != "system":

        chat_msg = st.chat_message(msg["role"])

        chat_msg.write(msg["content"])


def get_conversation_buffer(messages):

    system_message = messages[0]

    conversation_messages = messages[1:]

    conversation_buffer = conversation_messages[-6:]

    return [system_message] + conversation_buffer


model_to_use = "gpt-5-nano"


if prompt := st.chat_input("Ask a question about the course"):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    with st.chat_message("user"):

        st.markdown(prompt)


    extra_info, source_files = get_info_from_vectorDB(
        st.session_state.Lab4_VectorDB,
        prompt
    )


    messages_to_send = get_conversation_buffer(
        st.session_state.messages
    )


    rag_prompt = {
        "role": "system",
        "content": (
            "Use the following retrieved course document information "
            "to answer the user's question.\n\n"
            "If the retrieved information supports your answer, make it clear "
            "that you are using information from the course documents. "
            "If the answer cannot be found in the retrieved information, "
            "say that you could not find the answer in the retrieved course "
            "documents. Do not make up course information.\n\n"
            f"{extra_info}"
        )
    }


    messages_to_send.insert(
        1,
        rag_prompt
    )


    stream = st.session_state.openai_client.chat.completions.create(
        model=model_to_use,
        messages=messages_to_send,
        stream=True
    )


    with st.chat_message("assistant"):

        response = st.write_stream(stream)

        source_text = (
            "\n\n**Documents used:** "
            + ", ".join(source_files)
        )

        st.markdown(source_text)


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response + source_text
        }
    )
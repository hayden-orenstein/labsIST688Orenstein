import streamlit as st
from openai import OpenAI
import sys
from pathlib import Path
from pypdf import PdfReader
import pysqlite3

sys.modules["sqlite3"] = pysqlite3

import chromadb


st.title("Lab 4 - Course Information Chatbot")

st.write(
    "Ask questions about the courses contained in the provided syllabi. "
    "This chatbot uses a ChromaDB vector database to retrieve course information. "
    "Answers about the courses are based only on the information contained in the "
    "provided documents."
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


def get_info_from_vector_db(collection, question):

    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )

    query_embedding = response.data[0].embedding


    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=collection.count(),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )


    context = ""


    for i in range(len(results["documents"][0])):

        document = results["documents"][0][i]

        metadata = results["metadatas"][0][i]

        file_name = metadata["filename"]


        context += (
            f"\n\nDOCUMENT NAME: {file_name}\n"
            f"DOCUMENT CONTENT:\n"
            f"{document}\n"
        )


    return context


if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "How can I help you with your course information?"
        }
    ]


for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])


if prompt := st.chat_input(
    "Ask a question about the courses"
):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    with st.chat_message("user"):

        st.write(prompt)


    course_context = get_info_from_vector_db(
        st.session_state.Lab4_VectorDB,
        prompt
    )


    system_prompt = (
        "You are a course information chatbot.\n\n"

        "The course syllabi from the vector database are provided below.\n\n"

        "For questions about the courses, ONLY use information that appears "
        "in these documents. Do not make up course information and do not use "
        "outside knowledge about these courses.\n\n"

        "Use only the document or documents that are relevant to the user's "
        "question.\n\n"

        "If the user asks about one specific course, use only the syllabus "
        "for that course when answering.\n\n"

        "If the user asks about multiple courses, use the syllabi for those "
        "courses.\n\n"

        "If the user asks about all courses, every course, or requests a "
        "comparison involving all of the courses, examine all of the provided "
        "syllabi and use all documents needed to answer completely.\n\n"

        "If the requested information cannot be found in the documents, clearly "
        "tell the user that the information was not found in the provided syllabi.\n\n"

        "At the very bottom of every answer that uses information from the "
        "syllabi, write 'Documents used:' followed by the exact filename or "
        "filenames of ONLY the documents whose information you actually used.\n\n"

        "Do not create labels such as SOURCE_1 or SOURCE_2. "
        "Always use the real document filename.\n\n"

        "COURSE DOCUMENTS:\n"
        + course_context
    )


    messages_to_send = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]


    messages_to_send += st.session_state.messages


    response = (
        st.session_state.openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages_to_send
        )
    )


    answer = response.choices[0].message.content


    with st.chat_message("assistant"):

        st.write(answer)


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
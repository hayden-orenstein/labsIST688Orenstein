import streamlit as st
from openai import OpenAI
import sys
import re
from pathlib import Path
from pypdf import PdfReader


__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb


st.title("Lab 4 - Course Information Chatbot")

st.write(
    "Ask questions about the course information contained in the provided syllabi. "
    "The chatbot uses a ChromaDB vector database to access the course documents. "
    "The documents used to answer each question are listed below the response."
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

    existing_data = collection.get()

    existing_ids = existing_data["ids"]


    for pdf_file in pdf_files:

        if pdf_file.name not in existing_ids:

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

    number_of_documents = collection.count()

    if number_of_documents == 0:

        return "", {}


    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=number_of_documents
    )


    extra_info = ""

    source_map = {}


    for i in range(len(results["documents"][0])):

        document = results["documents"][0][i]

        file_name = results["ids"][0][i]

        source_label = f"SOURCE_{i + 1}"


        source_map[source_label] = file_name


        extra_info += (
            f"\n{source_label}\n"
            f"FILENAME: {file_name}\n"
            f"CONTENT:\n{document}\n\n"
        )


    return extra_info, source_map


if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful course syllabus information chatbot. "
                "Answer questions using the provided course documents whenever "
                "the answer can be found in them. Do not make up course information."
            )
        },
        {
            "role": "assistant",
            "content": "How can I help you with your course information?",
            "sources": [],
            "show_sources": False
        }
    ]


for msg in st.session_state.messages:

    if msg["role"] != "system":

        with st.chat_message(msg["role"]):

            st.write(msg["content"])


            if msg.get("show_sources", False):

                sources = msg.get("sources", [])


                if sources:

                    st.markdown(
                        "**Documents used:** "
                        + ", ".join(sources)
                    )


def get_conversation_buffer(messages):

    system_message = {
        "role": messages[0]["role"],
        "content": messages[0]["content"]
    }


    conversation_messages = messages[1:]

    conversation_buffer = conversation_messages[-6:]


    clean_buffer = []


    for msg in conversation_buffer:

        clean_buffer.append(
            {
                "role": msg["role"],
                "content": msg["content"]
            }
        )


    return [system_message] + clean_buffer


model_to_use = "gpt-5-nano"


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

        st.markdown(prompt)


    extra_info, source_map = get_info_from_vectorDB(
        st.session_state.Lab4_VectorDB,
        prompt
    )


    messages_to_send = get_conversation_buffer(
        st.session_state.messages
    )


    rag_prompt = {
        "role": "system",
        "content": (
            "Use the course documents below to answer the user's current question.\n\n"

            "All of the supplied course documents are available to you for this "
            "question. Examine whichever documents are necessary before deciding "
            "that information is unavailable.\n\n"

            "Do not make up course information.\n\n"

            "The labels SOURCE_1, SOURCE_2, and so on are INTERNAL identifiers only. "
            "NEVER mention these SOURCE labels in the answer that the user reads.\n\n"

            "After completely finishing your answer, add one final line in this "
            "exact format:\n\n"

            "SOURCES_USED: SOURCE_1\n\n"

            "If you actually used multiple documents, use this format:\n\n"

            "SOURCES_USED: SOURCE_1 | SOURCE_3 | SOURCE_5\n\n"

            "Only include a source if information from that document actually "
            "contributed to your answer.\n\n"

            "If none of the documents supplied useful information, write:\n\n"

            "SOURCES_USED: NONE\n\n"

            "Do not write 'Source:', 'SOURCE_1', or any other internal source "
            "identifier anywhere in the visible answer. The SOURCES_USED line "
            "must be the final line only.\n\n"

            "COURSE DOCUMENTS:\n\n"
            + extra_info
        )
    }


    messages_to_send.insert(
        1,
        rag_prompt
    )


    completion = (
        st.session_state.openai_client.chat.completions.create(
            model=model_to_use,
            messages=messages_to_send
        )
    )


    full_response = completion.choices[0].message.content


    used_sources = []


    if "SOURCES_USED:" in full_response:

        response, source_line = full_response.rsplit(
            "SOURCES_USED:",
            1
        )

        response = response.strip()


        source_labels = re.findall(
            r"SOURCE_\d+",
            source_line.upper()
        )


        for source_label in source_labels:

            if source_label in source_map:

                file_name = source_map[source_label]

                if file_name not in used_sources:

                    used_sources.append(
                        file_name
                    )

    else:

        response = full_response.strip()


    response = re.sub(
        r'(?i)\bsource\s*:\s*SOURCE_\d+[.,]?',
        '',
        response
    )


    response = re.sub(
        r'\bSOURCE_\d+\b[.,]?',
        '',
        response
    )


    response = re.sub(
        r'\n\s*\n\s*\n+',
        '\n\n',
        response
    )


    response = response.strip()


    with st.chat_message("assistant"):

        st.write(response)


        if used_sources:

            st.markdown(
                "**Documents used:** "
                + ", ".join(used_sources)
            )


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "sources": used_sources,
            "show_sources": True
        }
    )
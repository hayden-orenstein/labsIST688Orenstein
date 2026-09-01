import streamlit as st
from openai import OpenAI, AuthenticationError
from pypdf import PdfReader


# Function to read PDF files
def read_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)

    document = ""

    for page in reader.pages:
        text = page.extract_text()

        if text:
            document += text + "\n"

    return document


st.title("MY Lab 2 Document Question Answering")

st.write(
    "Upload a document and select how you would like GPT to summarize it."
)


try:
    # Get OpenAI API key from Streamlit secrets
    openai_api_key = st.secrets["OPENAI_API_KEY"]

    # Create OpenAI client
    client = OpenAI(api_key=openai_api_key)


    # Sidebar options
    st.sidebar.header("Summary Options")

    summary_option = st.sidebar.radio(
        "Select summary instructions:",
        [
            "Summarize the document in 100 words",
            "Summarize the document in 2 connecting paragraphs",
            "Summarize the document in 5 bullet points"
        ]
    )


    # Model selection
    advanced_model = st.sidebar.checkbox(
        "Select the more advanced model"
    )


    if advanced_model:
        model = "gpt-5-mini"
    else:
        model = "gpt-5-nano"


    # Upload file
    uploaded_file = st.file_uploader(
        "Upload a document (.txt, .md, or .pdf)",
        type=("txt", "md", "pdf")
    )


    # Run button
    run_button = st.button(
        "Run",
        disabled=uploaded_file is None
    )


    if run_button:

        # Determine file type
        file_extension = uploaded_file.name.split(".")[-1].lower()


        # Read TXT or Markdown files
        if file_extension in ["txt", "md"]:
            document = uploaded_file.read().decode()


        # Read PDF files
        elif file_extension == "pdf":
            document = read_pdf(uploaded_file)


        else:
            st.error("Unsupported file type.")
            st.stop()


        # Make sure the document contains readable text
        if not document.strip():
            st.error("No readable text was found in the document.")
            st.stop()


        # Create messages for GPT
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a document summarization assistant. "
                    f"{summary_option}. "
                    "Only use information contained in the provided document. "
                    "Do not add information that is not present in the document."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Here is the document:\n\n"
                    f"{document}"
                )
            }
        ]


        # Generate response
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )


        # Display summary
        st.subheader("Summary")

        st.write_stream(stream)


except KeyError:
    st.error(
        "OPENAI_API_KEY was not found in your Streamlit secrets."
    )


except AuthenticationError:
    st.error(
        "The OpenAI API key in your Streamlit secrets is invalid."
    )
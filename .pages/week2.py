import streamlit as st
from openai import OpenAI, AuthenticationError


st.title("MY Lab 2 Document Question Answering")

st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
    "To use this app, you need to provide an OpenAI API key, which you can get "
    "[here](https://platform.openai.com/account/api-keys)."
)

# Ask user for OpenAI API key
openai_api_key = st.text_input(
    "OpenAI API Key",
    type="password"
)

if not openai_api_key:
    st.info(
        "Please add your OpenAI API key to continue.",
        icon="🗝️"
    )

else:
    try:
        # Create OpenAI client
        client = OpenAI(api_key=openai_api_key)

        # Verify API key
        client.models.list()

        st.success("API key verified!")

        # Upload document
        uploaded_file = st.file_uploader(
            "Upload a document (.txt or .md)",
            type=("txt", "md")
        )

        # Ask question
        question = st.text_area(
            "Now ask a question about the document!",
            placeholder="Can you give me a short summary?",
            disabled=not uploaded_file,
        )

        if uploaded_file and question:

            # Read document
            document = uploaded_file.read().decode()

            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Here's a document:\n\n"
                        f"{document}\n\n"
                        f"---\n\n"
                        f"{question}"
                    ),
                }
            ]

            # Generate response
            stream = client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages,
                stream=True,
            )

            # Display streamed response
            st.write_stream(stream)

    except AuthenticationError:
        st.error(
            "Invalid OpenAI API key. Please check your key and try again."
        )
import streamlit as st
from openai import OpenAI


st.title("Lab 3 - Streaming Chatbot  (turn based limit)")


if "client" not in st.session_state:
    st.session_state.client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


model_to_use = "gpt-5-nano"


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": """
            Answer all questions using language that a 10-year-old understands.

            After answering a user's question, always ask:
            "Do you want more info?"

            If the user says "Yes", provide more information about the
            previous answer and then ask "Do you want more info?" again.

            If the user says "No", ask the user what esle you can help them with.
            """
        },
        {
            "role": "assistant",
            "content": "How can I help you?"
        }
    ]


# Display conversation history
for msg in st.session_state.messages:

    # Do not display the system prompt to the user
    if msg["role"] != "system":

        chat_msg = st.chat_message(msg["role"])

        chat_msg.write(msg["content"])


def get_conversation_buffer(messages):

    user_indices = []

    for i in range(len(messages)):
        if messages[i]["role"] == "user":
            user_indices.append(i)


    # If there are 2 or fewer user messages,
    # keep the whole conversation
    if len(user_indices) <= 2:
        return messages


    # Find the second-most-recent user message
    start_index = user_indices[-2]


    # ALWAYS keep the system message
    system_message = messages[0]


    # Add system message + last 2 conversations
    return [system_message] + messages[start_index:]


if prompt := st.chat_input("What is up?"):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    # Display user's message
    with st.chat_message("user"):
        st.markdown(prompt)


    messages_to_send = get_conversation_buffer(
        st.session_state.messages
    )


    stream = st.session_state.client.chat.completions.create(
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
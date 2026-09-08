import streamlit as st
from openai import OpenAI


st.title("Lab 3 - Streaming Chatbot")


if "client" not in st.session_state:
    st.session_state.client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


model_to_use = "gpt-5-nano"

if "messages" not in st.session_state:
    st.session_state.messages = \
        [{"role": "assistant", "content": "How can I help you?"}]


for msg in st.session_state.messages:

    chat_msg = st.chat_message(msg["role"])

    chat_msg.write(msg["content"])


def get_conversation_buffer(messages):

    user_indices = []

    for i in range(len(messages)):
        if messages[i]["role"] == "user":
            user_indices.append(i)


    if len(user_indices) <= 2:
        return messages

    start_index = user_indices[-2]

    return messages[start_index:]


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
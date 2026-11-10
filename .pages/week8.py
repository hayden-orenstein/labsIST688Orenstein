
import base64
from pathlib import Path
import streamlit as st
from openai import OpenAI

st.title("Lab 8 - See and Hear Assistant")

st.write(
    "Upload an image or audio file to receive a summary, "
    "three key points, and answers to questions about the content."
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def prepare_image(upload):
    formats = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }
    mime = formats[Path(upload.name).suffix.lower()]
    encoded = base64.b64encode(upload.getvalue()).decode("utf-8")
    return {
        "type": "input_image",
        "image_url": f"data:{mime};base64,{encoded}"
    }


def transcribe_audio(upload):
    transcript = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=(upload.name, upload.getvalue())
    )
    return transcript.text


def analyze_content(content, prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        instructions=prompt,
        input=[{"role": "user", "content": content}],
        max_output_tokens=600
    )
    return response.output_text


system_prompt = """
You are a helpful assistant that analyzes uploaded images and audio transcripts.

Use only the information provided in the uploaded material.
Do not use outside knowledge to fill in missing information.

First, provide a short summary of the uploaded content.
Then, identify three important key points.

If the user asks a question, answer it using evidence from the uploaded material.
If the answer cannot be determined from the material, clearly say that
the information is not available in the uploaded content.

For images, describe relevant visual details, text, charts, or diagrams.
For audio, focus on what was actually said in the transcript.

Do not invent details or make assumptions about unclear information.
Keep responses organized, concise, and easy to understand.
"""


file_type = st.radio(
    "Choose upload type",
    ["Image", "Audio"],
    horizontal=True
)

if file_type == "Image":
    uploaded_file = st.file_uploader(
        "Upload an image",
        type=["png", "jpg", "jpeg"]
    )
else:
    uploaded_file = st.file_uploader(
        "Upload an audio file",
        type=["mp3", "wav", "m4a"]
    )

question = st.text_input(
    "Optional question about the uploaded content",
    placeholder="What is the main point of this material?"
)

if uploaded_file is not None:
    if uploaded_file.size > 5 * 1024 * 1024:
        st.error("The file must be 5 MB or smaller.")
    else:
        if file_type == "Image":
            st.image(uploaded_file)
        else:
            st.audio(uploaded_file)

if st.button("Analyze"):
    if uploaded_file is None:
        st.warning("Please upload an image or audio file first.")

    elif uploaded_file.size > 5 * 1024 * 1024:
        st.error("The file must be 5 MB or smaller.")

    else:
        try:
            with st.spinner("Analyzing your upload..."):
                if file_type == "Image":
                    content = [
                        {
                            "type": "input_text",
                            "text": (
                                question.strip()
                                if question.strip()
                                else "Summarize this image and identify three key points."
                            )
                        },
                        prepare_image(uploaded_file)
                    ]

                else:
                    transcript = transcribe_audio(uploaded_file)

                    with st.expander("Audio Transcript", expanded=True):
                        st.write(transcript)

                    content = [
                        {
                            "type": "input_text",
                            "text": (
                                f"Audio transcript:\n{transcript}\n\n"
                                f"User question: "
                                f"{question.strip() if question.strip() else 'Summarize this audio and identify three key points.'}"
                            )
                        }
                    ]

                answer = analyze_content(content, system_prompt)

            st.subheader("Analysis")
            st.write(answer)

        except Exception as e:
            st.error(f"Error: {e}")


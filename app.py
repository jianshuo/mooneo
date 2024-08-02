from openai import AzureOpenAI
import dotenv
import os
import streamlit as st
import urllib
import re
from audio_recorder_streamlit import audio_recorder
import tempfile


SHOW_VIDEO = "SHOW_VIDEO"
dotenv.load_dotenv()

client = AzureOpenAI(
    azure_endpoint=st.secrets["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=st.secrets["AZURE_OPENAI_CHATGPT_DEPLOYMENT"],
    api_key=st.secrets["AZURE_OPENAI_KEY"],
    api_version=st.secrets["AZURE_OPENAI_API_VERSION"],
)

whisper_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)


if "messages" not in st.session_state:
    st.session_state.messages = []

# for message in st.session_state.messages[-1:]:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])


with st.sidebar:
    st.title("Awesome AI English Teacher")
    audio_bytes = audio_recorder()
    st.write("or")
    text_prompt = st.chat_input("Enter your message")
    with st.expander("Settings"):
        repeat = st.slider("Repeat - How many time the word is repeated", 1, 5)
        padding = st.slider(
            "Padding - How many clips before and after the word is included", 0, 5
        )

if audio_bytes or text_prompt:
    if audio_bytes:
        # st.audio(audio_bytes, format="audio/wav", autoplay=True)
        deployment_id = "wisper"  # This will correspond to the custom name you chose for your deployment when you deployed a model."

        # Save the recorded audio to a temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".wav"
        ) as temp_audio_file:
            temp_audio_file.write(audio_bytes)
            temp_audio_path = temp_audio_file.name

        result = whisper_client.audio.transcriptions.create(
            file=open(temp_audio_path, "rb"), model="wisper"
        )

        # Remove temporary file
        os.remove(temp_audio_path)

    prompt = text_prompt or result.text

    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.messages.append(
        {
            "role": "system",
            "content": f"""
            You are an English teacher. You find an innovative way 
            to teach English. Whenever you want to teach user a new word
            or phrase, you can show a video clip containing the word or phrase.
            Youc an just use {SHOW_VIDEO}: word or {SHOW_VIDEO}: phrase to show the video
            to the user. For example, if you want to teach students word "hola",
            you should say: {SHOW_VIDEO}: hola. The video will be shown to the user.
            When you show a word using the video, please also provide Chinese
            explaination of the meaning. Please also make sure
            you only output not more than 3 videos. 
            """,
        }
    )
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        messages=st.session_state.messages,
        model="gpt-4o",
    )

    with st.chat_message("assistant"):
        reply = response.choices[0].message.content
        for line in reply.splitlines():
            st.write(line)
            if match := re.search(f"{SHOW_VIDEO}:.*", line):
                term = line.replace(SHOW_VIDEO + ":", "")
                st.video(
                    "https://video.chato.cn/m3u8/"
                    + urllib.parse.quote(term)
                    + f".m3u8?repeat={repeat}&padding={padding}",
                    autoplay=False,
                    loop=True,
                )

    st.session_state.messages.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )

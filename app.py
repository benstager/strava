import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

st.set_page_config(page_title="Chat", layout="centered")

st.header("Strava Analyst")
st.subheader("An app designed by Benjamin Stager to communicate with his 2025 running data.")

with open("formatted_strs.txt", "r") as file:
    context = file.read()

llm = ChatOpenAI(
    model="gpt-5.1",
    max_completion_tokens=16000,
    streaming=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

def stream_response(messages):
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content

# render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    messages = [
        SystemMessage(
            content=(
                "You are a Strava workout analysis assistant. "
                "Don't tell me how detailed my runs are or anything. JUST BE READY TO ASSIST. DO NOT TELL ME HOW GREAT THE LOG IS JUST BE READY TO ANSWER ANY QUESTION"
                "The user's name is Ben."
                "Answer concisely and factually.\n\n"
                "You are to serve every request accurately. You are not to suggest additional analysis or suggestions."
                "Often times there will be a song of the day and description. Try to reference this as well"
                "Don't just spit out the data, try to do an analysis with it, or craft some sort of narrative around it."
                f"Dataset:\n{context}"
            )
        ),
        HumanMessage(content=user_input),
    ]

    with st.chat_message("assistant"):
        placeholder = st.empty()
        streamed_text = ""

        for chunk in stream_response(messages):
            streamed_text += chunk
            placeholder.markdown(streamed_text)

    st.session_state.messages.append(
        {"role": "assistant", "content": streamed_text}
    )

    # keep last 4 turns
    st.session_state.messages = st.session_state.messages[-8:]

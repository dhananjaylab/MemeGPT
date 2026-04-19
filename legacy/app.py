import streamlit as st

from get_meme import generate_memes


if "images" not in st.session_state:
    st.session_state.images = []

if 'run_button' in st.session_state and st.session_state.run_button == True:
    st.session_state.running = True
else:
    st.session_state.running = False


def delete_image(image_path):
    st.session_state.images = [
        img for img in st.session_state.images if img != image_path
    ]


st.set_page_config(
    page_title="Meme Generator",
    page_icon="🧙",
    layout="wide",
)

st.title("Welcome to the Meme Generator! 🧙")
st.write(
    "##### Please provide a situation or a topic to generate a meme. You can provide a short topic or paste in a whole story or article."
)

user_input = st.text_area("Situation, topic or article:", height=200)

if st.button("Generate Memes", disabled=st.session_state.running, key='run_button'):
    print("Generating memes...")
    new_images = generate_memes(user_input)
    if new_images:
        st.session_state.images = new_images + st.session_state.images
    st.rerun()

num_columns = 4
columns = st.columns(num_columns)
for index, image_path in enumerate(st.session_state.images):
    with columns[index % num_columns]:
        st.image(str(image_path), use_container_width=True)
        if st.button(
            "🗑️ Delete",
            key=f"delete_{index}",
            on_click=lambda image=image_path: delete_image(image),
        ):
            print("Deleting image...")

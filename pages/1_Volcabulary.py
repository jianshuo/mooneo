import streamlit as st
import os
import urllib

files = [file for file in os.listdir("dicts") if file.endswith(".txt")]
files = sorted(files)

data = {}


def get_terms(raw):
    results = {}
    for line in raw.splitlines():
        if len(line) < 5:
            continue
        term, *meaning = line.split("	")
        results[term] = " ".join(meaning)
    return results


st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.subheader("Please click on the button on the left to play the video")

repeat = 1
padding = 0


def show_video(term):
    st.video(
        f"https://video.chato.cn/m3u8/{urllib.parse.quote(term)}.m3u8?repeat={repeat}&padding={padding}",
        autoplay=True,
        loop=True,
    )


with st.sidebar:
    vocab_tab, search_tab, setting_tab = st.tabs(["词汇", "搜索", "设置"])
    with vocab_tab:
        level = st.selectbox("单词表", files)
        letter = st.selectbox(
            "单词开头",
            (
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
                "K",
                "L",
                "M",
                "N",
                "O",
                "P",
                "Q",
                "R",
                "S",
                "T",
                "U",
                "V",
                "W",
                "X",
                "Y",
                "Z",
            ),
        )

        index = 0
        for term, meaning in get_terms(open("dicts/" + level).read()).items():
            if term.upper().startswith(letter):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.button(
                        f"{term}",
                        key=term + str(index),
                        on_click=show_video,
                        args=[term],
                    )
                with col2:
                    st.write(f"{meaning[0:30]}")
                index += 1
    with search_tab:
        search_term = st.text_input("Search")
        show_video(search_term)
    with setting_tab:
        repeat = st.slider("How many times you want the video to repeat?", 1, 10)
        padding = st.slider("Context", 0, 3)


# import json
# import random

# cards = []
# for file in files:

#     title = file.replace(".txt", "")
#     terms = [
#         "worthless",
#         "worthwhile",
#         "worthy",
#         "would",
#         "wound",
#         "wrap",
#         "wreath",
#         "wreck",
#         "wrist",
#         "write",
#         "writer",
#         "writing",
#         "winner",
#         "winter",
#         "wipe",
#         "wire",
#         "wireless",
#         "wisdom",
#         "wise",
#         "wish",
#         "wit",
#         "with",
#         "withdraw",
#         "within"
#     ]

#     cards.append({
#         "url": f'https://mira-1255830993.cos.ap-shanghai.myqcloud.com/m3u8s/{title}.json',
#         "name": title,
#         "image": f"https://video.chato.cn/m3u8/{random.choice(terms)}.jpg"
#         })

# st.code(json.dumps(cards, indent=4))

# cards = []
# terms = list(get_terms(open("dicts/" + file).read()).keys())
# size = 12
# chunks = [terms[i:i+size] for i in range(0, len(terms), size)]
# for chunk in chunks:
#     cards.append(
#         {
#         "url": f"https://video.chato.cn/m3u8/{chunk[0]}.m3u8",
#         "terms": chunk
#     })
# result = {
#     "cards": cards
# }

# json.dump(result, open(file.replace(".txt", ".json"), "w"), indent=4)

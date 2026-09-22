import streamlit as st


week1_page = st.Page(
    ".pages/week1.py",
    title="Week 1"
)

week2_page = st.Page(
    ".pages/week2.py",
    title="Week 2"
)

week3_page = st.Page(
    ".pages/week3.py",
    title="Week 3"
)

week4_page = st.Page(
    ".pages/week4.py",
    title="Week 4"
)

week5_page = st.Page(
    ".pages/week5.py",
    title="Week 5",
    default=True
)

pg = st.navigation([
    week1_page,
    week2_page,
    week3_page,
    week4_page,
    week5_page
])


st.set_page_config(
    page_title="IST 688",
    page_icon=":material/code:"
)


pg.run()
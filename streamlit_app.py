import streamlit as st


week1_page = st.Page(
    ".pages/week1.py",
    title="Week 1",
    icon=":material/description:"
)

week2_page = st.Page(
    ".pages/week2.py",
    title="Week 2",
    icon=":material/description:",
    default= True
)


pg = st.navigation([
    week1_page,
    week2_page
])


st.set_page_config(
    page_title="IST 688",
    page_icon=":material/code:"
)


pg.run()
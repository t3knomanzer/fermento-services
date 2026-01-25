#!/usr/bin/env python
""" """

__author__ = "Ruben Henares "
__email__ = "rhenares0@gmail.com"
__maintainers__ = ["Ruben Henares <rhenares0@gmail.com>"]

import dotenv
import streamlit as st

dotenv.load_dotenv()

# Set root page options
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "mailto:rhenares0@gmail.com",
        "About": """
        """,
    },
)


# Sidebar tools
clear_cache = st.sidebar.button("Clear cache")
if clear_cache:
    st.cache_data.clear()

# Navigation
navigation = st.navigation(
    [
        st.Page("lib/pages/hello_world.py", title="Hello-World", default=True),
    ]
)
navigation.run()

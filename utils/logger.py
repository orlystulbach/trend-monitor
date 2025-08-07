# import streamlit.components.v1 as components

# def log_to_browser(message):
#     components.html(f"""
#         <script style="display: none;">
#             console.log({repr(message)});
#         </script>
#     """, height=0)


import streamlit as st

# def log_to_browser(message):
#     st.markdown(f"""
#         <script>
#             console.log({repr(message)});
#         </script>
#     """, unsafe_allow_html=True)

def log_to_browser(message):
    # Create an empty container that won't take up space
    log_container = st.empty()
    log_container.markdown(f"""
    <script>
    console.log('{message}');
    </script>
    """, unsafe_allow_html=True)
    # Immediately clear it
    log_container.empty()
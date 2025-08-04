import streamlit as st

# Initialize session state
if 'show_download' not in st.session_state:
    st.session_state.show_download = False

st.title("trying")

st.markdown("Trying to download without reload")
user_input = st.text_area("Put in keywords you want to save")

if st.button("Try Now"):
    # Set flag to show download button
    st.session_state.show_download = True
    st.session_state.user_data = user_input  # Store the data

# Show download button and success message if flag is set
if st.session_state.show_download:
    st.download_button(
        label="📥 Download Data (CSV)",
        data=st.session_state.user_data,
        file_name="trying.csv",
        mime="text/csv",
        key="download_csv"
    )
    
    st.success("Download ready!")
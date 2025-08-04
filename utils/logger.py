import streamlit.components.v1 as components

def log_to_browser(message):
    components.html(f"""
        <script>
            console.log('[From Python] {message}');
        </script>
    """, height=0)
import streamlit as st
import pyperclip
from summarizer import ArticleSummarizer
import os

def copy_to_clipboard(text: str):
    """Helper function to copy text to clipboard"""
    pyperclip.copy(text)
    st.success("Copied to clipboard!")

def get_unique_key():
    """Generate a unique key based on the form reset counter"""
    return f"{st.session_state.get('form_reset_counter', 0)}"

def reset_form():
    """Helper function to trigger form reset"""
    st.session_state['form_reset_counter'] = st.session_state.get('form_reset_counter', 0) + 1
    st.session_state['summary'] = None
    st.session_state['error_message'] = None

def handle_submit():
    """Handle form submission logic"""
    if 'summarizer' not in st.session_state:
        st.session_state['error_message'] = "Please enter your API key first"
        return

    unique_key = get_unique_key()
    publication = st.session_state[f'publication_{unique_key}']
    article_type = st.session_state[f'article_type_{unique_key}']
    article_text = st.session_state[f'article_text_{unique_key}']
    author = st.session_state.get(f'author_{unique_key}', None)
    specific_instructions = st.session_state.get(f'specific_instructions_{unique_key}', None)

    # Validate inputs
    if not publication or not article_text:
        st.session_state['error_message'] = "Please provide both publication name and article text"
        return

    if article_type in ["op-ed", "interview"] and not author:
        st.session_state['error_message'] = f"Please provide the {'author' if article_type == 'op-ed' else 'interviewee'} name"
        return

    # Clear any previous error message
    st.session_state['error_message'] = None
    st.session_state['is_summarizing'] = True

    try:
        # Get summary
        summary = st.session_state.summarizer.get_summary(
            article_text=article_text,
            publication=publication,
            article_type=article_type,
            author=author,
            specific_instructions=specific_instructions,
            sentence_count=st.session_state[f'sentence_count_{unique_key}']
        )

        # Store summary in session state
        st.session_state['summary'] = summary

    except Exception as e:
        st.session_state['error_message'] = f"An error occurred: {str(e)}"

    finally:
        st.session_state['is_summarizing'] = False

def initialize_summarizer(api_key: str):
    """Initialize the summarizer with the provided API key"""
    try:
        summarizer = ArticleSummarizer(api_key)
        st.session_state['summarizer'] = summarizer
        st.session_state['api_key_valid'] = True
        st.success("API key validated successfully!")
    except Exception as e:
        st.error(f"Invalid API key: {str(e)}")
        st.session_state['api_key_valid'] = False

def main():
    # Page configuration
    st.set_page_config(
        page_title="Article Summariser",
        page_icon="📰",
        layout="wide"
    )

    # Initialize session state variables
    if 'form_reset_counter' not in st.session_state:
        st.session_state['form_reset_counter'] = 0
    if 'summary' not in st.session_state:
        st.session_state['summary'] = None
    if 'error_message' not in st.session_state:
        st.session_state['error_message'] = None
    if 'is_summarizing' not in st.session_state:
        st.session_state['is_summarizing'] = False
    if 'api_key_valid' not in st.session_state:
        st.session_state['api_key_valid'] = False

    # Title and description
    st.title("📰 Article Summariser")
    st.markdown("""
        This app summarises articles using Claude AI. Simply input your API key and the article details below.
        The summary will maintain British English spelling.
    """)

    # API Key input section
    if not st.session_state.get('api_key_valid', False):
        st.write("### First, enter your Anthropic API key")
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter your Anthropic API key. Get one at https://console.anthropic.com/",
            placeholder="sk-ant-xxxx..."
        )
        if st.button("Submit API Key"):
            initialize_summarizer(api_key)
        st.divider()

    # Only show the main interface if API key is valid
    if st.session_state.get('api_key_valid', False):
        # Create two columns
        col1, col2 = st.columns([1, 1])

        with col1:
            # Input fields with dynamic keys
            unique_key = get_unique_key()

            st.text_input(
                "Publication Name",
                placeholder="e.g., The Guardian",
                key=f'publication_{unique_key}'
            )

            article_type = st.selectbox(
                "Article Type",
                ["news", "op-ed", "feature", "interview"],
                help="Select the type of article you're summarizing",
                key=f'article_type_{unique_key}'
            )

            st.number_input(
                "Number of sentences in summary",
                min_value=2,
                max_value=6,
                value=3,
                help="Choose how many sentences you want in your summary (2-6)",
                key=f'sentence_count_{unique_key}'
            )

            # Show author field for op-eds and interviews
            if article_type in ["op-ed", "interview"]:
                author_label = "Author Name" if article_type == "op-ed" else "Interviewee Name"
                st.text_input(
                    author_label,
                    placeholder="e.g., John Smith",
                    key=f'author_{unique_key}'
                )

            # Add checkbox and text input for specific instructions
            use_specific_instructions = st.checkbox(
                "Give specific instructions?",
                key=f'use_instructions_{unique_key}'
            )
            if use_specific_instructions:
                st.text_area(
                    "Specific Instructions",
                    placeholder="Enter specific aspects you want the summary to focus on...",
                    max_chars=500,
                    help="Maximum 500 characters",
                    key=f'specific_instructions_{unique_key}'
                )

            # Article text area
            st.text_area(
                "Article Text",
                height=190,
                placeholder="Paste your article text here...",
                key=f'article_text_{unique_key}'
            )

            # Summarize button
            st.button("Summarise", type="primary", on_click=handle_submit)

        with col2:
            # Display any error messages at the top of the right column
            if st.session_state.get('error_message'):
                st.error(st.session_state['error_message'])

            # Show loading spinner when processing
            if st.session_state.get('is_summarizing', False):
                with st.spinner("Generating summary..."):
                    st.empty()

            # Display summary
            if st.session_state['summary']:
                st.subheader("Summary")
                st.write(st.session_state['summary'])

                # Copy to clipboard button
                if st.button("Copy to Clipboard", type="primary"):
                    copy_to_clipboard(st.session_state['summary'])

                # New Article button with different color
                st.button("New Article",
                         type="secondary",
                         on_click=reset_form,
                         help="Start a new article summary")

if __name__ == "__main__":
    main()

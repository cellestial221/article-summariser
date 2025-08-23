import streamlit as st
import pyperclip
from summarizer import ArticleSummarizer
import os
import re

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
    st.session_state['detected_type'] = None
    st.session_state['detection_explanation'] = None
    st.session_state['client_mention_count'] = None
    st.session_state['client_validation_done'] = False

def safe_display_text(text):
    """Safely display text content, handling potential encoding or formatting issues"""
    if text is None:
        return ""

    # Ensure it's a string
    text_str = str(text)

    # Use st.text() instead of st.write() for safer display of API responses
    return text_str

def count_client_mentions(article_text: str, client_name: str) -> int:
    """Count how many times a client is mentioned in the article text"""
    if not article_text or not client_name:
        return 0

    # Clean the client name and article text
    client_name = client_name.strip()

    # Create various patterns to match (case-insensitive)
    # This handles variations like "Company", "Company's", "Company Inc.", etc.
    patterns = [
        r'\b' + re.escape(client_name) + r'\b',  # Exact word match
        r'\b' + re.escape(client_name) + r'\'s\b',  # Possessive form
        r'\b' + re.escape(client_name) + r's\b',  # Alternative possessive
    ]

    total_count = 0
    for pattern in patterns:
        matches = re.findall(pattern, article_text, re.IGNORECASE)
        total_count += len(matches)

    # Remove duplicate counts (e.g., if "Company's" was counted both as "Company" and "Company's")
    # by doing a more sophisticated count
    all_matches = re.findall(r'\b' + re.escape(client_name) + r'(?:\'?s)?\b', article_text, re.IGNORECASE)

    return len(all_matches)

def validate_client_mention(article_text: str, client_name: str):
    """Validate if client is mentioned and return count"""
    count = count_client_mentions(article_text, client_name)
    return count

def handle_type_detection():
    """Handle article type detection"""
    if 'summarizer' not in st.session_state:
        st.session_state['error_message'] = "Please enter your API key first"
        return

    unique_key = get_unique_key()
    article_text = st.session_state.get(f'article_text_{unique_key}', '')

    if not article_text.strip():
        st.session_state['error_message'] = "Please paste your article text before analyzing"
        return

    st.session_state['is_analyzing'] = True
    st.session_state['error_message'] = None

    try:
        result = st.session_state.summarizer.detect_article_type(article_text)
        st.session_state['detected_type'] = result['type']
        st.session_state['detection_explanation'] = result['explanation']
        st.success(f"Article type detected: **{result['type'].title()}** - {result['explanation']}")
    except Exception as e:
        st.session_state['error_message'] = f"Error detecting article type: {str(e)}"
    finally:
        st.session_state['is_analyzing'] = False

def handle_submit():
    """Handle form submission logic"""
    if 'summarizer' not in st.session_state:
        st.session_state['error_message'] = "Please enter your API key first"
        return

    unique_key = get_unique_key()
    publication = st.session_state[f'publication_{unique_key}']
    article_text = st.session_state[f'article_text_{unique_key}']

    # Determine article type - either from detection or manual selection
    use_ai_analysis = st.session_state.get(f'use_ai_analysis_{unique_key}', False)
    if use_ai_analysis:
        article_type = st.session_state.get('detected_type')
        if not article_type:
            st.session_state['error_message'] = "Please analyze the article type first using the 'Analyze Article Type' button"
            return
    else:
        article_type = st.session_state[f'article_type_{unique_key}']

    author = st.session_state.get(f'author_{unique_key}', None)
    specific_instructions = st.session_state.get(f'specific_instructions_{unique_key}', None)

    # Handle client mention feature
    client_name = None
    client_mention_count = None
    use_client_tracking = st.session_state.get(f'use_client_tracking_{unique_key}', False)

    if use_client_tracking:
        client_name = st.session_state.get(f'client_name_{unique_key}', '').strip()
        if client_name:
            # Validate client mentions
            client_mention_count = validate_client_mention(article_text, client_name)
            if client_mention_count == 0:
                st.session_state['error_message'] = f"'{client_name}' was not found in the article text. Please check the client name and try again."
                return
            # Store for display
            st.session_state['client_mention_count'] = client_mention_count
            st.session_state['client_validation_done'] = True

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
        # Get summary with client mention info if applicable
        summary = st.session_state.summarizer.get_summary(
            article_text=article_text,
            publication=publication,
            article_type=article_type,
            author=author,
            specific_instructions=specific_instructions,
            sentence_count=st.session_state[f'sentence_count_{unique_key}'],
            client_name=client_name,
            client_mention_count=client_mention_count
        )

        # Store summary in session state, ensuring it's properly cleaned
        st.session_state['summary'] = safe_display_text(summary)

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
    if 'is_analyzing' not in st.session_state:
        st.session_state['is_analyzing'] = False
    if 'api_key_valid' not in st.session_state:
        st.session_state['api_key_valid'] = False
    if 'detected_type' not in st.session_state:
        st.session_state['detected_type'] = None
    if 'detection_explanation' not in st.session_state:
        st.session_state['detection_explanation'] = None
    if 'client_mention_count' not in st.session_state:
        st.session_state['client_mention_count'] = None
    if 'client_validation_done' not in st.session_state:
        st.session_state['client_validation_done'] = False

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

            # Step 1: Publication Name
            st.text_input(
                "Publication Name",
                placeholder="e.g., The Guardian",
                key=f'publication_{unique_key}'
            )

            # Step 2: Article Text (always in the same place)
            st.text_area(
                "Article Text",
                height=180,
                placeholder="Paste your article text here...",
                key=f'article_text_{unique_key}'
            )

            # Step 3: Article Type Determination
            st.subheader("Article Type")

            # Option to use AI analysis
            use_ai_analysis = st.checkbox(
                "🤖 Let AI analyze and determine the article type",
                help="Use Claude AI to automatically detect whether this is news, op-ed, feature, or interview",
                key=f'use_ai_analysis_{unique_key}'
            )

            if use_ai_analysis:
                # AI Detection Path
                if st.button("🔍 Analyze Article Type", type="secondary"):
                    handle_type_detection()

                # Show loading spinner when analyzing
                if st.session_state.get('is_analyzing', False):
                    with st.spinner("Analyzing article type..."):
                        st.empty()

                # Show detected type
                if st.session_state.get('detected_type'):
                    detected_type = st.session_state['detected_type']
                    explanation = st.session_state.get('detection_explanation', '')

                    st.success(f"**Detected Type: {detected_type.title()}**  \n{explanation}")

                    # Show author field if needed for detected type
                    if detected_type in ["op-ed", "interview"]:
                        author_label = "Author Name" if detected_type == "op-ed" else "Interviewee Name"
                        st.text_input(
                            author_label,
                            placeholder="e.g., John Smith",
                            key=f'author_{unique_key}',
                            help=f"Required for {detected_type} articles"
                        )
            else:
                # Manual Selection Path (Default)
                article_type = st.selectbox(
                    "Select Article Type",
                    ["news", "op-ed", "feature", "interview"],
                    help="Choose the type that best describes your article",
                    key=f'article_type_{unique_key}'
                )

                # Show author field for op-eds and interviews
                if article_type in ["op-ed", "interview"]:
                    author_label = "Author Name" if article_type == "op-ed" else "Interviewee Name"
                    st.text_input(
                        author_label,
                        placeholder="e.g., John Smith",
                        key=f'author_{unique_key}',
                        help=f"Required for {article_type} articles"
                    )

            # Step 4: Summary preferences (integrated into main flow)
            st.number_input(
                "Number of sentences in summary",
                min_value=2,
                max_value=6,
                value=3,
                help="Choose how many sentences you want in your summary (2-6)",
                key=f'sentence_count_{unique_key}'
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
                    height=80,
                    key=f'specific_instructions_{unique_key}'
                )

            # Add client mention tracking feature
            use_client_tracking = st.checkbox(
                "Client mention?",
                help="Ensure accurate representation of client mentions in the summary",
                key=f'use_client_tracking_{unique_key}'
            )
            if use_client_tracking:
                client_name = st.text_input(
                    "Client Name",
                    placeholder="Enter the client name to track...",
                    help="The summary will accurately reflect how this client is mentioned in context",
                    key=f'client_name_{unique_key}'
                )

                # Show validation result if available
                if st.session_state.get('client_validation_done') and st.session_state.get('client_mention_count'):
                    count = st.session_state['client_mention_count']
                    if count == 1:
                        st.info(f"✓ '{client_name}' is mentioned once in the article")
                    else:
                        st.info(f"✓ '{client_name}' is mentioned {count} times in the article")

            st.divider()

            # Summarize button
            st.button("Summarise", type="primary", on_click=handle_submit, use_container_width=True)

        with col2:
            # Display any error messages at the top of the right column
            if st.session_state.get('error_message'):
                st.error(st.session_state['error_message'])

            # Show loading spinner when processing
            if st.session_state.get('is_summarizing', False):
                with st.spinner("Generating summary..."):
                    st.empty()

            # Display summary using safe text display
            if st.session_state['summary']:
                st.subheader("Summary")

                # Use st.text() for safer display of API responses
                # This prevents formatting issues with special characters
                st.text(st.session_state['summary'])

                # Copy to clipboard button
                if st.button("Copy to Clipboard", type="primary"):
                    copy_to_clipboard(st.session_state['summary'])

                # New Article button with different color
                st.button("New Article",
                         type="secondary",
                         on_click=reset_form,
                         help="Start a new article summary")

            # Show helpful information when no summary is present
            elif not st.session_state.get('is_summarizing', False):
                st.markdown("""
                ### How to use:

                **Step 1:** Enter publication name
                **Step 2:** Paste your article text
                **Step 3:** Select article type manually **OR** check the AI analysis option
                **Step 4:** Set summary length and generate

                ---

                **🤖 AI Analysis**: Let Claude Haiku automatically detect whether your article is news, an op-ed, feature, or interview

                **📋 Manual Selection**: Choose the type yourself from the dropdown (default)

                **🏢 Client Tracking**: Track how a specific client is mentioned to ensure accurate representation in the summary
                """)

if __name__ == "__main__":
    main()

import os
import re

import bcrypt
import pyperclip
import streamlit as st

from article_scraper import ArticleScraper
from summarizer import ArticleSummarizer


def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;600;700&display=swap');
    h1, h2, h3, h4, h5, h6,
    [data-testid="stHeading"] {
        font-family: 'Hanken Grotesk', sans-serif !important;
    }
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background-color: #224347 !important;
        border-color: #224347 !important;
        color: white !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background-color: #1a3437 !important;
        border-color: #1a3437 !important;
        color: white !important;
    }
    button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        border: 1px solid #224347 !important;
        color: #224347 !important;
        background-color: transparent !important;
    }
    button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #eef4f4 !important;
        border-color: #224347 !important;
        color: #224347 !important;
    }
    [data-testid="stFormSubmitButton"] > button {
        background-color: #224347 !important;
        border-color: #224347 !important;
        color: white !important;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1a3437 !important;
        border-color: #1a3437 !important;
    }
    input[type="radio"],
    [data-testid="stRadio"] input[type="radio"] {
        accent-color: #224347 !important;
    }
    [data-testid="stRadio"] label {
        border-color: #224347 !important;
    }
    [data-testid="stRadio"] label[data-selected="true"] {
        background-color: #224347 !important;
        color: white !important;
    }
    input[type="checkbox"] {
        accent-color: #224347 !important;
    }
    [data-testid="stTextInput"] > div:focus-within,
    [data-testid="stTextArea"] > div:focus-within,
    [data-testid="stNumberInput"] > div:focus-within,
    [data-testid="stSelectbox"] > div:focus-within {
        border-color: #224347 !important;
        box-shadow: 0 0 0 1px #224347 !important;
    }
    [data-testid="stText"] {
        border-left: 3px solid #00A19B !important;
        padding: 10px 16px !important;
        background-color: #F6FAFA !important;
        border-radius: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def get_unique_key():
    """Generate a unique key based on the form reset counter"""
    return f"{st.session_state.get('form_reset_counter', 0)}"


def reset_form():
    """Helper function to trigger form reset"""
    st.session_state["form_reset_counter"] = (
        st.session_state.get("form_reset_counter", 0) + 1
    )
    st.session_state["summary"] = None
    st.session_state["error_message"] = None
    st.session_state["detected_type"] = None
    st.session_state["detection_explanation"] = None
    st.session_state["client_mention_count"] = None
    st.session_state["client_validation_done"] = False
    st.session_state["scraped_content"] = None
    st.session_state["detected_language"] = None
    st.session_state["clipboard_feedback"] = None
    st.session_state["pending_article_type"] = None


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
        r"\b" + re.escape(client_name) + r"\b",  # Exact word match
        r"\b" + re.escape(client_name) + r"\'s\b",  # Possessive form
        r"\b" + re.escape(client_name) + r"s\b",  # Alternative possessive
    ]

    total_count = 0
    for pattern in patterns:
        matches = re.findall(pattern, article_text, re.IGNORECASE)
        total_count += len(matches)

    # Remove duplicate counts (e.g., if "Company's" was counted both as "Company" and "Company's")
    # by doing a more sophisticated count
    all_matches = re.findall(
        r"\b" + re.escape(client_name) + r"(?:\'?s)?\b", article_text, re.IGNORECASE
    )

    return len(all_matches)


def validate_client_mention(article_text: str, client_name: str):
    """Validate if client is mentioned and return count"""
    count = count_client_mentions(article_text, client_name)
    return count


def detect_article_language(article_text: str):
    """Detect the language of the article and store in session state"""
    if "summarizer" not in st.session_state or not article_text:
        return

    try:
        language_info = st.session_state.summarizer.detect_language(article_text)
        st.session_state["detected_language"] = language_info
    except Exception as e:
        st.session_state["detected_language"] = {
            "language": "Unknown",
            "is_english": True,
            "error": str(e),
        }


def handle_url_scraping():
    """Handle URL scraping"""
    unique_key = get_unique_key()
    url = st.session_state.get(f"article_url_{unique_key}", "").strip()

    if not url:
        st.session_state["error_message"] = "Please enter a URL"
        return

    # Initialize scraper
    scraper = ArticleScraper()

    # Create a placeholder for the progress indicator
    progress_placeholder = st.empty()

    try:
        with progress_placeholder.container():
            with st.spinner(
                "🌐 Fetching article content... This may take a few seconds"
            ):
                result = scraper.scrape_article(url)

        if result["success"]:
            # Store the scraped content
            st.session_state["scraped_content"] = {
                "text": result["text"],
                "publication": result.get("publication", ""),
                "author": result.get("author", ""),
                "title": result.get("title", ""),
            }

            # Pre-fill the form fields
            if result.get("publication"):
                st.session_state[f"publication_{unique_key}"] = result["publication"]

            st.session_state[f"article_text_{unique_key}"] = result["text"]

            if result.get("author"):
                st.session_state[f"author_{unique_key}"] = result["author"]

            # Detect language of scraped content
            detect_article_language(result["text"])

            st.success("✅ Article successfully extracted.")
            if result.get("paywall_warning"):
                st.caption("⚠️ This site often has paywalled content — if the text looks incomplete, paste it manually.")

        else:
            st.session_state["error_message"] = result.get(
                "error", "Failed to extract article"
            )
            # Still try to fill publication name if we got it
            if result.get("publication"):
                st.session_state[f"publication_{unique_key}"] = result["publication"]

    except Exception as e:
        st.session_state["error_message"] = f"Error scraping URL: {str(e)}"
    finally:
        progress_placeholder.empty()


def handle_type_detection():
    """Handle article type detection"""
    if "summarizer" not in st.session_state:
        st.session_state["error_message"] = "Please enter your API key first"
        return

    unique_key = get_unique_key()
    article_text = st.session_state.get(f"article_text_{unique_key}", "")

    if not article_text.strip():
        st.session_state["error_message"] = (
            "Please paste your article text before analyzing"
        )
        return

    st.session_state["error_message"] = None

    # Create a placeholder for the progress indicator
    progress_placeholder = st.empty()

    try:
        with progress_placeholder.container():
            with st.spinner("🔍 Analyzing article type with Claude Haiku..."):
                result = st.session_state.summarizer.detect_article_type(article_text)

        st.session_state["detected_type"] = result["type"]
        st.session_state["detection_explanation"] = result["explanation"]
        st.session_state["pending_article_type"] = result["type"]
        st.rerun()  # rerun so pending is applied before the selectbox renders
    except Exception as e:
        error_message = str(e)

        # Provide specific error messages based on the error type
        if "529" in error_message or "overloaded" in error_message.lower():
            st.session_state["error_message"] = (
                "⚠️ Anthropic's servers are currently overloaded. Please wait a moment and try again."
            )
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            st.session_state["error_message"] = (
                "⏱️ Rate limit exceeded. Please wait a minute before trying again."
            )
        elif "500" in error_message or "502" in error_message or "503" in error_message:
            st.session_state["error_message"] = (
                "🔧 Anthropic is experiencing server issues. Please try again in a few moments."
            )
        else:
            st.session_state["error_message"] = (
                f"Error detecting article type: {error_message}"
            )
    finally:
        progress_placeholder.empty()


def handle_submit():
    """Handle form submission logic"""
    if "summarizer" not in st.session_state:
        st.session_state["error_message"] = "Please enter your API key first"
        return

    unique_key = get_unique_key()
    publication = st.session_state[f"publication_{unique_key}"]
    article_text = st.session_state[f"article_text_{unique_key}"]

    article_type = st.session_state[f"article_type_{unique_key}"]

    author = st.session_state.get(f"author_{unique_key}", None)
    specific_instructions = st.session_state.get(
        f"specific_instructions_{unique_key}", None
    )
    use_article_pointers = (
        article_type == "news"
        and st.session_state.get(f"use_article_pointers_{unique_key}", False)
    )

    # Handle client mention feature
    client_name = None
    client_mention_count = None
    use_client_tracking = st.session_state.get(
        f"use_client_tracking_{unique_key}", False
    )

    if use_client_tracking:
        client_name = st.session_state.get(f"client_name_{unique_key}", "").strip()
        if client_name:
            # Validate client mentions
            client_mention_count = validate_client_mention(article_text, client_name)
            if client_mention_count == 0:
                st.session_state["error_message"] = (
                    f"'{client_name}' was not found in the article text. Please check the client name and try again."
                )
                return
            # Store for display - FIX: Store with unique key to prevent loss
            st.session_state[f"client_mention_count_{unique_key}"] = (
                client_mention_count
            )
            st.session_state[f"client_validation_done_{unique_key}"] = True

    # Validate inputs
    if not publication or not article_text:
        st.session_state["error_message"] = (
            "Please provide both publication name and article text"
        )
        return

    if article_type in ["op-ed", "interview"] and not author:
        st.session_state["error_message"] = (
            f"Please provide the {'author' if article_type == 'op-ed' else 'interviewee'} name"
        )
        return

    # Clear any previous error message
    st.session_state["error_message"] = None

    try:
        # Get summary with client mention info if applicable
        summary = st.session_state.summarizer.get_summary(
            article_text=article_text,
            publication=publication,
            article_type=article_type,
            author=author,
            specific_instructions=specific_instructions,
            sentence_count=st.session_state[f"sentence_count_{unique_key}"],
            client_name=client_name,
            client_mention_count=client_mention_count,
            use_article_pointers=use_article_pointers,
        )

        # Store summary in session state, ensuring it's properly cleaned
        st.session_state["summary"] = safe_display_text(summary)

    except Exception as e:
        error_message = str(e)

        # Provide specific error messages based on the error type
        if "529" in error_message or "overloaded" in error_message.lower():
            st.session_state["error_message"] = (
                "⚠️ Anthropic's servers are currently overloaded. Please wait a moment and try again."
            )
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            st.session_state["error_message"] = (
                "⏱️ Rate limit exceeded. Please wait a minute before trying again."
            )
        elif "500" in error_message or "502" in error_message or "503" in error_message:
            st.session_state["error_message"] = (
                "🔧 Anthropic is experiencing server issues. Please try again in a few moments."
            )
        elif (
            "network" in error_message.lower() or "connection" in error_message.lower()
        ):
            st.session_state["error_message"] = (
                "🌐 Network connection error. Please check your connection and try again."
            )
        else:
            st.session_state["error_message"] = f"An error occurred: {error_message}"


def copy_to_clipboard(text):
    """Copy text to clipboard using pyperclip"""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        st.warning(f"Could not copy to clipboard: {str(e)}")
        return False


def remove_publication_from_summary(text):
    """Strip leading publication name, keeping the connecting phrase intact."""
    if not text:
        return ""
    for phrase in [" reports that ", " carries a ", " carries an "]:
        if phrase in text:
            idx = text.index(phrase)
            return text[idx + 1:]  # skip leading space, keep phrase as-is
    return text


def handle_copy_full():
    """Handle copying full summary"""
    if st.session_state.get("summary"):
        if copy_to_clipboard(st.session_state["summary"]):
            st.session_state["clipboard_feedback"] = "full"


def handle_copy_clean():
    """Handle copying clean summary"""
    if st.session_state.get("summary"):
        clean_summary = remove_publication_from_summary(st.session_state["summary"])
        if copy_to_clipboard(clean_summary):
            st.session_state["clipboard_feedback"] = "clean"


def check_password() -> bool:
    """Show login form and return True if the user is authenticated."""
    if st.session_state.get("authenticated", False):
        return True

    def _verify():
        username = st.session_state.get("login_username", "").lower().strip()
        password = st.session_state.get("login_password", "")
        stored = st.secrets.get("passwords", {}).get(username)
        if stored and bcrypt.checkpw(password.encode(), stored.encode()):
            st.session_state["authenticated"] = True
            st.session_state.pop("login_username", None)
            st.session_state.pop("login_password", None)
        else:
            st.session_state["authenticated"] = False
            st.session_state["login_failed"] = True

    st.markdown("<h1 style='text-align:center'>📰 Article Summariser</h1>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1, 1])
    with col:
        with st.form("login_form"):
            st.text_input("Username", key="login_username")
            st.text_input("Password", type="password", key="login_password")
            st.form_submit_button("Log in", use_container_width=True, on_click=_verify)
        if st.session_state.get("login_failed"):
            st.error("Invalid username or password.")

    return False


def setup_api_keys():
    """Load the Anthropic API key from secrets and initialise the summarizer."""
    api_key = st.secrets["anthropic"]["api_key"]
    os.environ["ANTHROPIC_API_KEY"] = api_key
    if "summarizer" not in st.session_state:
        initialize_summarizer(api_key)


def initialize_summarizer(api_key: str):
    """Initialize the summarizer with the provided API key"""
    st.session_state["summarizer"] = ArticleSummarizer(api_key)



def main():
    st.set_page_config(page_title="Article Summariser", page_icon="📰", layout="wide")
    inject_custom_css()

    # Initialize session state variables
    if "form_reset_counter" not in st.session_state:
        st.session_state["form_reset_counter"] = 0
    if "summary" not in st.session_state:
        st.session_state["summary"] = None
    if "error_message" not in st.session_state:
        st.session_state["error_message"] = None
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "login_failed" not in st.session_state:
        st.session_state["login_failed"] = False
    if "detected_type" not in st.session_state:
        st.session_state["detected_type"] = None
    if "detection_explanation" not in st.session_state:
        st.session_state["detection_explanation"] = None
    if "scraped_content" not in st.session_state:
        st.session_state["scraped_content"] = None
    if "detected_language" not in st.session_state:
        st.session_state["detected_language"] = None
    if "clipboard_feedback" not in st.session_state:
        st.session_state["clipboard_feedback"] = None
    if not check_password():
        st.stop()

    # Authenticated — load API keys and initialise summarizer
    setup_api_keys()

    st.title("📰 Article Summariser")

    # Only show the main interface if logged in
    if st.session_state.get("authenticated", False):
        # Create two columns
        col1, col2 = st.columns([1, 1])

        with col1:
            # Input fields with dynamic keys
            unique_key = get_unique_key()

            # Step 1: Choose input method
            input_method = st.radio(
                "How would you like to provide the article?",
                ["Enter URL", "Paste Text"],
                horizontal=True,
                key=f"input_method_{unique_key}",
            )

            if input_method == "Enter URL":
                # URL input and scraping
                article_url = st.text_input(
                    "Article URL",
                    placeholder="https://www.example.com/article",
                    key=f"article_url_{unique_key}",
                )

                col_scrape, col_clear = st.columns(2)
                with col_scrape:
                    if st.button(
                        "🔍 Fetch Article", type="primary", use_container_width=True
                    ):
                        handle_url_scraping()
                with col_clear:
                    st.button(
                        "🔄 Clear",
                        type="secondary",
                        use_container_width=True,
                        on_click=reset_form,
                    )

            # Step 2: Publication Name (always visible, may be pre-filled from scraping)
            st.text_input(
                "Publication Name",
                placeholder="e.g., The Guardian",
                key=f"publication_{unique_key}",
            )

            # Step 3: Article Text (always visible, may be pre-filled from scraping)
            article_text_value = st.text_area(
                "Article Text",
                height=180,
                placeholder="Paste your article text here...",
                key=f"article_text_{unique_key}",
                on_change=lambda: detect_article_language(
                    st.session_state.get(f"article_text_{unique_key}", "")
                ),
            )

            # Show language detection only for non-English articles
            if article_text_value:
                lang_info = st.session_state.get("detected_language")
                if lang_info and not lang_info.get("is_english", True) and lang_info.get("language") not in (None, "Unknown"):
                    st.caption(f"🌍 {lang_info['language']} detected — will translate")

            # Step 4: Article Type Determination
            st.markdown("#### Article Type")

            # Apply pending auto-detected type before the widget renders
            if st.session_state.get("pending_article_type"):
                st.session_state[f"article_type_{unique_key}"] = st.session_state.pop("pending_article_type")

            article_type = st.selectbox(
                "Select Article Type",
                ["news", "op-ed", "feature", "interview"],
                key=f"article_type_{unique_key}",
            )

            if st.button("🤖 Auto-detect type", type="secondary", use_container_width=True):
                handle_type_detection()

            if st.session_state.get("detected_type"):
                explanation = st.session_state.get("detection_explanation", "")
                label = st.session_state["detected_type"].title()
                st.caption(f"Auto-detected: {label}" + (f" — {explanation}" if explanation else ""))

            # Show author field for op-eds and interviews
            if article_type in ["op-ed", "interview"]:
                author_label = (
                    "Author Name" if article_type == "op-ed" else "Interviewee Name"
                )
                st.text_input(
                    author_label,
                    placeholder="e.g., John Smith",
                    key=f"author_{unique_key}",
                )

            if article_type == "news":
                st.checkbox(
                    "Use article pointers?",
                    value=True,
                    key=f"use_article_pointers_{unique_key}",
                    help="Sentences after the first will begin with 'The article highlights / notes / outlines / cites'",
                )

            # Step 5: Summary preferences (integrated into main flow)
            st.number_input(
                "Number of sentences in summary",
                min_value=2,
                max_value=6,
                value=3,
                help="Choose how many sentences you want in your summary (2-6)",
                key=f"sentence_count_{unique_key}",
            )

            # Add checkbox and text input for specific instructions
            use_specific_instructions = st.checkbox(
                "Give specific instructions?", key=f"use_instructions_{unique_key}"
            )
            if use_specific_instructions:
                st.text_area(
                    "Specific Instructions",
                    placeholder="Enter specific aspects you want the summary to focus on...",
                    max_chars=500,
                    help="Maximum 500 characters",
                    height=80,
                    key=f"specific_instructions_{unique_key}",
                )

            # Add client mention tracking feature
            use_client_tracking = st.checkbox(
                "Client mention?",
                help="Ensure accurate representation of client mentions in the summary",
                key=f"use_client_tracking_{unique_key}",
            )
            if use_client_tracking:
                client_name = st.text_input(
                    "Client Name",
                    placeholder="Enter the client name to track...",
                    help="The summary will accurately reflect how this client is mentioned in context",
                    key=f"client_name_{unique_key}",
                )

                # FIX: Show validation result with unique key
                if st.session_state.get(
                    f"client_validation_done_{unique_key}"
                ) and st.session_state.get(f"client_mention_count_{unique_key}"):
                    count = st.session_state[f"client_mention_count_{unique_key}"]
                    if count == 1:
                        st.info(f"✓ '{client_name}' is mentioned once in the article")
                    else:
                        st.info(
                            f"✓ '{client_name}' is mentioned {count} times in the article"
                        )

            summarise_clicked = st.button("Summarise", type="primary", use_container_width=True)

        with col2:
            if summarise_clicked:
                with st.spinner("Summarising..."):
                    handle_submit()

            # Display any error messages at the top of the right column
            if st.session_state.get("error_message"):
                st.error(st.session_state["error_message"])

            # Display summary using safe text display
            if st.session_state["summary"]:
                st.subheader("Summary")

                st.text(st.session_state["summary"])

                # Show clipboard feedback
                if st.session_state.get("clipboard_feedback"):
                    if st.session_state["clipboard_feedback"] == "full":
                        st.success("📋 Full summary copied to clipboard!")
                    elif st.session_state["clipboard_feedback"] == "clean":
                        st.success("📄 Clean summary copied to clipboard!")
                    # Clear feedback after showing
                    st.session_state["clipboard_feedback"] = None

                # FIX: Action buttons using callbacks to prevent disappearing
                col_copy, col_copy_no_pub, col_new = st.columns(3)

                with col_copy:
                    st.button(
                        "📋 Copy Full",
                        type="primary",
                        use_container_width=True,
                        help="Copy complete summary including publication name",
                        on_click=handle_copy_full,
                    )

                with col_copy_no_pub:
                    st.button(
                        "📄 Copy Clean",
                        type="secondary",
                        use_container_width=True,
                        help="Copy summary without publication name",
                        on_click=handle_copy_clean,
                    )

                with col_new:
                    st.button(
                        "🔄 New Article",
                        type="secondary",
                        on_click=reset_form,
                        help="Start a new article summary",
                        use_container_width=True,
                    )

            # Show placeholder when no summary is present
            else:
                st.caption("Enter article details on the left to generate a summary.")


if __name__ == "__main__":
    main()

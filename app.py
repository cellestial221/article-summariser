import os
import re

import pyperclip
import streamlit as st

from article_scraper import ArticleScraper
from summarizer import ArticleSummarizer


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
    # Clear clipboard feedback
    st.session_state["clipboard_feedback"] = None


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

            # Success message
            method = result.get("method", "unknown")
            success_msg = f"✅ Article successfully extracted using {method}!"

            if result.get("paywall_warning"):
                success_msg += "\n⚠️ Note: This site often has paywalled content. If the extracted text seems incomplete, you may need to paste it manually."

            st.success(success_msg)

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
        st.success(
            f"Article type detected: **{result['type'].title()}** - {result['explanation']}"
        )
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

    # Determine article type - either from detection or manual selection
    use_ai_analysis = st.session_state.get(f"use_ai_analysis_{unique_key}", False)
    if use_ai_analysis:
        article_type = st.session_state.get("detected_type")
        if not article_type:
            st.session_state["error_message"] = (
                "Please analyze the article type first using the 'Analyze Article Type' button"
            )
            return
    else:
        article_type = st.session_state[f"article_type_{unique_key}"]

    author = st.session_state.get(f"author_{unique_key}", None)
    specific_instructions = st.session_state.get(
        f"specific_instructions_{unique_key}", None
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


def initialize_summarizer(api_key: str):
    """Initialize the summarizer with the provided API key"""
    try:
        with st.spinner("Validating API key..."):
            summarizer = ArticleSummarizer(api_key)
            st.session_state["summarizer"] = summarizer
            st.session_state["api_key_valid"] = True
        st.success("API key validated successfully!")
    except Exception as e:
        error_message = str(e)

        # Parse different types of errors
        if "401" in error_message or "invalid_api_key" in error_message.lower():
            st.error("❌ Invalid API key. Please check your API key and try again.")
            st.info("💡 Get your API key from https://console.anthropic.com/")
        elif "529" in error_message or "overloaded" in error_message.lower():
            st.warning(
                "⚠️ Anthropic's servers are currently overloaded. Please try again in a few moments."
            )
            st.info(
                "💡 This is a temporary issue on Anthropic's end. Your API key may be valid - just wait a minute and try again."
            )
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            st.warning(
                "⏱️ Rate limit exceeded. Please wait a moment before trying again."
            )
        elif (
            "network" in error_message.lower() or "connection" in error_message.lower()
        ):
            st.error(
                "🌐 Network connection error. Please check your internet connection and try again."
            )
        else:
            st.error(f"Error validating API key: {error_message}")
            st.info(
                "💡 If this persists, try generating a new API key at https://console.anthropic.com/"
            )

        st.session_state["api_key_valid"] = False


def main():
    # Page configuration
    st.set_page_config(page_title="Article Summariser", page_icon="📰", layout="wide")

    # Initialize session state variables
    if "form_reset_counter" not in st.session_state:
        st.session_state["form_reset_counter"] = 0
    if "summary" not in st.session_state:
        st.session_state["summary"] = None
    if "error_message" not in st.session_state:
        st.session_state["error_message"] = None
    if "api_key_valid" not in st.session_state:
        st.session_state["api_key_valid"] = False
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

    # Title and description
    st.title("📰 Article Summariser")

    # Check if language detection is available and show info
    try:
        import fast_langdetect

        langdetect_status = "✅ Fast language detection enabled (fast-langdetect)"
    except ImportError:
        langdetect_status = "⚠️ Fast language detection not installed - install 'fast-langdetect' for automatic language detection"

    st.markdown(f"""
        This app summarises articles using Claude AI. Simply input your API key and provide the article either by URL or text.
        The summary will maintain British English spelling and automatically translate non-English articles.

        *{langdetect_status}*
    """)

    # API Key input section
    if not st.session_state.get("api_key_valid", False):
        st.write("### First, enter your Anthropic API key")
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter your Anthropic API key. Get one at https://console.anthropic.com/",
            placeholder="sk-ant-xxxx...",
        )
        if st.button("Submit API Key"):
            initialize_summarizer(api_key)
        st.divider()

    # Only show the main interface if API key is valid
    if st.session_state.get("api_key_valid", False):
        # Create two columns
        col1, col2 = st.columns([1, 1])

        with col1:
            # Input fields with dynamic keys
            unique_key = get_unique_key()

            # Step 1: Choose input method
            st.subheader("📝 Article Input")
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
                    help="Enter the full URL of the article you want to summarize",
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

                # Show info about scraping
                with st.expander("ℹ️ About URL scraping"):
                    st.markdown("""
                    - The scraper works with most news websites
                    - Sites with paywalls may not work - you'll need to paste the text manually
                    - The publication name is auto-detected from the URL
                    - If scraping fails, you can always switch to manual text input
                    """)

            # Step 2: Publication Name (always visible, may be pre-filled from scraping)
            st.text_input(
                "Publication Name",
                placeholder="e.g., The Guardian",
                key=f"publication_{unique_key}",
                help="This may be auto-filled if you used URL scraping",
            )

            # Step 3: Article Text (always visible, may be pre-filled from scraping)
            article_text_value = st.text_area(
                "Article Text",
                height=180,
                placeholder="Paste your article text here or use the URL scraper above...",
                key=f"article_text_{unique_key}",
                help="This will be auto-filled if you successfully scraped a URL",
                on_change=lambda: detect_article_language(
                    st.session_state.get(f"article_text_{unique_key}", "")
                ),
            )

            # Show character count and language detection for the article
            if article_text_value:
                char_count = len(article_text_value)
                word_count = len(article_text_value.split())

                # Display stats in columns
                stat_col1, stat_col2 = st.columns(2)
                with stat_col1:
                    st.caption(f"📊 {char_count:,} characters, ~{word_count:,} words")

                with stat_col2:
                    if st.session_state.get("detected_language"):
                        lang_info = st.session_state["detected_language"]
                        language = lang_info.get("language", "Unknown")
                        confidence = lang_info.get("confidence")
                        method = lang_info.get("method", "unknown")
                        error = lang_info.get("error")

                        # Build detection method tooltip
                        if method == "fast-langdetect":
                            method_text = "⚡"  # Lightning emoji for fast detection
                            tooltip = "Detected using fast-langdetect (offline)"
                        elif method == "none":
                            method_text = "❌"
                            tooltip = "fast-langdetect not available"
                        else:
                            method_text = ""
                            tooltip = ""

                        # Show error if present (for debugging)
                        if error and language == "Unknown":
                            st.caption(
                                f"🌍 Language detection unavailable {method_text}",
                                help=f"{tooltip}. Error: {error}",
                            )
                        elif confidence and confidence > 0:
                            confidence_pct = int(confidence * 100)
                            if not lang_info.get("is_english", True):
                                st.caption(
                                    f"🌍 Language: **{language}** ({confidence_pct}% conf.) {method_text} - will translate",
                                    help=tooltip,
                                )
                            else:
                                st.caption(
                                    f"🌍 Language: **{language}** ({confidence_pct}% conf.) {method_text}",
                                    help=tooltip,
                                )
                        else:
                            if not lang_info.get("is_english", True):
                                st.caption(
                                    f"🌍 Language: **{language}** {method_text} (will translate)",
                                    help=tooltip,
                                )
                            else:
                                if language == "Unknown":
                                    st.caption(
                                        f"🌍 Language: **{language}** {method_text}",
                                        help=f"{tooltip}. {'Error: ' + error if error else 'Language could not be detected'}",
                                    )
                                else:
                                    st.caption(
                                        f"🌍 Language: **{language}** {method_text}",
                                        help=tooltip,
                                    )

            # Step 4: Article Type Determination
            st.subheader("Article Type")

            # Option to use AI analysis
            use_ai_analysis = st.checkbox(
                "🤖 Let AI analyze and determine the article type",
                help="Use Claude AI to automatically detect whether this is news, op-ed, feature, or interview. Note: AI analysis may occasionally misclassify articles.",
                key=f"use_ai_analysis_{unique_key}",
            )

            if use_ai_analysis:
                # AI Detection Path
                if st.button("🔍 Analyze Article Type", type="secondary"):
                    handle_type_detection()

                # Add small disclaimer
                st.caption(
                    "💡 AI detection is generally accurate but may occasionally misclassify. You can always double-check the result."
                )

                # Show detected type
                if st.session_state.get("detected_type"):
                    detected_type = st.session_state["detected_type"]
                    explanation = st.session_state.get("detection_explanation", "")

                    st.success(
                        f"**Detected Type: {detected_type.title()}**  \n{explanation}"
                    )

                    # Show author field if needed for detected type
                    if detected_type in ["op-ed", "interview"]:
                        author_label = (
                            "Author Name"
                            if detected_type == "op-ed"
                            else "Interviewee Name"
                        )
                        st.text_input(
                            author_label,
                            placeholder="e.g., John Smith",
                            key=f"author_{unique_key}",
                            help=f"Required for {detected_type} articles",
                        )
            else:
                # Manual Selection Path (Default)
                article_type = st.selectbox(
                    "Select Article Type",
                    ["news", "op-ed", "feature", "interview"],
                    help="Choose the type that best describes your article",
                    key=f"article_type_{unique_key}",
                )

                # Show author field for op-eds and interviews
                if article_type in ["op-ed", "interview"]:
                    author_label = (
                        "Author Name" if article_type == "op-ed" else "Interviewee Name"
                    )
                    st.text_input(
                        author_label,
                        placeholder="e.g., John Smith",
                        key=f"author_{unique_key}",
                        help=f"Required for {article_type} articles",
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

            st.divider()

            # Summarize button with spinner
            if st.button("Summarise", type="primary", use_container_width=True):
                with st.spinner("🤖 Generating summary with Claude Sonnet..."):
                    handle_submit()

        with col2:
            # Display any error messages at the top of the right column
            if st.session_state.get("error_message"):
                st.error(st.session_state["error_message"])

            # Display summary using safe text display
            if st.session_state["summary"]:
                st.subheader("Summary")

                # Create a nice container for the summary
                with st.container():
                    # Add a subtle background color to the summary box
                    st.markdown(
                        """
                        <style>
                        .summary-box {
                            background-color: #f0f2f6;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 10px 0;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Display the summary text
                    st.text(st.session_state["summary"])

                # FIX: Show clipboard feedback
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

            # Show helpful information when no summary is present
            else:
                # Create an info box with better styling
                with st.container():
                    st.markdown("""
                    ### 📖 How to use:

                    **Option A: URL Scraping (New!)**
                    1. Select "Enter URL" and paste the article URL
                    2. Click "Fetch Article" to automatically extract the text
                    3. The publication name and article text will be auto-filled
                    4. Continue with type selection and generate summary

                    **Option B: Manual Input**
                    1. Select "Paste Text" and enter publication name
                    2. Paste your article text in the text box
                    3. Select article type (manually or with AI)
                    4. Set summary length and generate

                    ---

                    **✨ Features:**

                    **🌐 URL Scraping**: Automatically extract articles from most news websites

                    **⚡ Fast Language Detection**: Ultra-fast offline detection with 95% accuracy (when fast-langdetect installed)

                    **🌍 Multilingual Support**: Automatically detects article language and translates to British English

                    **🤖 AI Analysis**: Let Claude Haiku automatically detect the article type

                    **📋 Manual Selection**: Choose the type yourself from the dropdown

                    **🏢 Client Tracking**: Track how a specific client is mentioned

                    **🇬🇧 UK Context**: Summaries are optimised for UK readers, avoiding redundant UK labels

                    ---

                    **⚠️ Note on Paywalls:** Some sites have paywalls that prevent automatic scraping. If scraping fails, you can always paste the text manually.
                    """)


if __name__ == "__main__":
    main()

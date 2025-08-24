from anthropic import Anthropic
import ftfy
try:
    from fast_langdetect import detect as fast_detect
    FAST_LANGDETECT_AVAILABLE = True
except ImportError:
    FAST_LANGDETECT_AVAILABLE = False
    print("Warning: fast-langdetect not installed. Language detection will use Claude API.")

class ArticleSummarizer:
    def __init__(self, api_key: str):
        """Initialize the summarizer with an API key"""
        if not api_key:
            raise ValueError("API key is required")

        try:
            # Initialize the client with just the API key
            self.anthropic = Anthropic(api_key=api_key)

            # Try to make a minimal API call to validate the key
            self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
        except Exception as e:
            raise ValueError(f"Invalid API key: {str(e)}")

    def _extract_claude_content(self, response):
        """Extract text content from Claude API response structure"""
        try:
            # Handle different response formats
            if hasattr(response, 'content') and response.content:
                # Handle list of content blocks
                if isinstance(response.content, list) and len(response.content) > 0:
                    content_block = response.content[0]
                    if hasattr(content_block, 'text'):
                        return content_block.text
                    elif isinstance(content_block, dict) and 'text' in content_block:
                        return content_block['text']
                # Handle direct content
                elif hasattr(response.content, 'text'):
                    return response.content.text

            # Fallback to string conversion
            return str(response)
        except Exception as e:
            print(f"Error extracting content: {e}")
            return str(response)

    def _fix_api_response_encoding(self, response_text: str) -> str:
        """Fix encoding issues in API response text"""
        if isinstance(response_text, str):
            try:
                return ftfy.fix_text(response_text)
            except:
                # If ftfy fails, return original text
                return response_text
        return response_text

    def _clean_response(self, summary: str) -> str:
        """Clean the response from any formatting artifacts"""
        # Remove any TextBlock formatting or other code-like elements
        if 'TextBlock' in summary:
            import re
            match = re.search(r'text="([^"]+)"', summary)
            if match:
                summary = match.group(1)

        # Fix encoding issues
        summary = self._fix_api_response_encoding(summary)

        # Remove any remaining artifacts
        summary = summary.replace('TextBlock(text="', '').replace('", type="text")', '')

        # Remove line breaks between sentences but preserve the space
        # This handles various types of line breaks
        summary = summary.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')

        # Clean up any multiple spaces that may have been created
        import re
        summary = re.sub(r'\s+', ' ', summary)

        return summary.strip()

    def _build_client_mention_context(self, client_name: str, mention_count: int) -> str:
        """Build contextual instructions for client mentions in the summary"""
        if not client_name or mention_count == 0:
            return ""

        if mention_count == 1:
            context = (f"\n\nIMPORTANT: The client '{client_name}' is mentioned once in this article. "
                      f"You must accurately reflect this single mention in the summary with appropriate context. "
                      f"If the mention is brief or peripheral, do not overemphasise it (especially not in the first sentence). "
                      f"If '{client_name}' is central to the story, position it appropriately. "
                      f"Be accurate about HOW '{client_name}' is described or referenced in the article.")
        elif mention_count <= 3:
            context = (f"\n\nIMPORTANT: The client '{client_name}' is mentioned {mention_count} times in this article. "
                      f"You must accurately reflect these mentions in the summary with appropriate weight and context. "
                      f"If the mentions are brief or peripheral, do not overemphasise them. "
                      f"If '{client_name}' is central to the story, ensure this is clear in the summary. "
                      f"Be accurate about HOW '{client_name}' is described or referenced, maintaining the article's perspective.")
        else:
            context = (f"\n\nIMPORTANT: The client '{client_name}' is mentioned {mention_count} times in this article, "
                      f"suggesting they are likely a significant element of the story. "
                      f"You must accurately reflect '{client_name}'s prominence in the summary while maintaining overall balance. "
                      f"If '{client_name}' is the main focus, this should be clear (potentially in the first sentence). "
                      f"If they are one of several key elements, position them appropriately. "
                      f"Be precise about HOW '{client_name}' is described, what role they play, and maintain the article's tone and perspective.")

        return context

    def detect_language(self, article_text: str) -> dict:
        """
        Detect the language of the article using fast-langdetect or Claude as fallback
        Returns a dict with 'language' and 'is_english' keys
        """
        if not article_text:
            raise ValueError("Article text is required for language detection")

        # Try fast-langdetect first if available
        if FAST_LANGDETECT_AVAILABLE:
            try:
                # Use fast-langdetect for efficient offline detection
                # Clean the text for better detection (remove newlines)
                clean_text = article_text[:2000].replace("\n", " ")
                result = fast_detect(clean_text, low_memory=True)

                # Map language codes to full names
                lang_code = result['lang'].lower()
                confidence = result['score']

                # Common language code mappings
                lang_map = {
                    'en': 'English',
                    'es': 'Spanish',
                    'fr': 'French',
                    'de': 'German',
                    'it': 'Italian',
                    'pt': 'Portuguese',
                    'nl': 'Dutch',
                    'pl': 'Polish',
                    'ru': 'Russian',
                    'zh': 'Chinese',
                    'ja': 'Japanese',
                    'ko': 'Korean',
                    'ar': 'Arabic',
                    'he': 'Hebrew',
                    'hi': 'Hindi',
                    'tr': 'Turkish',
                    'sv': 'Swedish',
                    'da': 'Danish',
                    'no': 'Norwegian',
                    'fi': 'Finnish',
                    'el': 'Greek',
                    'cs': 'Czech',
                    'hu': 'Hungarian',
                    'ro': 'Romanian',
                    'bg': 'Bulgarian',
                    'uk': 'Ukrainian',
                    'vi': 'Vietnamese',
                    'th': 'Thai',
                    'id': 'Indonesian',
                    'ms': 'Malay',
                    'fa': 'Persian',
                    'ur': 'Urdu',
                    'bn': 'Bengali',
                    'ta': 'Tamil',
                    'te': 'Telugu',
                    'ml': 'Malayalam',
                    'ca': 'Catalan',
                    'eu': 'Basque',
                    'gl': 'Galician',
                    'hr': 'Croatian',
                    'sr': 'Serbian',
                    'sk': 'Slovak',
                    'sl': 'Slovenian',
                    'lt': 'Lithuanian',
                    'lv': 'Latvian',
                    'et': 'Estonian',
                    'mk': 'Macedonian',
                    'sq': 'Albanian',
                    'hy': 'Armenian',
                    'ka': 'Georgian',
                    'az': 'Azerbaijani',
                    'kk': 'Kazakh',
                    'uz': 'Uzbek',
                    'tg': 'Tajik',
                    'ky': 'Kyrgyz',
                    'tt': 'Tatar',
                    'ba': 'Bashkir',
                    'cv': 'Chuvash',
                    'ce': 'Chechen',
                    'mn': 'Mongolian',
                    'ne': 'Nepali',
                    'si': 'Sinhala',
                    'km': 'Khmer',
                    'lo': 'Lao',
                    'my': 'Burmese',
                    'am': 'Amharic',
                    'ti': 'Tigrinya',
                    'yo': 'Yoruba',
                    'sw': 'Swahili',
                    'zu': 'Zulu',
                    'xh': 'Xhosa',
                    'af': 'Afrikaans',
                    'cy': 'Welsh',
                    'ga': 'Irish',
                    'gd': 'Scottish Gaelic',
                    'is': 'Icelandic',
                    'mt': 'Maltese',
                    'lb': 'Luxembourgish',
                    'tl': 'Tagalog',
                    'haw': 'Hawaiian',
                    'sm': 'Samoan',
                    'mg': 'Malagasy',
                    'la': 'Latin'
                }

                language = lang_map.get(lang_code, lang_code.upper())

                return {
                    'language': language,
                    'is_english': lang_code == 'en',
                    'confidence': confidence,
                    'method': 'fast-langdetect'
                }

            except Exception as e:
                # If fast-langdetect fails, fall back to Claude API
                print(f"fast-langdetect failed: {e}. Falling back to Claude API.")
                pass

        # Fallback to Claude API method
        prompt = """Identify the language of this article text.

Respond with ONLY the language name in English (e.g., "English", "Spanish", "French", "German", "Italian", "Portuguese", "Dutch", "Polish", "Russian", "Chinese", "Japanese", "Korean", "Arabic", "Hebrew", "Hindi", etc.)

If the text contains multiple languages, identify the PRIMARY language (the one used for the main content).

Article text:
""" + article_text[:1000]  # Use first 1000 chars for language detection

        try:
            # Use Claude Haiku for speed
            message = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=20,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = self._extract_claude_content(message)
            language = self._clean_response(response_text).strip()

            # Normalize common language names
            language_lower = language.lower()
            if 'english' in language_lower:
                language = 'English'
            elif 'spanish' in language_lower or 'español' in language_lower:
                language = 'Spanish'
            elif 'french' in language_lower or 'français' in language_lower:
                language = 'French'
            elif 'german' in language_lower or 'deutsch' in language_lower:
                language = 'German'
            elif 'italian' in language_lower or 'italiano' in language_lower:
                language = 'Italian'
            elif 'portuguese' in language_lower or 'português' in language_lower:
                language = 'Portuguese'
            elif 'dutch' in language_lower or 'nederlands' in language_lower:
                language = 'Dutch'
            elif 'chinese' in language_lower or '中文' in language_lower:
                language = 'Chinese'
            elif 'japanese' in language_lower or '日本語' in language_lower:
                language = 'Japanese'
            elif 'korean' in language_lower or '한국어' in language_lower:
                language = 'Korean'
            elif 'arabic' in language_lower or 'عربي' in language_lower:
                language = 'Arabic'
            elif 'russian' in language_lower or 'русский' in language_lower:
                language = 'Russian'
            elif 'polish' in language_lower or 'polski' in language_lower:
                language = 'Polish'
            elif 'hebrew' in language_lower or 'עברית' in language_lower:
                language = 'Hebrew'
            elif 'hindi' in language_lower or 'हिन्दी' in language_lower:
                language = 'Hindi'

            return {
                'language': language,
                'is_english': language.lower() == 'english',
                'method': 'claude-api'
            }

        except Exception as e:
            # Default to English if detection fails
            return {
                'language': 'English',
                'is_english': True,
                'error': str(e),
                'method': 'default'
            }

    def detect_article_type(self, article_text: str) -> dict:
        """
        Detect the type of article using Claude
        Returns a dict with 'type' and 'explanation' keys
        """
        if not article_text:
            raise ValueError("Article text is required for type detection")

        prompt = """You are an expert journalism classifier. Analyze this article and determine its type.

DEFINITIONS:

1. NEWS - Recent events, announcements, or developments being reported
   - Reports what happened, when, where, who was involved
   - Focuses on facts and timeliness
   - Includes: breaking news, earnings reports, policy announcements, court decisions, data releases
   - Key indicators: "announced", "said", "reported", "revealed", dates/times, official sources

2. OP-ED - Opinion piece expressing the author's personal viewpoint
   - Contains clear argument or thesis
   - Uses "I" or "we" from author's perspective
   - Makes recommendations or calls to action
   - Author's credentials usually mentioned
   - Key indicators: evaluative language, personal pronouns, should/must statements

3. FEATURE - Human interest, lifestyle, or trend pieces with narrative elements
   - Profile pieces about people/organizations
   - Trend analysis or cultural phenomena
   - Lifestyle, travel, food, arts coverage
   - Often has narrative structure or storytelling elements
   - NOT just any long article - must have feature journalism characteristics
   - Key indicators: descriptive scenes, personal anecdotes, broader themes beyond news

4. INTERVIEW - Article primarily presenting someone's views through Q&A or extensive quotes
   - Q&A format OR
   - Article where 50%+ is direct quotes from one person
   - Focuses on interviewee's thoughts/experiences
   - May have brief intro but bulk is their words
   - Key indicators: question-answer structure, "says", extensive quotation marks

CLASSIFICATION RULES:
- If reporting recent events/announcements → NEWS (even if long or analytical)
- If expressing author's opinion → OP-ED
- If Q&A or mostly one person's quotes → INTERVIEW
- Only classify as FEATURE if it has clear feature journalism elements (not just because it's long)

Respond with ONLY: type (reason in parentheses)
Example: "news (reports CBO announcement about tariff impacts)"

Article text:
""" + article_text[:3000]  # Limit to first 3000 chars to avoid token limits

        try:
            # Use Claude Haiku for speed
            message = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = self._extract_claude_content(message)
            response_text = self._clean_response(response_text)

            # Parse the response to extract type and explanation
            response_lower = response_text.lower()

            # Determine the detected type
            detected_type = None
            if response_lower.startswith('news'):
                detected_type = 'news'
            elif response_lower.startswith('op-ed'):
                detected_type = 'op-ed'
            elif response_lower.startswith('feature'):
                detected_type = 'feature'
            elif response_lower.startswith('interview'):
                detected_type = 'interview'
            else:
                # Fallback: try to find any of the types in the response
                for article_type in ['news', 'op-ed', 'feature', 'interview']:
                    if article_type in response_lower:
                        detected_type = article_type
                        break

                if not detected_type:
                    detected_type = 'news'  # Default fallback

            # Extract explanation if present
            explanation = ""
            if '(' in response_text and ')' in response_text:
                start = response_text.find('(')
                end = response_text.find(')', start)
                if start != -1 and end != -1:
                    explanation = response_text[start+1:end]

            return {
                'type': detected_type,
                'explanation': explanation or "Article type detected",
                'raw_response': response_text
            }

        except Exception as e:
            raise Exception(f"Error detecting article type: {str(e)}")

    def _get_system_message(self) -> str:
        """
        Get the system message that establishes Claude's role for concise summarization
        """
        return """You are an expert news summarizer who specializes in creating SHORT, readable, information-dense summaries while maintaining absolute factual accuracy.

CRITICAL ACCURACY RULES:
- NEVER change currencies (if the article mentions dollars, use dollars; if euros, use euros; if pounds, use pounds)
- British English spelling does NOT mean British currency - these are completely separate
- Preserve all numbers, amounts, and financial figures exactly as stated
- Maintain factual accuracy above all else - never alter facts for brevity

UK AUDIENCE CONTEXT:
- Your summaries are written for UK-based readers
- Do NOT add "UK" before UK government officials, institutions, or entities (e.g., write "Technology Secretary" not "UK Technology Secretary", "the government" not "the UK government" when referring to UK entities)
- DO specify country for ALL foreign entities (e.g., "US President", "French government", "German Chancellor", "EU Commission")
- If unclear whether an entity is UK or foreign, err on the side of specifying the country

Your writing style:
- Each sentence should be SHORT but also MUST flow naturally with proper grammar
- Include necessary articles (the, a, an) and conjunctions (that, which, who) for clarity
- Combine related ideas efficiently while maintaining natural speech patterns
- Use precise, specific language over vague terms
- Aim for 15 words per sentence (flexibility for natural flow)
- Every word must contribute to clarity or accuracy

IMPORTANT: Return the summary as a single continuous paragraph with no line breaks between sentences. Sentences should flow together with just spaces between them.

Remember: Readers want maximum information in minimum time with 100% factual accuracy. Think like a telegraph operator who pays per word but NEVER sacrifices accuracy."""

    def get_summary(self, article_text: str, publication: str, article_type: str,
                   author: str = None, specific_instructions: str = None,
                   sentence_count: int = 3, client_name: str = None,
                   client_mention_count: int = None) -> str:
        """
        Get article summary using Claude API

        Args:
            article_text: The article content to summarize
            publication: Name of the publication
            article_type: Type of article (news, op-ed, feature, interview)
            author: Author name (required for op-eds) or interviewee name (for interviews)
            specific_instructions: Optional specific instructions for the summary
            sentence_count: Number of sentences in the summary (2-6)
            client_name: Optional client name to track in the summary
            client_mention_count: Number of times the client is mentioned
        """
        # Validate inputs
        if not article_text or not publication:
            raise ValueError("Article text and publication name are required")
        if article_type == "op-ed" and not author:
            raise ValueError("Author name is required for op-ed articles")
        if not 2 <= sentence_count <= 6:
            raise ValueError("Sentence count must be between 2 and 6")

        # Detect language of the article
        language_info = self.detect_language(article_text)
        detected_language = language_info['language']
        is_english = language_info['is_english']

        # Build the specific instructions part if provided
        instruction_text = ""
        if specific_instructions:
            instruction_text = f" Pay special attention to the following aspects: {specific_instructions}."

        # Build client mention context if provided
        client_context = ""
        if client_name and client_mention_count:
            client_context = self._build_client_mention_context(client_name, client_mention_count)

        # Build language and spelling instructions
        if is_english:
            spelling_instruction = ("Use British English spelling conventions (e.g., 'colour', 'realise', 'centre', 'organisation') "
                                   "but preserve all other details exactly as they appear in the original article, "
                                   "including currencies, locations, measurements, and proper nouns. "
                                   "Do not convert currencies to pounds or change any factual details.")
        else:
            spelling_instruction = (f"IMPORTANT: This article is written in {detected_language}. The summary MUST translate the content to English "
                                   f"and use British English spelling conventions (e.g., 'colour', 'realise', 'centre', 'organisation') in your summary. "
                                   f"However, preserve proper nouns, currencies, and specific terms exactly as they appear. "
                                   f"Do not convert currencies or change any factual details, just translate the text to British English.")

        # Select appropriate prompt based on article type
        if article_type == "news":
            prompt = (f"Summarise this news article in {sentence_count} *short* sentences. {spelling_instruction} Be specific where applicable. Full sentences only, no lists.{instruction_text}{client_context} "
                     f"You MUST begin with '{publication} reports that'\n\nArticle: {article_text}")

        elif article_type == "interview":
            prompt = (f"Summarise this interview article in {sentence_count} *concise* SHORT sentences that flow. {spelling_instruction} Do NOT use 'we' in the summary. Be specific where applicable.{instruction_text}{client_context} "
                    f"For your first sentence: Begin with '{publication} carries an interview with {author}' and include a brief overview of the main topic discussed. "
                    f"For remaining {sentence_count-1} sentences, begin these sentences like  '[author last name] argues/highlights/describes/discusses/notes/cites that'.\n\nArticle: {article_text}")

        elif article_type == "op-ed":
            # For op-eds, first ask Claude to identify the author's role
            try:
                author_role_message = self.anthropic.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system="You are a precise information extractor. Respond only with the requested information, nothing more.",
                    messages=[
                        {
                            "role": "user",
                            "content": f"From this article, extract ONLY the author's role or credentials if mentioned (like their job title, position, or expertise). Do NOT include the author's name in your response. If no role is mentioned, respond with 'NO_ROLE'. Don't include any other text in your response:\n\n{article_text}"
                        }
                    ]
                )

                # Use the new extraction method
                author_role = self._extract_claude_content(author_role_message).strip()

                # Construct the author introduction based on whether a role was found
                if author_role and author_role != 'NO_ROLE':
                    # Remove any instances of the author's name from the role
                    author_role = author_role.replace(author, '').strip()
                    # Clean up any leftover commas or spaces
                    author_role = author_role.strip(' ,')
                    author_intro = f"{author}, {author_role}"
                else:
                    author_intro = author

            except Exception as e:
                print(f"Error getting author role: {e}")
                author_intro = author

            prompt = (f"Summarise this op-ed article in {sentence_count} *concise* SHORT sentences that flow. {spelling_instruction} Do NOT use 'we' in the summary. Be specific where applicable.{instruction_text}{client_context} "
                        f"For your first sentence: Begin with '{publication} carries an op-ed by {author_intro}' and include a brief overview of their main argument. "
                        f"For remaining {sentence_count-1} sentences, begin these sentences like  '[author last name] argues/highlights/describes/discusses/notes/cites that'.\n\nArticle: {article_text}")
        else:  # feature
            prompt = (f"Summarise this feature article in {sentence_count} *concise* quite SHORT sentences that flow. {spelling_instruction} Where applicable begin sentences like 'The article (also) highlights/cites/notes/discusses/examines/suggests'. Do NOT use 'we' in the summary. Be specific where applicable and make sure to convey the broad points of the piece in the summary.{instruction_text}{client_context} "
                     f"You MUST begin with '{publication} carries a feature'\n\nArticle: {article_text}")

        try:
            # Get response from Claude with system message for conciseness
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self._get_system_message(),
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract content using the new method
            summary = self._extract_claude_content(message)

            # Clean the response
            summary = self._clean_response(summary)

            return summary

        except Exception as e:
            raise Exception(f"Error getting summary from Claude: {str(e)}")

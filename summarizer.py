from anthropic import Anthropic

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
                model="claude-3-sonnet-20240229",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
        except Exception as e:
            raise ValueError(f"Invalid API key: {str(e)}")


    def get_summary(self, article_text: str, publication: str, article_type: str, author: str = None, specific_instructions: str = None, sentence_count: int = 3) -> str:
        """
        Get article summary using Claude API
        """
        # Validate inputs
        if not article_text or not publication:
            raise ValueError("Article text and publication name are required")
        if article_type == "op-ed" and not author:
            raise ValueError("Author name is required for op-ed articles")
        if not 2 <= sentence_count <= 6:
            raise ValueError("Sentence count must be between 2 and 6")


        # Build the specific instructions part if provided
        instruction_text = ""
        if specific_instructions:
            instruction_text = f" Pay special attention to the following aspects: {specific_instructions}."

        # Select appropriate prompt based on article type
        if article_type == "news":
            prompt = (f"Summarise this news article in {sentence_count} *short* sentences. Use British English spelling ONLY!!! Be specific where applicable. Full sentences only, no lists. {instruction_text} "
                     f"You MUST begin with '{publication} reports that'\n\nArticle: {article_text}")

        elif article_type == "interview":
            prompt = (f"Summarise this interview article in {sentence_count} *concise* sentences that flow. Use British English spelling ONLY. Do NOT use 'we' in the summary. Be specific where applicable.{instruction_text} "
                    f"For your first sentence: Begin with '{publication} carries an interview with {author}' and include a brief overview of the main topic discussed. "
                    f"For remaining {sentence_count-1} sentences, begin these sentences like  '[author last name] argues/highlights/describes/discusses/notes/cites that'.\n\nArticle: {article_text}")

        elif article_type == "op-ed":
            # For op-eds, first ask Claude to identify the author's role
            author_role_message = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"From this article, extract ONLY the author's role or credentials if mentioned (like their job title, position, or expertise). Do NOT include the author's name in your response. If no role is mentioned, respond with 'NO_ROLE'. Don't include any other text in your response:\n\n{article_text}"
                    }
                ]
            )

            author_role = author_role_message.content[0].text.strip()

            # Construct the author introduction based on whether a role was found
            if author_role and author_role != 'NO_ROLE':
                # Remove any instances of the author's name from the role
                author_role = author_role.replace(author, '').strip()
                # Clean up any leftover commas or spaces
                author_role = author_role.strip(' ,')
                author_intro = f"{author}, {author_role}"
            else:
                author_intro = author

            prompt = (f"Summarise this op-ed article in {sentence_count} *concise* sentences that flow. Use British English spelling ONLY. Do NOT use 'we' in the summary. Be specific where applicable.{instruction_text} "
                        f"For your first sentence: Begin with '{publication} carries an op-ed by {author_intro}' and include a brief overview of their main argument. "
                        f"For remaining {sentence_count-1} sentences, begin these sentences like  '[author last name] argues/highlights/describes/discusses/notes/cites that'.\n\nArticle: {article_text}")
        else:  # feature
            prompt = (f"Summarise this feature article in {sentence_count} sentences. Use British English spelling ONLY and where applicable begin sentences like 'The article (also) highlights/cites/notes/discusses/examines/suggests'. Do NOT use 'we' in the summary. Be specific where applicable and make sure to convey the broad points of the piece in the summary.{instruction_text} "
                     f"You MUST begin with '{publication} carries a feature'\n\nArticle: {article_text}")

        try:
            # Get response from Claude
            message = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Clean the response: remove any TextBlock formatting or other code-like elements
            summary = message.content[0].text

            # Clean the response if it contains TextBlock formatting
            if 'TextBlock' in summary:
                import re
                match = re.search(r'text="([^"]+)"', summary)
                if match:
                    summary = match.group(1)

            return summary.strip()

        except Exception as e:
            raise Exception(f"Error getting summary from Claude: {str(e)}")

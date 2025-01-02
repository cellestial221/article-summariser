# Article Summarizer

A Streamlit web application that uses Claude AI to generate concise summaries of articles while maintaining British English spelling.

## Features

- Supports multiple article types (news, op-ed, feature, interview)
- Customizable summary length (2-6 sentences)
- Optional specific focus instructions
- British English spelling
- Copy to clipboard functionality
- Clean and intuitive interface

## Setup

1. Clone this repository
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Enter your Anthropic API key (get one at https://console.anthropic.com/)
2. Fill in the article details (publication, type, etc.)
3. Paste your article text
4. Click "Summarise" to generate a summary
5. Use the "Copy to Clipboard" button to copy the summary
6. Click "New Article" to start fresh

## Note

You'll need an Anthropic API key to use this application. The API key is required for each session and is not stored.

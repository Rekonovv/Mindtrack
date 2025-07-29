# Mindtrack Telegram Bot

Mindtrack is a Telegram bot designed for personal reflections, journaling, and self-tracking.

With Mindtrack, you can:
- Save your thoughts and reflections privately
- Analyze your notes (AI-powered, optional)
- Track your mental well-being over time

## Features
- Simple and friendly interface
- Secure and private: your data stays with you
- Easy to deploy and use

## Getting Started
1. Clone the repository
2. Create a `.env` file with your Telegram bot token and (optionally) OpenAI API key
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Environment Variables
Create a `.env` file in the root of `mindtrack_bot` with the following content:
```
TELEGRAM_BOT_TOKEN=your_telegram_token_here
OPENAI_API_KEY=your_openai_key_here  # optional
```

## License
MIT

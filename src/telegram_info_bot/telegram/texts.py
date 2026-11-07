def help_text(bot_username: str) -> str:
    return (
        "Commands:\n"
        "/start — meet the bot\n"
        "/me — your ID, name and available profile details\n"
        "/chat — the current chat ID, type and title\n"
        "/help — this guide\n"
        "/privacy — data handling\n\n"
        "A user ID identifies your account; a chat ID identifies the conversation. "
        "They match in a private chat; groups have a separate, usually negative ID. "
        "Use the button below a reply to copy the ID for notification integrations.\n\n"
        f"In groups, use /chat@{bot_username} or /me@{bot_username}. "
        "The bot needs no administrator rights; privacy mode can stay enabled. "
        "Replies in groups are visible to all participants. The bot cannot look up "
        "arbitrary people or reveal hidden information."
    )


PRIVACY_TEXT = (
    "Data handling\n\n"
    "To reply, the bot processes the message received from Telegram: the command, "
    "user and chat IDs, first name, available last name, username, "
    "language, chat type and title. "
    "The application does not store these details in a database, files or user analytics; "
    "message contents, names and IDs are not written to application logs. "
    "HTTP server logs may include IP addresses, request paths, timestamps and status codes.\n\n"
    "Replies in groups are visible to all participants. Use a private chat for your own details. "
    "During development, requests pass through ngrok; local traffic inspection is disabled. "
    "Telegram and ngrok process data under their own policies. "
    "The bot does not control their retention or delete messages or data on their systems."
)

FALLBACK_TEXT = "Use /help for commands. /me shows your ID; /chat shows the current chat ID."

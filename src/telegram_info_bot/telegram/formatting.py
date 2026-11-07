from html import escape

from telegram_info_bot.telegram.models import ChatInfo, UserInfo


def format_user_info(user: UserInfo) -> str:
    lines = [f"ID: <code>{user.id}</code>"]
    lines.append(f"First name: {escape(user.first_name)}")
    if user.last_name:
        lines.append(f"Last name: {escape(user.last_name)}")
    if user.username:
        lines.append(f"Username: @{escape(user.username)}")
    if user.language_code:
        lines.append(f"Language: {escape(user.language_code)}")
    return "\n".join(lines)


def format_chat_info(chat: ChatInfo) -> str:
    lines = [
        f"Chat ID: <code>{chat.id}</code>",
        f"Type: {escape(chat.type)}",
    ]
    if chat.title:
        lines.append(f"Title: {escape(chat.title)}")
    return "\n".join(lines)

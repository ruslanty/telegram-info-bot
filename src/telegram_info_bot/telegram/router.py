from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from telegram_info_bot.telegram.formatting import format_chat_info, format_user_info
from telegram_info_bot.telegram.keyboards import copy_id_keyboard
from telegram_info_bot.telegram.models import ChatInfo, UserInfo
from telegram_info_bot.telegram.texts import FALLBACK_TEXT, PRIVACY_TEXT, help_text


def create_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        text = "Find Telegram IDs for your integrations.\nCommands: /me, /chat, /help, /privacy."
        user = message.from_user
        if message.chat.type == "private" and user and not message.sender_chat:
            text = f"Your Telegram ID: {user.id}\n\n" + text
        await message.answer(text, parse_mode=None)

    @router.message(Command("me"))
    async def me(message: Message) -> None:
        user = message.from_user
        if message.sender_chat or user is None:
            await message.answer(
                "Cannot identify the sender: this message was sent on behalf of a chat "
                "or sender details are unavailable. Send /me in a private chat with the bot.",
                parse_mode=None,
            )
            return
        info = UserInfo(user.id, user.first_name, user.last_name, user.username, user.language_code)
        text = format_user_info(info)
        if message.chat.type != "private":
            text += "\n\nThis reply is visible to everyone in this chat."
        await message.answer(text, parse_mode="HTML", reply_markup=copy_id_keyboard(info.id))

    @router.message(Command("chat"))
    async def chat(message: Message) -> None:
        info = ChatInfo(message.chat.id, message.chat.type, message.chat.title)
        await message.answer(
            format_chat_info(info),
            parse_mode="HTML",
            reply_markup=copy_id_keyboard(info.id),
        )

    @router.message(Command("help"))
    async def help_command(message: Message, bot: Bot) -> None:
        identity = await bot.me()
        await message.answer(help_text(identity.username or ""), parse_mode=None)

    @router.message(Command("privacy"))
    async def privacy_command(message: Message) -> None:
        await message.answer(PRIVACY_TEXT, parse_mode=None)

    # Last route: known commands must be handled before private-chat hints.
    @router.message(F.chat.type == "private", F.text)
    async def private_fallback(message: Message, bot: Bot) -> None:
        words = (message.text or "").split(maxsplit=1)
        command = words[0] if words else ""
        if command.startswith("/") and "@" in command:
            identity = await bot.me()
            if command.partition("@")[2].casefold() != (identity.username or "").casefold():
                return
        await message.answer(FALLBACK_TEXT, parse_mode=None)

    return router

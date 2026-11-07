from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


def copy_id_keyboard(identifier: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Copy ID",
                    copy_text=CopyTextButton(text=str(identifier)),
                )
            ]
        ]
    )

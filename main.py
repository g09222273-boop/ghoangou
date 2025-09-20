import configparser
import json
from typing import Union

from io import BytesIO
from aiogram.types.business_connection import BusinessConnection

import asyncio

from aiogram import (Router, Bot, Dispatcher,
                     F, types)
import logging

from database import Messagesx

router = Router(name=__name__)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read("config.ini")

TOKEN = config["main"]["bot_token"]
USER_ID = config["main"]["user"]


async def send_msg(message_old: str, message_new: Union[str, None], user_fullname: str, user_id: int, bot: Bot = None):
    if message_new is None:
        msg = (f' <b>Пользователь {user_fullname} ({user_id})</b>\n'
               f' <b>Сообщение удалено:</b>\n'
               f' Сообщение:\n<code>{message_old}</code>\n')
    else:
        msg = (f' <b>Пользователь {user_fullname} ({user_id})</b>\n'
               f'✏ <b>Сообщение изменено:</b>\n'
               f' Старое сообщение:\n<code>{message_old}</code>\n'
               f' Новое сообщение:\n<code>{message_new}</code>')
    await bot.send_message(USER_ID, msg, parse_mode='html')


@router.edited_business_message()
async def edited_business_message(message: types.Message):
    if message.from_user.id == message.chat.id:
        user_msg = Messagesx.get(user_id=message.from_user.id)
        data = {message.message_id: message.text}
        if user_msg is None:
            Messagesx.add(user_id=message.from_user.id, message_history=json.dumps(data))
        else:
            msg_history = json.loads(user_msg.message_history)
            if str(message.message_id) in msg_history:
                await send_msg(message_old=msg_history[str(message.message_id)], message_new=message.text,
                               user_fullname=message.from_user.full_name, user_id=message.chat.id, bot=message.bot)
                data = {**msg_history, **data}
                Messagesx.update(user_id=message.from_user.id, message_history=json.dumps(data))


@router.deleted_business_messages()
async def deleted_business_messages(message: types.Message):
    user_msg = Messagesx.get(user_id=message.chat.id)
    if user_msg is not None:
        msg_history = json.loads(user_msg.message_history)
        for msg_id in message.message_ids:
            if str(msg_id) in msg_history:
                await send_msg(message_old=msg_history[str(msg_id)], message_new=None,
                               user_fullname=message.chat.full_name, user_id=message.chat.id, bot=message.bot)
                msg_history.pop(str(msg_id))
                Messagesx.update(user_id=message.chat.id, message_history=json.dumps(msg_history))


@router.business_message(F.text)
async def business_message(message: types.Message):
    if message.from_user.id == message.chat.id:
        user_msg = Messagesx.get(user_id=message.from_user.id)
        data = {message.message_id: message.text}
        if user_msg is None:
            Messagesx.add(user_id=message.from_user.id, message_history=json.dumps(data))
        else:
            msg_history = json.loads(user_msg.message_history)
            data = {**msg_history, **data}
            Messagesx.update(user_id=message.from_user.id, message_history=json.dumps(data))


async def main() -> None:
    Messagesx.create_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    @dp.business_message(F.reply_to_message)
    async def handle_business_media(business_message: Message):
        try:
            business_conn: BusinessConnection = await bot.get_business_connection(
                business_message.business_connection_id
            )

            if not business_message.from_user.id == business_conn.user.id:
                return

            target_message = business_message.reply_to_message

            file_data = None
            filename = None
            caption = None

            if target_message.photo:
                file_data, filename = await download_photo(target_message.photo)
                caption = f" Фото {business_message.from_user.first_name}"

            elif target_message.video:
                file_data, filename = await download_video(target_message.video)
                caption = f" Видео {business_message.from_user.first_name}"

            elif target_message.video_note:
                file_data, filename = await download_video_note(target_message.video_note)
                caption = f" Кружок {business_message.from_user.first_name}"

            if file_data and filename:
                if target_message.caption:
                    caption += f"\n\n Подпись: {target_message.caption}"

                await send_to_owner(
                    business_conn.user.id,
                    file_data,
                    filename,
                    caption
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке медиа: {e}")


    async def download_photo(photos: list[PhotoSize]) -> tuple[BytesIO, str]:   
        file_info = await bot.get_file(photos[-1].file_id)
        file_data = BytesIO()
        await bot.download_file(file_info.file_path, file_data)
        file_data.seek(0)

        filename = f"photo_{photos[-1].file_id}.jpg"
        return file_data, filename


    async def download_video(video: Video) -> tuple[BytesIO, str]:
        file_info = await bot.get_file(video.file_id)
        file_data = BytesIO()
        await bot.download_file(file_info.file_path, file_data)
        file_data.seek(0)

        filename = video.file_name or f"video_{video.file_id}.mp4"
        return file_data, filename


    async def download_video_note(video_note: VideoNote) -> tuple[BytesIO, str]:
        file_info = await bot.get_file(video_note.file_id)
        file_data = BytesIO()
        await bot.download_file(file_info.file_path, file_data)
        file_data.seek(0)

        filename = f"video_note_{video_note.file_id}.mp4"
        return file_data, filename


    async def send_to_owner(
        owner_id: int,
        file_data: BytesIO,
        filename: str,
        caption: str
    ):
        try:
            input_file = BufferedInputFile(file_data.read(), filename=filename)

            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                await bot.send_photo(
                    chat_id=owner_id,
                    photo=input_file,
                    caption=caption
                )
            elif 'video_note' in filename:
                await bot.send_video_note(
                    chat_id=owner_id,
                    video_note=input_file
                )
                if caption:
                    await bot.send_message(owner_id, caption)
            else:
                await bot.send_video(
                    chat_id=owner_id,
                    video=input_file,
                    caption=caption
                )

        except Exception as e:
            logger.error(f"Ошибка при отправке: {e}")
            raise


    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
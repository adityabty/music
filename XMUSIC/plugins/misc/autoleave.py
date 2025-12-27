
import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

import config
from XMUSIC import app
from XMUSIC.misc import SUDOERS
from XMUSIC.core.call import JARVIS, autoend
from XMUSIC.utils.database import get_client, is_active_chat, is_autoend

AUTO_LEAVE = False


@app.on_message(filters.command("autoleave") & SUDOERS)
async def _auto_leave(_, message: Message):
    global AUTO_LEAVE
    if len(message.command) != 2:
        return await message.reply_text("<b>ᴇxᴀᴍᴘʟᴇ :</b>\n\n/autoleave [enable | disable]")
    state = message.command[1].lower()
    if state not in ["enable", "disable"]:
        return await message.reply_text("<b>ᴇxᴀᴍᴘʟᴇ :</b>\n\n/autoleave [enable | disable]")
    AUTO_LEAVE = True if state == "enable" else False
    await message.reply_text(f"Auto leave {'enabled' if AUTO_LEAVE else 'disabled'}.")


async def auto_leave():
    while True:
        await asyncio.sleep(14400)
        if not AUTO_LEAVE:
            continue
        from XMUSIC.core.userbot import assistants
        for num in assistants:
            client = await get_client(num)
            left = 0
            try:
                async for i in client.get_dialogs():
                    if i.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP, ChatType.CHANNEL]:
                        if i.chat.id == config.LOG_GROUP_ID:
                            continue
                        if left >= 10:
                            break
                        if not await is_active_chat(i.chat.id):
                            try:
                                await client.leave_chat(i.chat.id)
                                left += 1
                                await asyncio.sleep(5)
                            except:
                                continue
            except:
                pass


asyncio.create_task(auto_leave())


async def auto_end():
    while True:
        await asyncio.sleep(5)
        if not await is_autoend():
            continue
        for chat_id in list(autoend.keys()):
            timer = autoend.get(chat_id)
            if not timer:
                continue
            if datetime.now() > timer:
                if not await is_active_chat(chat_id):
                    autoend[chat_id] = {}
                    continue
                autoend[chat_id] = {}
                try:
                    await JARVIS.stop_stream(chat_id)
                except:
                    pass
                try:
                    await app.send_message(
                        chat_id,
                        "» ʙᴏᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʟᴇғᴛ ᴠɪᴅᴇᴏᴄʜᴀᴛ ʙᴇᴄᴀᴜsᴇ ɴᴏ ᴏɴᴇ ᴡᴀs ʟɪsᴛᴇɴɪɴɢ ᴏɴ ᴠɪᴅᴇᴏᴄʜᴀᴛ."
                    )
                except:
                    pass


asyncio.create_task(auto_end())

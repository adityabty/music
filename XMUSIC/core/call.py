import asyncio
import os
from datetime import datetime, timedelta
from typing import Union
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall
from ntgcalls import TelegramServerError
from pytgcalls.types import Update, StreamEnded, GroupCallParticipant
from pytgcalls import filters as fl
from pytgcalls.types import AudioQuality, VideoQuality
from pytgcalls.types import MediaStream, ChatUpdate
import config
from config import autoclean
from XMUSIC import LOGGER, YouTube, app
from XMUSIC.misc import db
from XMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from XMUSIC.utils.exceptions import AssistantErr
from XMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from XMUSIC.utils.inline.play import stream_markup
from XMUSIC.utils.thumbnails import get_thumb as gen_thumb
from strings import get_string

autoend = {}
counter = {}

async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)

async def safe_delete(message, delay=0):
    if not message:
        return False
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await message.delete()
        return True
    except:
        return False

async def cleanup_all_messages(chat_id: int):
    pass

class Call(PyTgCalls):
    def __init__(self):
        self.userbot1 = Client(name="JARVISAss1", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING1))
        self.one = PyTgCalls(self.userbot1, cache_duration=100)
        self.userbot2 = Client(name="JARVISAss2", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING2))
        self.two = PyTgCalls(self.userbot2, cache_duration=100)
        self.userbot3 = Client(name="JARVISAss3", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING3))
        self.three = PyTgCalls(self.userbot3, cache_duration=100)
        self.userbot4 = Client(name="JARVISAss4", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING4))
        self.four = PyTgCalls(self.userbot4, cache_duration=100)
        self.userbot5 = Client(name="JARVISAss5", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING5))
        self.five = PyTgCalls(self.userbot5, cache_duration=100)

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_call(chat_id)
        except:
            pass

    async def stop_stream_force(self, chat_id: int):
        try:
            if config.STRING1:
                await self.one.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING2:
                await self.two.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING3:
                await self.three.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING4:
                await self.four.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING5:
                await self.five.leave_call(chat_id)
        except:
            pass
        try:
            await _clear_(chat_id)
        except:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        assistant = await group_assistant(self, chat_id)
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                if str(speed) == str("0.5"):
                    vs = 2.0
                elif str(speed) == str("0.75"):
                    vs = 1.35
                elif str(speed) == str("1.5"):
                    vs = 0.68
                elif str(speed) == str("2.0"):
                    vs = 0.5
                else:
                    vs = 1.0
                proc = await asyncio.create_subprocess_shell(
                    cmd=(f"ffmpeg -i {file_path} -filter:v setpts={vs}*PTS -filter:a atempo={speed} -c:a libopus -b:a 192k -vbr on -compression_level 10 {out}"),
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
        else:
            out = file_path
        dur = await asyncio.get_event_loop().run_in_executor(None, check_duration, out)
        dur = int(dur)
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration = seconds_to_min(dur)
        stream = (MediaStream(out, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p, ffmpeg_parameters=f"-ss {played} -to {duration}") if playing[0]["streamtype"] == "video" else MediaStream(out, audio_parameters=AudioQuality.HIGH, ffmpeg_parameters=f"-ss {played} -to {duration}", video_flags=MediaStream.Flags.IGNORE))
        if str(db[chat_id][0]["file"]) == str(file_path):
            await assistant.play(chat_id, stream)
        else:
            raise AssistantErr("Umm")
        if str(db[chat_id][0]["file"]) == str(file_path):
            exis = (playing[0]).get("old_dur")
            if not exis:
                db[chat_id][0]["old_dur"] = db[chat_id][0]["dur"]
                db[chat_id][0]["old_second"] = db[chat_id][0]["seconds"]
            db[chat_id][0]["played"] = con_seconds
            db[chat_id][0]["dur"] = duration
            db[chat_id][0]["seconds"] = dur
            db[chat_id][0]["speed_path"] = out
            db[chat_id][0]["speed"] = speed

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            check.pop(0)
        except:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def skip_stream(self, chat_id: int, link: str, video: Union[bool, str] = None, image: Union[bool, str] = None):
        assistant = await group_assistant(self, chat_id)
        if video:
            stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p)
        else:
            stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE)
        await assistant.play(chat_id, stream)

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        stream = (MediaStream(file_path, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p, ffmpeg_parameters=f"-ss {to_seek} -to {duration}") if mode == "video" else MediaStream(file_path, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE, ffmpeg_parameters=f"-ss {to_seek} -to {duration}"))
        await assistant.play(chat_id, stream)

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOGGER_ID)
        await assistant.play(config.LOGGER_ID, MediaStream(link, audio_parameters=AudioQuality.HIGH))
        await asyncio.sleep(0.2)
        await assistant.leave_call(config.LOGGER_ID)

    async def join_call(self, chat_id: int, original_chat_id: int, link, video: Union[bool, str] = None, image: Union[bool, str] = None):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)
        if video:
            stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p)
        else:
            stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE)
        try:
            await assistant.play(chat_id, stream)
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except TelegramServerError:
            raise AssistantErr(_["call_10"])
        except Exception as e:
            raise AssistantErr(str(e))
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        
        await asyncio.sleep(0.05)
        
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            if popped:
                rem = popped["file"]
                autoclean.remove(rem)
            if not check:
                await _clear_(chat_id)
                
                buttons = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✙ ᴀᴅᴅ ᴍᴇ ʙᴀʙʏ ✙", 
                                url=f"https://t.me/{app.username}?startgroup=true"
                            ),
                            InlineKeyboardButton(
                                "⌯ ᴄʟᴏsᴇ ⌯", 
                                callback_data="close"
                            )
                        ]
                    ]
                )
                await app.send_message(
                    chat_id,
                    "🎙️",
                    reply_markup=buttons
                )
                return await client.leave_call(chat_id)
        except:
            try:
                await _clear_(chat_id)
                
                buttons = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✙ ᴀᴅᴅ ᴍᴇ ʙᴀʙʏ ✙", 
                                url=f"https://t.me/{app.username}?startgroup=true"
                            ),
                            InlineKeyboardButton(
                                "⌯ ᴄʟᴏsᴇ ⌯", 
                                callback_data="close"
                            )
                        ]
                    ]
                )
                await app.send_message(
                    chat_id,
                    "🎙️",
                    reply_markup=buttons
                )
                return await client.leave_call(chat_id)
            except:
                return
        
        queued = check[0]["file"]
        language = await get_lang(chat_id)
        _ = get_string(language)
        title = (check[0]["title"]).title()
        user = check[0]["by"]
        user_id = check[0]["user_id"]
        original_chat_id = check[0]["chat_id"]
        streamtype = check[0]["streamtype"]
        videoid = check[0]["vidid"]
        db[chat_id][0]["played"] = 0
        exis = (check[0]).get("old_dur")
        if exis:
            db[chat_id][0]["dur"] = exis
            db[chat_id][0]["seconds"] = check[0]["old_second"]
            db[chat_id][0]["speed_path"] = None
            db[chat_id][0]["speed"] = 1.0
        video = True if str(streamtype) == "video" else False
        
        if "live_" in queued:
            n, link = await YouTube.video(videoid, True)
            if n == 0:
                return await app.send_message(original_chat_id, text=_["call_6"])
            if video:
                stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p)
            else:
                stream = MediaStream(link, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE)
            try:
                await client.play(chat_id, stream)
            except:
                return await app.send_message(original_chat_id, text=_["call_6"])
            img = await get_thumb(videoid, user_id)
            button = stream_markup(_, chat_id)
            run = await app.send_photo(chat_id=original_chat_id, photo=img, caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], check[0]["dur"], user, "🎥 Vɪᴅᴇᴏ" if video else "🎵 Aᴜᴅɪᴏ"), reply_markup=InlineKeyboardMarkup(button))
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        elif "index_" in queued:
            stream = (MediaStream(videoid, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p) if str(streamtype) == "video" else MediaStream(videoid, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE))
            try:
                await client.play(chat_id, stream)
            except:
                return await app.send_message(original_chat_id, text=_["call_6"])
            button = stream_markup(_, chat_id)
            run = await app.send_photo(chat_id=original_chat_id, photo=config.STREAM_IMG_URL, caption=_["stream_2"].format(user), reply_markup=InlineKeyboardMarkup(button))
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        else:
            if video:
                stream = MediaStream(queued, audio_parameters=AudioQuality.HIGH, video_parameters=VideoQuality.FHD_1080p)
            else:
                stream = MediaStream(queued, audio_parameters=AudioQuality.HIGH, video_flags=MediaStream.Flags.IGNORE)
            try:
                await client.play(chat_id, stream)
            except:
                return await app.send_message(original_chat_id, text=_["call_6"])
            if videoid == "telegram":
                button = stream_markup(_, chat_id)
                run = await app.send_photo(chat_id=original_chat_id, photo=config.TELEGRAM_AUDIO_URL if str(streamtype) == "audio" else config.TELEGRAM_VIDEO_URL, caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], check[0]["dur"], user, "🎥 Vɪᴅᴇᴏ" if video else "🎵 Aᴜᴅɪᴏ"), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            elif videoid == "soundcloud":
                button = stream_markup(_, chat_id)
                run = await app.send_photo(chat_id=original_chat_id, photo=config.SOUNCLOUD_IMG_URL, caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], check[0]["dur"], user, "🎥 Vɪᴅᴇᴏ" if video else "🎵 Aᴜᴅɪᴏ"), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            else:
                img = await get_thumb(videoid, user_id)
                button = stream_markup(_, chat_id)
                run = await app.send_photo(chat_id=original_chat_id, photo=img, caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], check[0]["dur"], user, "🎥 Vɪᴅᴇᴏ" if video else "🎵 Aᴜᴅɪᴏ"), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"

    async def ping(self):
        pings = []
        if config.STRING1:
            pings.append(self.one.ping)
        if config.STRING2:
            pings.append(self.two.ping)
        if config.STRING3:
            pings.append(self.three.ping)
        if config.STRING4:
            pings.append(self.four.ping)
        if config.STRING5:
            pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3))

    async def start(self):
        LOGGER(__name__).info("» sᴛᴀʀᴛɪɴɢ ᴘʏᴛɢᴄᴀʟʟs ᴄʟɪᴇɴᴛ...")
        if config.STRING1:
            await self.one.start()
        if config.STRING2:
            await self.two.start()
        if config.STRING3:
            await self.three.start()
        if config.STRING4:
            await self.four.start()
        if config.STRING5:
            await self.five.start()

    async def decorators(self):
        @self.one.on_update(fl.chat_update(ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT))
        @self.two.on_update(fl.chat_update(ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT))
        @self.three.on_update(fl.chat_update(ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT))
        @self.four.on_update(fl.chat_update(ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT))
        @self.five.on_update(fl.chat_update(ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT))
        async def stream_services_handler(client, update: Update):
            await self.stop_stream(update.chat_id)
       
        @self.one.on_update(fl.stream_end())
        @self.two.on_update(fl.stream_end())
        @self.three.on_update(fl.stream_end())
        @self.four.on_update(fl.stream_end())
        @self.five.on_update(fl.stream_end())
        async def stream_end_handler1(client: PyTgCalls, update: StreamEnded):
            await self.change_stream(client, update.chat_id)

JARVIS = Call()

from pyrogram import Client, filters
import re
import json
import os

DATA_FILE = "bio_security_data.json"

BAD_DOMAINS = [
    "grabify.link",
    "iplogger.org",
    "cpmlink.net",
    "freegiftcards",
    "discord-nitro",
    "tinyurl.com",
]

URL_REGEX = r"(https?://[^\s]+)"

# ---------------------------------------------
# Load / Save Database
# ---------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"whitelist": [], "warns": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ---------------------------------------------
# Check Bio for Suspicious Links
# ---------------------------------------------
async def scan_user_bio(client, user_id):
    try:
        u = await client.get_users(user_id)
        bio = u.bio or ""
    except:
        return False, []

    links = re.findall(URL_REGEX, bio)
    bad = []

    for link in links:
        if any(d in link.lower() for d in BAD_DOMAINS):
            bad.append(link)

    return bool(bad), bad


# ---------------------------------------------
# AUTO SCAN (Every message)
# ---------------------------------------------
@Client.on_message(filters.group)
async def auto_scan(client, msg):
    user = msg.from_user
    if not user:
        return

    chat_id = msg.chat.id
    user_id = str(user.id)

    # Ignore admins
    m = await client.get_chat_member(chat_id, user.id)
    if m.status in ["administrator", "creator"]:
        return

    # Ignore whitelisted
    if user_id in data["whitelist"]:
        return

    # Scan bio
    bad, links = await scan_user_bio(client, user.id)
    if not bad:
        return

    # Get warn count
    warns = data["warns"].get(user_id, 0)

    if warns < 5:
        data["warns"][user_id] = warns + 1
        save_data(data)

        await msg.reply(
            f"⚠️ **Warning {warns+1}/5 to {user.mention}**\n"
            f"Suspicious link found in bio:\n`{links[0]}`\n"
            f"Fix bio before you get banned."
        )
    else:
        try:
            await client.ban_chat_member(chat_id, int(user_id))
            await msg.reply(f"🚫 **{user.mention} banned after 5 warnings.**")
        except:
            await msg.reply("❌ Ban failed — bot needs admin rights.")


# ---------------------------------------------
# ADMIN COMMANDS
# ---------------------------------------------

@Client.on_message(filters.command("whitelistadd") & filters.group)
async def whitelist_add(client, msg):
    admin = await client.get_chat_member(msg.chat.id, msg.from_user.id)
    if admin.status not in ["administrator", "creator"]:
        return

    if not msg.reply_to_message:
        return await msg.reply("Reply to a user to whitelist.")

    target_id = str(msg.reply_to_message.from_user.id)
    if target_id not in data["whitelist"]:
        data["whitelist"].append(target_id)
        save_data(data)

    await msg.reply("✔ User added to whitelist.")


@Client.on_message(filters.command("whitelistremove") & filters.group)
async def whitelist_remove(client, msg):
    admin = await client.get_chat_member(msg.chat.id, msg.from_user.id)
    if admin.status not in ["administrator", "creator"]:
        return

    if not msg.reply_to_message:
        return await msg.reply("Reply to a user to remove.")

    target_id = str(msg.reply_to_message.from_user.id)
    if target_id in data["whitelist"]:
        data["whitelist"].remove(target_id)
        save_data(data)

    await msg.reply("❌ User removed from whitelist.")
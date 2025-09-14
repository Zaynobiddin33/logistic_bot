from telethon.tl.types import Channel
import asyncio
from telethon import TelegramClient
from datetime import datetime, timedelta
from tokens import *
from functions import get_interval
import uuid
import time
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChatBannedRights
from telethon.tl.types import ChatBannedRights, Channel, ChannelParticipantCreator, ChannelParticipantAdmin
import random

async def can_send_messages(client, chat_id):
    chat = await client.get_entity(chat_id)

    # Case 1: If it's a broadcast channel (not a megagroup) => only admins can post
    if isinstance(chat, Channel) and not chat.megagroup:
        return False

    # Case 2: Check default (global) banned rights
    if getattr(chat, "default_banned_rights", None):
        banned = chat.default_banned_rights
        if isinstance(banned, ChatBannedRights) and banned.send_messages:
            return False

    # Case 3: Check specific participant rights
    try:
        participant = await client(GetParticipantRequest(chat_id, "me"))
        p = participant.participant

        # Creators and admins can always send
        if isinstance(p, (ChannelParticipantCreator, ChannelParticipantAdmin)):
            return True

        # Explicitly banned?
        if getattr(p, "banned_rights", None) and p.banned_rights.send_messages:
            return False

        return True
    except Exception as e:
        # e.g. not a participant, kicked, etc.
        print(f"⚠️ Failed to check {chat_id}: {e}")
        return False


def random_interval(number:int):
    return random.randint(number, number+5)

async def smart_sleep(seconds: float, stop_event: asyncio.Event):
    """Sleep in small chunks so it can stop early if event is set"""
    chunk = 0.5  # half a second
    slept = 0
    while slept < seconds and not stop_event.is_set():
        await asyncio.sleep(min(chunk, seconds - slept))
        slept += chunk


async def get_group_numbers(user_id):
    count = 0
    async with TelegramClient(f'sessions/{user_id}', API_ID, API_HASH) as client:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.megagroup and entity.username:
                count += 1
        return count

from collections import defaultdict

user_stats = defaultdict(lambda: {
    "all_messages": 0,
    "sent": 0,
    "failed": 0,
    "status": "Xabar yuborilmoqda... ⏳"
})

user_stops = defaultdict(asyncio.Event)


async def send_to_all_groups(user_id, text: str):
    stop_event = user_stops[user_id]
    stop_event.clear()

    stats = user_stats[user_id]
    stats.update({"all_messages": 0, "sent": 0, "failed": 0, "status": "Xabar yuborilmoqda... ⏳"})

    sleep_time = get_interval(user_id)
    async with TelegramClient(f'sessions/{user_id}', API_ID, API_HASH) as client:
        # cache dialogs once
        dialogs = [
            d for d in [d async for d in client.iter_dialogs()]
            if isinstance(d.entity, Channel) and d.entity.megagroup and d.entity.username
        ]
        stats["all_messages"] = len(dialogs)*24

        end_time = datetime.now() + timedelta(days=1)
        while datetime.now() < end_time:
            beginning = datetime.now()
            for dialog in dialogs:
                if stop_event.is_set():
                    stats["status"] = "Xabarlar yuborish to'xtatildi ❌"
                    return
                try:
                    if not await can_send_messages(client, dialog.id):
                        stats["failed"] += 1
                        print(f"⚠️ Skipped {dialog.name} (no send rights)")
                        continue
                    await client.send_message(dialog.id, text + f"\n\nID:{str(uuid.uuid4()).replace('-', '')}")
                    stats["sent"] += 1
                    print(f"✅ Sent to: {dialog.name}")
                except Exception as e:
                    stats["failed"] += 1
                    print(f"❌ Failed to send to {dialog.name}: {e}")
                await asyncio.sleep(random_interval(sleep_time))

            # enforce 1-hour minimum cycle
            elapsed = datetime.now() - beginning
            if elapsed < timedelta(hours=1):
                print(f"{(timedelta(hours=1) - elapsed).total_seconds()} seconds sleep")
                await smart_sleep((timedelta(hours=1) - elapsed).total_seconds(), stop_event)

        if not stop_event.is_set():
            stats["status"] = "Xabarlar yuborish yakunlandi ✅"


async def stop_sending_messages(user_id: str):
    user_stops[user_id].set()


def get_stats(user_id: str):
    stats = user_stats[user_id]
    if stats['sent'] != 0:
        percentage = int(stats["sent"] / stats['all_messages'] * 100)
    else:
        percentage = 0

    return (
        f"{stats['status']} \n\n"
        f"Xabar yuborilish statistikasi: \n\n"
        f"{stats['sent']}/{stats['all_messages']} xabar yuborildi\n\n"
        f"{round(percentage/10)*'◽️'}{(10-round(percentage/10))*'◼️'} {percentage}%\n\n"
        f"{datetime.now().strftime('%H:%M:%S')}"
    )
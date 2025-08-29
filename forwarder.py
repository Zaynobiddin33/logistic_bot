from telethon.tl.types import Channel
import asyncio
from telethon import TelegramClient
from datetime import datetime
from tokens import *
from functions import get_interval


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
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.megagroup and entity.username:
                stats["all_messages"] += 1

        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.megagroup and entity.username:
                if stop_event.is_set():
                    stats["status"] = "Xabarlar yuborish to'xtatildi ❌"
                    break
                try:
                    await client.send_message(dialog.id, text)
                    stats["sent"] += 1
                    print(f"✅ Sent to: {dialog.name}")
                    await asyncio.sleep(sleep_time)
                except Exception as e:
                    stats["failed"] += 1
                    print(f"❌ Failed to send to {dialog.name}: {e}")

        if not stop_event.is_set():
            stats["status"] = "Xabarlar yuborish yakunlandi ✅"


def stop_sending_messages(user_id: str):
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
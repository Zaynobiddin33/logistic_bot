from telethon import TelegramClient
import asyncio
import os
from tokens import *

async def main():
    os.makedirs("sessions", exist_ok=True)
    # Log in once with temp_session
    temp_client = TelegramClient("sessions/temp_session", API_ID, API_HASH)
    await temp_client.start()

    # Get logged-in user
    me = await temp_client.get_me()
    user_id = me.id
    print(f"✅ Logged in as {me.first_name} (ID: {user_id})")

    await temp_client.disconnect()

    # Rename the session file instead of logging in again
    old_path = "sessions/temp_session.session"
    new_path = f"sessions/{user_id}.session"
    os.rename(old_path, new_path)
    print(f"✅ Session saved as {new_path}")

if __name__ == "__main__":
    asyncio.run(main())
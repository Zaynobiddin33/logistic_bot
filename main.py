import logging
import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError, PhoneNumberInvalidError
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import Router, F
from aiogram.types import CallbackQuery
from functions import *
from tokens import *
from forwarder import *
import os

admins = ['zaynobiddin_shakhabiddinov', 'lazizbeyy', 'azmvvx']


# Your API ID and API Hash
BOT_TOKEN = BOT_TOKEN
API_ID = API_ID
API_HASH = API_HASH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = Router()
dp.include_router(router)
# Define a state group for the login process

class Form(StatesGroup):
    wait_otp = State()

    wait_message = State()
    wait_confirmed_message = State()
    wait_file = State()
    wait_blocking_id = State()
    wait_unblocking_id = State()


def is_authorized(user_id):
    folder_path = "sessions"  # replace with your folder path
    session_name = f"{user_id}.session"
    file_path = os.path.join(folder_path, session_name)
    return os.path.isfile(file_path)



#LOGIN
class LoginState(StatesGroup):
    waiting_for_contact = State()
    waiting_for_code = State()
    waiting_for_password = State()

# Store temp clients by user_id
temp_clients = {}

@dp.message(Command("login"))
async def start_login(message: types.Message, state: FSMContext):
    if os.path.exists(f'/sessions/{message.from_user.id}.session'):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🏠 Menyuga o'tish", callback_data="start"),
                ]
            ]
        )
        await message.answer("Siz allaqachon registratsiya qilingansiz, botdan foydalanishingiz mumkin.", reply_markup=keyboard)
    else:
        kb = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await state.set_state(LoginState.waiting_for_contact)
        await message.answer("📲 Telefon raqamingizni yuboring:", reply_markup=kb)

@dp.message(F.contact, LoginState.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    session_name = f"sessions/temp_{message.from_user.id}"
    os.makedirs("sessions", exist_ok=True)

    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    temp_clients[message.from_user.id] = client

    try:
        await client.send_code_request(phone)
        await state.update_data(phone=phone)
        await state.set_state(LoginState.waiting_for_code)
        await message.answer("✅ Kod yuborildi.\nIltimos, tasdiqlash kodini raqamlar orasida joy tashlab jo'nating!\n\n(misol: 1 2 3 4 5):", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        await client.disconnect()

@dp.message(LoginState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    phone = user_data["phone"]
    code = message.text.strip().replace(" ", "")
    client = temp_clients[message.from_user.id]

    try:
        await client.sign_in(phone, code)
        me = await client.get_me()

        old_path = f"sessions/temp_{message.from_user.id}.session"
        new_path = f"sessions/{me.id}.session"
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🏠 Menyuga o'tish", callback_data="start"),
                ]
            ]
        )
        await message.answer(f"✅ Muvaffaqiyatli login qildingiz: {me.first_name}", reply_markup=keyboard)
        await client.disconnect()
        del temp_clients[message.from_user.id]
        await state.clear()
    except SessionPasswordNeededError:
        await message.answer("🔐 Ikki bosqichli parol kerak. Parolni yuboring:")
        await state.set_state(LoginState.waiting_for_password)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        await message.answer(f"Login qilishda xatolik yuz berdi. Qayta urinish uchun /login yozuvini bosing")
        if os.path.exists(old_path):
            os.remove(old_path)
        await client.disconnect()
        del temp_clients[message.from_user.id]
        await state.clear()

@dp.message(LoginState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    client = temp_clients[message.from_user.id]

    try:
        await client.sign_in(password=password)
        me = await client.get_me()

        old_path = f"sessions/temp_{message.from_user.id}.session"
        new_path = f"sessions/{me.id}.session"
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🏠 Menyuga o'tish", callback_data="start"),
                ]
            ]
        )
        await message.answer(f"✅ Login muvaffaqiyatli yakunlandi: {me.first_name}", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        await message.answer("Login qilishda xatolik yuz berdi. Qayta urinish uchun /login yozuvini bosing")

        old_path = f"sessions/temp_{message.from_user.id}.session"
        if os.path.exists(old_path):
            os.remove(old_path)

    finally:
        # Always disconnect and clear temp client
        await client.disconnect()
        temp_clients.pop(message.from_user.id, None)
        await state.clear()


@dp.message(Command("help"))
async def help(message:types.Message):
    try:
            await bot.forward_message(
                chat_id=message.chat.id,     # user who pressed /start
                from_chat_id=-1002861245014,     # channel ID
                message_id=2        # exact message in channel
            )
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}")




@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext, is_initial=True):
    if is_initial:
        try:
            await bot.forward_message(
                chat_id=message.chat.id,     # user who pressed /start
                from_chat_id=-1002861245014,     # channel ID
                message_id=2        # exact message in channel
            )
        except Exception as e:
            await message.answer(f"⚠️ Error: {e}")
    user_id = int(message.from_user.id)
    add_users(user_id)
    if not is_user_otp_verified(user_id) and message.from_user.username not in admins:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="OTP kod'ni olishni bilmaysizmi?", callback_data="ask_otp"),
                ]
            ]
        )
        await message.answer("🔐 Siz OTP kod olmagansiz. Kirish uchun OTP kodni kiriting:", reply_markup=keyboard)
        await state.set_state(Form.wait_otp)
    elif message.from_user.username in ['zaynobiddin_shakhabiddinov', 'lazizbeyy', 'imavasix']:
        admin_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="/otp_yaratish"), ],
                [KeyboardButton(text="/userlar_soni"), ],
                [KeyboardButton(text="/block_user"), KeyboardButton(text="/unblock_user")],
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                    InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
                ]
            ]
        )
        if is_initial:
            await message.answer("Salom, admin! Siz tizimdasiz", reply_markup=admin_menu)
        await message.answer("Siz guruhlarga xabar yuborishingiz mumkin", reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                    InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
                ]
            ]
        )
        await message.answer("Siz tizimdasiz. Siz guruhlarga xabar yuborishingiz mumkin", reply_markup=keyboard)

@router.callback_query( F.data == "start")
async def start_callback(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.from_user.id)
    if not is_user_otp_verified(user_id):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="OTP kod'ni olishni bilmaysizmi?", callback_data="ask_otp"),
                ]
            ]
        )
        await callback.message.answer("🔐 Siz OTP kod olmagansiz. Kirish uchun OTP kodni kiriting:", reply_markup=keyboard)
        await state.set_state(Form.wait_otp)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                    InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
                ]
            ]
        )
        await callback.message.edit_text("Siz tizimdasiz. Siz guruhlarga xabar yuborishingiz mumkin", reply_markup=keyboard)


@dp.message(Form.wait_otp)
async def otp_confirm(message:types.Message, state: FSMContext):
    otp = message.text.strip()
    try:
        otp = int(otp)
        if is_free_otp(otp):
            occupy_otp(message.from_user.id, otp)
            keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                    InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
                ]
            ]
            )
            await message.answer("Siz tizimdasiz. Siz guruhlarga xabar yuborishingiz mumkin", reply_markup=keyboard)
        else:
            await message.answer("Noto'g'ri OTP. Qaytadan kiriting:")
    except:
            await message.answer("Avval OTP kirgizing, keyin botdan foydalanasiz")

    await state.clear()

    # except:
    #     message.answer("Parol noto'g'ri kiritilgan. Unda harflar qatnashmaydi. Iltimos haqiqiy parolni qaytadan yuboring.")
    #     state.set_state(Form.wait_otp)

@router.callback_query(F.data == "forward_message")
async def get_message(callback: CallbackQuery, state: FSMContext):
    if not is_blocked_user(callback.from_user.id):
        if is_user_otp_verified(callback.from_user.id):
            if is_authorized(str(callback.from_user.id)):
                await callback.message.edit_text("Tarqatmoqchi bo'lgan xabaringizni yuboring: ")
                await state.set_state(Form.wait_message)
            else:
                await callback.message.answer("Siz hali login qilmagansiz, iltimos login qilish uchun /login yozuvini bosing!")
        else:
            await callback.message.answer('Sizning OTP parolingiz muddati tugagan. Olish uchun @lazizbeyy ga murojat qiliing. Hamda /start tugmasini bosing!')
    else:
        await callback.message.answer("Siz ushbu botda bloklangansiz. Blokdan chiqarilganingizda biz sizga xabar beramiz. \n\nAgar buni xato deb o'ylasangiz adminga murojat qiling.")

@router.callback_query(F.data == "set_interval")
async def interval_list(callback:CallbackQuery):
    keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=" ⚡️ 5-10 sekund", callback_data="interval:fast"),
                        InlineKeyboardButton(text=" 🚗 7-12 sekund", callback_data="interval:medium"),
                        InlineKeyboardButton(text=" 🐌 10-15 sekund", callback_data="interval:slow"),
                    ]
                ]
            )
    await callback.message.edit_text("⏱️ Intervalni tanlang \n\n Interval bu har bir xabarni guruhlarga jo'natish uchun sarflanuvchi vaqt.\n\nE'tiborli bo'ling, xabarlani tez jo'natish akkountingizni spam bo'lishiga sabab bo'lishi mumkin. \n\n Kerakli tezlikni tanlang:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("interval:"))
async def save_interval(callback: CallbackQuery):
    choice = callback.data.split(":")[1]  # "fast", "medium", or "slow"

    # Example mapping to actual time (seconds)
    mapping = {
        "fast": 5,
        "medium": 7,
        "slow": 10
    }
    interval_value = mapping.get(choice, 2)  # default medium
    update_interval(callback.from_user.id, interval_value)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish ", callback_data="start"),
            ],
        ]
        )
    
    await callback.message.edit_text(
        f"✅ Xabar jo'natish intervali {interval_value} sekundga o'rgartirildi",
        reply_markup=keyboard
    )


@dp.message(Form.wait_message)
async def confirm_message(message: types.Message, state: FSMContext):
    # try:
        await state.update_data(user_message = message)
        keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Yo'q ❌", callback_data="start"),
                        InlineKeyboardButton(text="Ha ✅", callback_data="approve_forward"),
                    ]
                ]
            )
        await message.answer(f'Sizda guruhlar soni: {await get_group_numbers(message.from_user.id)}ta.\n\nYuboriladigan xabarlar soni: {await get_group_numbers(message.from_user.id)*24}ta\n\nBu xabarni yuborishga ishonchingiz komilmi?: \n "{message.text.strip()}"', reply_markup=keyboard)
        await state.set_state(Form.wait_confirmed_message)
    # except:
    #     await message.answer('Hozirda faqat matn yuborishga ruxsat etilgan. Matn yuboring!')

@router.callback_query(F.data == "approve_forward", Form.wait_confirmed_message)
async def send_message(callback: CallbackQuery, state:FSMContext):
    data = await state.get_data()
    message = data.get("user_message")

    # Now forward THAT copy from userbot’s chat with the bot
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="To'xtatish ❌", callback_data="stop"),
                    InlineKeyboardButton(text="Yangilash 🔄", callback_data="get_stats"),
                ]
            ]
        )
    await callback.message.edit_text("Xabaringiz jo'natilmoqda...", reply_markup=keyboard)
    await send_to_all_groups(callback.from_user.id, message.text)

    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📝 Yangi xabar jo'natish", callback_data="forward_message"),
                ],
                [
                    InlineKeyboardButton(text="♻️ Qayta yuborish ", callback_data="approve_forward"),
                ],
                [
                    InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="start"),
                ]
            ]
        )
    await callback.message.edit_text(f"{get_stats(callback.from_user.id)}", reply_markup=keyboard)
    # await state.clear() 



@router.callback_query(F.data == "get_stats")
async def statistics(callback:CallbackQuery):
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="❌ To'xtatish", callback_data="stop"),
                    InlineKeyboardButton(text="♻️ Yangilash", callback_data="get_stats"),
                ]
            ]
        )
    await callback.message.edit_text( get_stats(callback.from_user.id), reply_markup=keyboard)

@router.callback_query(F.data == "stop")
async def stop_forwarding(callback:CallbackQuery):
    await stop_sending_messages(callback.from_user.id)
    await callback.message.edit_text(f"{get_stats(callback.from_user.id)}")

#Routers
@router.callback_query(F.data == "ask_otp")
async def info_otp(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="OTP'ni adminlardan oldim. Botdan foydalanish...", callback_data="start"),
                ]
            ])
    await callback.message.edit_text("Siz 1 oylik OTP, ya'ni 1 oylik botdan foydalanish huquqini adminlar @imavasx va @lazizbeyy ga murojaat qilib olishingiz mumkin.", reply_markup=keyboard)
    await callback.answer()  # removes "loading" spinner on the button


@dp.message(Command('otp_yaratish'))
async def create_otp(message:types.Message):
    if message.from_user.username in admins:
        await message.answer(str(generate_otp()))
    else:
        await message.answer("Sizda bu funksiyadan foydalanish vakolati yo'q!")


async def cleanup_task():
    while True:
        now = datetime.utcnow()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        users = sortify_otp()
        for user_id in users:
        # Your task logic here
            await bot.send_message(user_id, "⏰ Sizning bir oylik OTP parolingiz muddati tugadi. Botdan foydalanish uchun iltimos admin orqali to'lov qiling va yangi parol oling.")

@dp.message(Command('userlar_soni'))
async def get_user_number(message: types.Message):
    if message.from_user.username in admins:
        users = get_user_num()
        await message.answer(f'Botdan jami {users}ta odam foydalanmoqda')
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
            ]
                
            ]
        )
        await message.answer("Sizni bu funksiyadan foydalanishga huquqingiz yo'q", reply_markup=keyboard)

@dp.message(Command('block_user'))
async def block_user(message:types.Message, state:FSMContext):
    if message.from_user.username in admins:
        await message.answer("Block qilmoqchi bo'lgan user id'sini yuboring:")
        await state.set_state(Form.wait_blocking_id)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
            ]
                
            ]
        )
        await message.answer("Sizni bu funksiyadan foydalanishga huquqingiz yo'q", reply_markup=keyboard)

@dp.message(Form.wait_blocking_id)
async def finish_blocking(message: types.Message, state:FSMContext):
    try:
        id = int(message.text)
        block_user_from_sending(id)
        await message.answer("✅ Foydalanuvchi bloklandi.")
        await state.clear()
        await start_handler(message, state, is_initial = False)
        return
    except:
        await message.answer("❌ Xatolik. ID raqamni qaytadan kiriting(harf va simvollarsiz):")



@dp.message(Command('unblock_user'))
async def unblock_user(message:types.Message, state:FSMContext):
    if message.from_user.username in admins:
        await message.answer("Blokdan chiqarmoqchi bo'lgan user id'sini yuboring:")
        await state.set_state(Form.wait_unblocking_id)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✉️ Xabar yuborish ", callback_data="forward_message"),
                ],
                [
                InlineKeyboardButton(text="⏱️ Intervalni o'zgartirish ", callback_data="set_interval"),
            ]
                
            ]
        )
        await message.answer("Sizni bu funksiyadan foydalanishga huquqingiz yo'q", reply_markup=keyboard)

@dp.message(Form.wait_unblocking_id)
async def finish_unblocking(message: types.Message, state:FSMContext):
    try:
        id = int(message.text)
        data = unblock_user_from_sending(id)
        if data:
            await message.answer("✅ Foydalanuvchi blokdan chiqarildi.")
            try:
                bot.send_message(chat_id = id, text="Hurmatli foydalanuvchi, siz blokdan chiqarildingiz.\n/start ushbu tugmani bosib, botdan foydalanishingiz mumkin.")
            except:
                pass
            await state.clear()
            await start_handler(message, state, is_initial = False)
        else:
            keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⬅️ Bekor qilish ", callback_data="start"),
                ],
                
            ]
        )
            await message.answer("❌ Bunday foydalanuvchi botda hali bloklanmagan. Qaytadan kiriting:", reply_markup=keyboard)
    except:
        await message.answer("❌ Xatolik. ID raqamni qaytadan kiriting(harf va simvollarsiz):")



async def main():
    asyncio.create_task(cleanup_task()) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
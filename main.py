import logging
import asyncio
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

def is_authorized(user_id):
    folder_path = "sessions"  # replace with your folder path
    session_name = f"{user_id}.session"
    file_path = os.path.join(folder_path, session_name)
    return os.path.isfile(file_path)

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = int(message.from_user.id)
    add_users(user_id)
    if not is_user_otp_verified(user_id):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="OTP kod'ni olishni bilmaysizmi?", callback_data="ask_otp"),
                ]
            ]
        )
        await message.answer("🔐 Siz OTP kod olmagansiz. Kirish uchun OTP kodni kiriting:", reply_markup=keyboard)
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

    # except:
    #     message.answer("Parol noto'g'ri kiritilgan. Unda harflar qatnashmaydi. Iltimos haqiqiy parolni qaytadan yuboring.")
    #     state.set_state(Form.wait_otp)

@router.callback_query(F.data == "forward_message")
async def get_message(callback: CallbackQuery, state: FSMContext):
    if is_user_otp_verified(callback.from_user.id):
        if is_authorized(str(callback.from_user.id)):
            await callback.message.edit_text("Tarqatmoqchi bo'lgan xabaringizni yuboring: ")
            await state.set_state(Form.wait_message)
        else:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Admin tomonidan login qilindim", callback_data="forward_message"),
                    ]
                ]
            )
            await callback.message.answer("Siz admin tomonidan login qilinmagansiz, iltimos adminga murojat qiling: @lazizbeyy \n\n Login qilinganingizdan so'ng pastdagi tugmani bosing.", reply_markup=keyboard)
    else:
        await callback.message.answer('Sizning OTP parolingiz muddati tugagan. Olish uchun /start ustiga bosing!')

@router.callback_query(F.data == "set_interval")
async def interval_list(callback:CallbackQuery):
    keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=" ⚡️ 1 sekund", callback_data="interval:fast"),
                        InlineKeyboardButton(text=" 🚗 3 sekund", callback_data="interval:medium"),
                        InlineKeyboardButton(text=" 🐌 5 sekund", callback_data="interval:slow"),
                    ]
                ]
            )
    await callback.message.edit_text("⏱️ Intervalni tanlang \n\n Interval bu har bir xabarni guruhlarga jo'natish uchun sarflanuvchi vaqt.\n\nE'tiborli bo'ling, xabarlani tez jo'natish akkountingizni spam bo'lishiga sabab bo'lishi mumkin. \n\n Kerakli tezlikni tanlang:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("interval:"))
async def save_interval(callback: CallbackQuery):
    choice = callback.data.split(":")[1]  # "fast", "medium", or "slow"

    # Example mapping to actual time (seconds)
    mapping = {
        "fast": 1,
        "medium": 3,
        "slow": 5
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
    await state.update_data(user_message = message)
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Yo'q ❌", callback_data="start"),
                    InlineKeyboardButton(text="Ha ✅", callback_data="approve_forward"),
                ]
            ]
        )
    await message.answer(f'Sizda guruhlar soni {await get_group_numbers(message.from_user.id)}ta.\n\n Bu xabarni yuborishga ishonchingiz komilmi?: \n "{message.text.strip()}"', reply_markup=keyboard)
    await state.set_state(Form.wait_confirmed_message)

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


@dp.message(Command('add_user'))
async def adding_user(message: types.Message, state: FSMContext):
    if message.from_user.username in ['lazizbeyy', 'zaynobiddin_shakhabiddinov']:
        await message.answer(".session fileni yuboring:")
        await state.set_state(Form.wait_file)
    else:
        await message.answer("Sizda bu funksiyani ishlatish vakolati yo'q!")

@dp.message(Form.wait_file)
async def save_session(message: types.Message, state: FSMContext, bot: Bot):
    folder = "./sessions"
    os.makedirs(folder, exist_ok=True)

    file_id = message.document.file_id
    file_name = message.document.file_name

    file_path = os.path.join(folder, file_name)

    # Download via bot
    await bot.download(message.document, destination=file_path)

    await message.answer(f"✅ {file_name} fayl saqlandi. Fodalanuvchi Botdan ro'yxatdan o'tdi {folder}")
    await state.clear()


@dp.message(Command('create_otp'))
async def create_otp(message:types.Message):
    if message.from_user.username in ['lazizbeyy', 'zaynobiddin_shakhabiddinov']:
        await message.answer(generate_otp())
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

@dp.message(Command('users'))
async def get_user_num(message: types.Message):
    if message.from_user.username in ['imavasx', 'lazizbeyy']:
        users = get_user_num()
        await message.answer(f'Botdan jami {users}ta odam fooydalanmoqda')
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




async def main():
    asyncio.create_task(cleanup_task()) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
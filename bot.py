import asyncio
import logging
import os
from aiogram.filters.command import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from dotenv import find_dotenv, load_dotenv
from ask import main
import chroma

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('TOKEN'), parse_mode=ParseMode.HTML)

dp = Dispatcher()

# Для глобальной переменной 
del_file = None

# Запуск бота
@dp.message(CommandStart())
async def get_start(message: Message):
    name = message.from_user.username
    await message.answer(f'Привет, {name}.\nДавай попробуем разобраться с твоей базой данных. Отправляй мне файлы!')

# Создание папки юзера и загрузки документа
@dp.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    if file_name.endswith('.pdf') or file_name.endswith('.txt'):
        user_folder =  os.path.join(chroma.DATA_PATH, str(user_id)) 
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        await message.bot.download(file=message.document.file_id, destination=os.path.join(user_folder, file_name))
        await message.reply(f"Файл '{file_name}' успешно загружен.")
    else:
        await message.reply("Вы загрузили файл некоррентного формата. Я обрабатываю файлы (.pdf/.txt)")

# Проверка, сколько файлов в папке юзера
@dp.message(Command("check"))
async def check_documents(message: Message):
    user_id = message.from_user.id
    if os.path.exists(os.path.join(chroma.DATA_PATH, str(user_id))):
        user_folder =  os.path.join(chroma.DATA_PATH, str(user_id))
        files = []
        files += os.listdir(user_folder)
        list_file = '\n'.join([f"{i}. '{item}'" for i, item in enumerate(files, 1)])
        if list_file == "":
            await message.reply(f"Вы удалили все файлы")
        else:
            await message.reply(f"В вашей базе данных файлы:\n{list_file}")
    else:
        await message.reply(f"Вы пока ничего не загружали")

# Помощь
@dp.message(Command("help"))
async def check_documents(message: Message):
    await message.answer("Последовательность действий:\n  1. Загружаете файл(.pdf/.txt) или несколько командой\n\
  2. Задаете вопрос\n\nПри повторном вопросе:\n  1. Проверьте какие файлы уже загружены командой /check\n  \
2. Удалить ненужные файлы командой /delete и загрузить новые или пропустить этот пункт\n  3. Задаем вопрос")

@dp.message(Command('clear'))
async def cmd_clear(message: Message, bot: Bot):
    try:
        # Все сообщения, начиная с текущего и до первого (message_id = 0)
        for i in range(message.message_id, 0, -1):
            await bot.delete_message(message.from_user.id, i)
    except TelegramBadRequest as ex:
        # Если сообщение не найдено (уже удалено или не существует), 
        # код ошибки будет "Bad Request: message to delete not found"
        if ex.message == "Bad Request: message to delete not found":
            print("Все сообщения удалены")

# Запрос на удаление файла, на выходе - в дефолт исходе файлы в кнопках
@dp.message(Command("delete"))
async def delete_file(message: Message):
    user_id = message.from_user.id
    user_folder =  os.path.join(chroma.DATA_PATH, str(user_id)) 
    if os.path.exists(user_folder):
        files = os.listdir(user_folder)
        if files:
            inline_buttons = [[InlineKeyboardButton(text=file_name, callback_data=file_name)] for file_name in files]
            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons, resize_keyboard=True)
            await message.reply("Выберите файл для удаления:", reply_markup=keyboard)
        else:
            await message.reply("В папке пользователя нет файлов для удаления.")
    else:
        await message.reply("У вас нет папки с файлами, вы еще ни разу не закружали файлы")

# Определение callback-ов
def callback_query_condition(callback):
    user_id = callback.from_user.id
    data_path = os.path.join(chroma.DATA_PATH, str(user_id))
    return callback.data in os.listdir(data_path)


# На вход - файл, который нужно удалить, на выход - уточнение да/нет
@dp.callback_query(callback_query_condition)
async def process_file_deletion(callback: CallbackQuery):
    global del_file
    del_file = callback.data
    inline_buttons = [[InlineKeyboardButton(text='Точно, удаляй', callback_data='Точно, удаляй')],
                        [InlineKeyboardButton(text='Нет, я еще подумаю', callback_data='Нет, я еще подумаю')]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons, resize_keyboard=True)
    await callback.answer()
    await callback.message.answer(f"Вы уверены, что хотите удалить файл {callback.data}?", reply_markup=keyboard)

# Удаление/отмена удаления
@dp.callback_query(lambda callback_query: callback_query.data in ["Точно, удаляй", "Нет, я еще подумаю"])
async def handle_confirmation(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_folder = os.path.join(chroma.DATA_PATH, str(user_id))
    if callback.data == "Точно, удаляй":
        global del_file
        file_name = del_file
        file_path = os.path.join(user_folder, file_name)
        os.remove(file_path)
        await callback.answer()
        await callback.message.answer(f"Файл {file_name} успешно удален.")
    elif callback.data == "Нет, я еще подумаю":
        await callback.answer()
        await callback.message.answer("Удаление отменено.")

# Вопрос к LLM
@dp.message(F.text)
async def cmd_answer(message: Message):
    user_id = message.from_user.id
    user_folder = os.path.join(chroma.DATA_PATH, str(user_id))
    await message.answer(f"Вопрос принят.\nПридется немного подождать, все LLM работают локально и на CPU")
    await message.answer(chroma.chroma_main(user_folder, user_id))
    await message.answer(await main(message.text, user_id))

# Запуск бота
async def start():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__": 
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print('Exit')
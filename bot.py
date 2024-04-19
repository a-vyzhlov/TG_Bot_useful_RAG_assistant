import asyncio
import logging
import os
from aiogram.filters.command import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher, types, F
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
async def get_start(message: types.Message):
    name = message.from_user.username
    await message.answer(f'Привет, {name}.\nДавай попробуем ответить на твой вопрос')

# Создание папки юзера и загрузки документа
@dp.message(F.document)
async def handle_document(message: types.Message):
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
async def check_documents(message: types.Message):
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
async def check_documents(message: types.Message):
    await message.answer("Последовательность действий:\n  1. Загружаете файл(.pdf/.txt) или несколько командой\n\
  2. Задаете вопрос\n\nПри повторном вопросе:\n  1. Проверьте какие файлы уже загружены командой /check\n  \
2. Удалить ненужные файлы командой /delete и загрузить новые или пропустить этот пункт\n  3. Задаем вопрос")

# Запрос на удаление файла, на выходе - в дефолт исходе файлы в кнопках
@dp.message(Command("delete"))
async def delete_file(message: types.Message):
    user_id = message.from_user.id
    user_folder =  os.path.join(chroma.DATA_PATH, str(user_id)) 
    if os.path.exists(user_folder):
        files = os.listdir(user_folder)
        if files:
            keyboard_buttons = [[KeyboardButton(text=file_name)] for file_name in files]
            keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)
            await message.reply("Выберите файл для удаления:", reply_markup=keyboard)
        else:
            await message.reply("В папке пользователя нет файлов для удаления.")
    else:
        await message.reply("У вас нет папки с файлами, вы еще ни разу не закружали файлы")

# На вход - файл, который нужно удалить, на выход - уточнение да/нет
@dp.message(lambda message: message.text in os.listdir(os.path.join(chroma.DATA_PATH, str(message.from_user.id))))
async def process_file_deletion(message: types.Message):
    global del_file
    del_file = message.text
    keyboard_buttons = [[KeyboardButton(text='Уверен, удаляй!')], [KeyboardButton(text='Нет, я еще подумаю')]]
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)
    await message.reply(f"Вы уверены, что хотите удалить файл {message.text}?", reply_markup=keyboard)

# Удаление/отмена удаления
@dp.message(lambda message: message.text in ["Уверен, удаляй!", "Нет, я еще подумаю"])
async def handle_confirmation(message: types.Message):
    user_id = message.from_user.id
    user_folder = os.path.join(chroma.DATA_PATH, str(user_id))
    if message.text == "Уверен, удаляй!":
        global del_file
        file_name = del_file
        file_path = os.path.join(user_folder, file_name)
        os.remove(file_path)
        await message.reply(f"Файл {file_name} успешно удален.")
    elif message.text == "Нет, я еще подумаю":
        await message.reply("Удаление отменено.")

# Вопрос к LLM
@dp.message(F.text)
async def cmd_answer(message: types.Message):
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
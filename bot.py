import os
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from ask import main
import chroma

router = Router()
# Для глобальной переменной 
del_file = None

# Состояния для избежания лишних промтов
class antiflood(StatesGroup):
    generating_message = State()

# Запуск бота
@router.message(CommandStart())
async def get_start(message: Message, state: FSMContext):
    name = message.from_user.username
    await message.answer(f'Привет, {name}.\nДавай попробуем разобраться с твоей базой данных. Отправляй мне файлы!')

# Создание папки юзера и загрузки документа
@router.message(F.document)
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
@router.message(Command("check"))
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
@router.message(Command("help"))
async def check_documents(message: Message):
    await message.answer("Последовательность действий при первом обращении:\n  1. Загружаете один или несколько файлов(.pdf/.txt)\n\
  2. Задаете вопрос обычным сообщением\n\nПри повторном обращении:\n  1. Проверьте какие файлы уже загружены командой /check\n  \
2. Удалить ненужные файлы командой /delete и загрузить новые или пропустить этот пункт\n  3. Задаем вопрос")

@router.message(Command('clear'))
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
@router.message(Command("delete"))
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
@router.callback_query(callback_query_condition)
async def process_file_deletion(callback: CallbackQuery):
    global del_file
    del_file = callback.data
    inline_buttons = [[InlineKeyboardButton(text='Точно, удаляй', callback_data='Точно, удаляй')],
                        [InlineKeyboardButton(text='Нет, я еще подумаю', callback_data='Нет, я еще подумаю')]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons, resize_keyboard=True)
    await callback.answer()
    await callback.message.answer(f"Вы уверены, что хотите удалить файл {callback.data}?", reply_markup=keyboard)

# Удаление/отмена удаления
@router.callback_query(lambda callback_query: callback_query.data in ["Точно, удаляй", "Нет, я еще подумаю"])
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


# Состояние для антифлуда
@router.message(antiflood.generating_message)
async def anti_flood(message: Message, state: FSMContext):
    await message.reply('Вы еще не получили ответа на свой прошлый вопрос.\nСначала дождитесь ответа, затем задавайте новый вопрос.')

# Вопрос к LLM
@router.message(F.text)
async def cmd_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_folder = os.path.join(chroma.DATA_PATH, str(user_id))
    await state.set_state(antiflood.generating_message)
    await message.answer(f"Вопрос принят.\nПридется немного подождать, все LLM работают локально и на CPU")
    ids = chroma.chroma_main(user_folder, user_id)
    await message.reply(await main(message.text, user_id, ids))
    await state.clear()
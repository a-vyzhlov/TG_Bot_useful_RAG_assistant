# TG_bot Python RAG LLM 
Telegram bot RAG aiogram

Данный бот представляет собой ИИ помощника, а именно RAG систему. Пользователь может загружать файлы (.pdf/.txt), бот создает векторную базу данных по всем файлам и благодаря LLM выдает ответ.    

Модель для создания эмбедингов: **intfloat/multilingual-e5-large**    
Модель для обработки запроса: **IlyaGusev/saiga_mistral_7b_gguf/model-q4_K.gguf**    

Используемые инструменты: `python`, `aiogram`, `langchain`, `chromadb`.

## Установка и настройка:
1. Клонируйте репозиторий:
`` 
git clone https://github.com/a-vyzhlov/TG_Bot_useful_RAG_assistant.git
``

2. Установите зависимости:
``
pip install -r requirements.txt
`` 

3. Настройка бота: Создайте нового бота в Telegram через @BotFather и получите токен.

4. Настройка переменных окружения: В файле .env укажите свой токен бота.

5. Запустите бота:
``
python run.py
``

**Бот имеет следующие команды:**
- `\start`  - начать взаимодействие с ботом
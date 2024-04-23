from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import shutil
import chroma
import os

# Шаблон запроса
PROMPT_TEMPLATE = """
Ответь на вопрос, используя только контексты. 
Вопрос: {question}

Контексты:
---

{context}

---
"""

async def main(query_text, user_id):
   # Создаем БД
    db = Chroma(persist_directory=os.path.join(chroma.CHROMA_PATH, str(user_id)), embedding_function=chroma.get_embeddings())

   # Ищем по БД
   # Мы будем использовать 3 чанка из БД, которые наиболее похожи на вопрос
    results = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(results) == 0 or results[0][1] < 0.7:
        print(f"Нет фрагментов текста, на которые можно опираться для ответа.")
        return

   # Собираем запрос к LLM, объединяя наши чанки.
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    # Подключение к LM Studio и отправка запроса
    model = ChatOpenAI(temperature=0.7, base_url="http://localhost:1234/v1", api_key="lm-studio")
    response_text = model.predict(prompt)

    # Выводим результаты ответа
    sources = [doc.page_content for doc, _score in results]
    rating_sources = '\n\n'.join([f"{i}. '{item}'" for i, item in enumerate(sources, 1)])
    formatted_response = f"Ответ: {response_text}\n\nДанные взяты из 3 отрывков:\n\n{rating_sources}"
    
    #Очистка базы данных
    db.delete_collection()
    db.persist()
    shutil.rmtree(chroma.CHROMA_PATH, str(user_id))
    return(formatted_response)

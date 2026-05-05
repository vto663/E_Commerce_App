\# E\_Commerce\_App



\## Описание

Console приложение за управление на продуктов каталог с MongoDB.



\## Възможности

\- CRUD операции с продукти

\- Full-text search

\- Агрегации и статистики

\- Управление на категории и варианти



\## Инсталация



\### Изисквания

\- Python 3.7+

\- MongoDB



\### Стъпки

```bash

\# 1. Клонирай репозиторито

git clone https://github.com/vto663/E\_Commerce\_App.git



\# 2. Влез в папката

cd E\_Commerce\_App



\# 3. Инсталирай зависимости

pip install pymongo python-dotenv



\# 4. Създай .env файл

echo "MONGO\_URI=mongodb://localhost:27017/" > .env

echo "DB\_NAME=ecommerce\_catalog" >> .env



\# 5. Стартирай приложението

python ecommerce\_store.py


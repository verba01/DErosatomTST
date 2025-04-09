клонировать репозиторий

по очереди ввести в терминале:

pip install poetry

poetry lock

poetry install

docker-compose up -d

alembic upgrade head

запустить main

чтобы делать запросы к базе в терминале ввести команду docker exec -it mycoolapp_db psql -U myuser -d mycoolappdb

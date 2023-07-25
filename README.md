# Webtronics Async API
## Асинхронный API-сервис
### Тестовое задание на позицию python developer.
### Сервис авторизации и управления постами с использованием JWT-токенов.

1. Клонируйте репозиторий.
2. Создайте виртуальное окружение и установите зависимости из файла requirements.txt.
3. Запустите docker-контейнеры с БД PostgreSQL и Redis следующими командами:

```
   docker run --name webtronics_pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=pgpass -e POSTGRES_DB=webtronics -p 5432:5432 -d postgres:15
```

```
   docker run --name webtronics_rd -p 6379:6379 -d redis:latest
```

4. Создайте .env-файл из примера .env.example.
5. Перейдите в рабочий каталог приложения и выполните миграции с помощью команды:

```
   alembic upgrade head
```

8. Запустите отладочный сервер приложения, выполнив команду
   
   ```
     python main.py
   ```

10. Документация к API находится по адресу:

   ```
   http://127.0.0.1:8001/api/openapi
   ```

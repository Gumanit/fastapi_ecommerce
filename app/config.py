import os
from dotenv import load_dotenv


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError(
        "SECRET_KEY не найден в переменных окружения. "
        "Добавьте его в файл .env или установите в системе."
    )
ALGORITHM = "HS256"
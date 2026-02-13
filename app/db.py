import os
import psycopg2
from dotenv import load_dotenv

# load from .env
load_dotenv()

# read variables from env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

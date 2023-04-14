import os
import redis


_database = None

def get_database_connection():
    global _database
    if _database is None:
        database_password = os.environ.get("DATABASE_PASSWORD")
        database_host = os.environ.get("DATABASE_HOST")
        database_port = os.environ.get("DATABASE_PORT")

        _database = redis.Redis(host=database_host, port=database_port, password=database_password, decode_responses=True)
    return _database
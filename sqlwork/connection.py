import sqlite3

db_path = 'OverHeard_user.db'

# Инициализация функции подключения с преобразованием данных рядов 
def get_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
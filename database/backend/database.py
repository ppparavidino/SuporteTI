import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()


SERVER = os.getenv("DB_SERVER", "")
DATABASE = os.getenv("DB_DATABASE", "")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")


connection_string = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


def conectar():
    if not SERVER or not DATABASE:
        raise RuntimeError("DB_SERVER e DB_DATABASE devem estar configurados no ambiente.")
    return pyodbc.connect(connection_string)

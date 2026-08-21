import pyodbc


SERVER = r"localhost\SQLEXPRESS"
DATABASE = "SuporteTI"
DRIVER = "ODBC Driver 18 for SQL Server"


connection_string = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


def conectar():
    return pyodbc.connect(connection_string)
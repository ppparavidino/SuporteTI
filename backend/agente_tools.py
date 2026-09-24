# backend/agente_tools.py
"""
Ferramentas que o agente de IA pode usar para consultar o banco.

Estas funções são chamadas pela IA via "tool calling" (function calling).
A IA decide sozinha qual chamar, com quais parâmetros.

Segurança:
- A conexão usa o usuário 'agente_ia', que é read-only no SQL Server.
- Além disso, validamos o SQL em Python antes de executar.
"""

import os
import re
import pyodbc
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONEXÃO COM O BANCO (usuário read-only)
# ============================================================

def _conectar():
    """Abre conexão com o SQL Server como 'agente_ia' (read-only)."""
    cs = (
        f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_DATABASE')};"
        f"UID={os.getenv('DB_AGENTE_USER')};"
        f"PWD={os.getenv('DB_AGENTE_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(cs)


# ============================================================
# VALIDAÇÃO DE SQL
# ============================================================

# Verbos perigosos que NÃO podem aparecer em queries do agente
PALAVRAS_PROIBIDAS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "REVOKE",
    "DENY", "BACKUP", "RESTORE", "SHUTDOWN", "KILL",
    "sp_", "xp_",  # procedures perigosas
]

# Padrões adicionais
PADROES_PROIBIDOS = [
    r";\s*\w+",           # múltiplos comandos separados por ;
    r"--",                # comentários (podem esconder coisas)
    r"/\*",               # comentários de bloco
    r"\bINTO\b",          # SELECT INTO cria tabela
    r"\bOPENROWSET\b",    # acesso externo
    r"\bOPENDATASOURCE\b",
    r"\bBULK\b",
    r"\bWAITFOR\b",       # pode causar delay
]


def validar_sql(sql: str) -> tuple[bool, str]:
    """
    Valida se o SQL é seguro para executar.
    Retorna (ok, motivo).
    """
    if not sql or not sql.strip():
        return False, "Query vazia."

    sql_upper = sql.upper().strip()

    # 1. Tem que começar com SELECT ou WITH (CTE)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Apenas consultas SELECT são permitidas."

    # 2. Bloqueia verbos perigosos
    for palavra in PALAVRAS_PROIBIDAS:
        # Usa regex para casar palavra inteira, não substring
        if re.search(rf"\b{re.escape(palavra)}\b", sql_upper):
            return False, f"Comando proibido detectado: {palavra}"

    # 3. Bloqueia padrões perigosos
    for padrao in PADROES_PROIBIDOS:
        if re.search(padrao, sql, re.IGNORECASE):
            return False, f"Padrão proibido detectado: {padrao}"

    # 4. Tamanho máximo (evita queries gigantes)
    if len(sql) > 5000:
        return False, "Query muito longa."

    return True, "OK"


# ============================================================
# FERRAMENTA 1 — LISTAR TABELAS
# ============================================================

def listar_tabelas() -> dict:
    """
    Lista todas as tabelas do banco SuporteTI.
    Útil para a IA entender o que existe.
    """
    try:
        con = _conectar()
        cur = con.cursor()
        cur.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tabelas = [row[0] for row in cur.fetchall()]
        con.close()

        return {
            "ok": True,
            "tabelas": tabelas,
            "total": len(tabelas)
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ============================================================
# FERRAMENTA 2 — DESCREVER TABELA
# ============================================================

def descrever_tabela(nome_tabela: str) -> dict:
    """
    Retorna as colunas e tipos de uma tabela específica.
    Útil para a IA entender a estrutura antes de fazer queries.
    """
    # Validação básica do nome (evita SQL injection no nome)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", nome_tabela):
        return {"ok": False, "erro": "Nome de tabela inválido."}

    try:
        con = _conectar()
        cur = con.cursor()
        cur.execute("""
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (nome_tabela,))

        colunas = []
        for row in cur.fetchall():
            colunas.append({
                "nome": row[0],
                "tipo": row[1],
                "permite_nulo": row[2] == "YES",
                "tamanho_max": row[3]
            })

        con.close()

        if not colunas:
            return {"ok": False, "erro": f"Tabela '{nome_tabela}' não encontrada."}

        return {
            "ok": True,
            "tabela": nome_tabela,
            "colunas": colunas,
            "total_colunas": len(colunas)
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ============================================================
# FERRAMENTA 3 — EXECUTAR SQL (a principal)
# ============================================================

def executar_sql(query: str) -> dict:
    """
    Executa uma query SELECT e retorna os dados.

    Validações aplicadas:
    - Só permite SELECT / WITH
    - Bloqueia verbos de escrita
    - Bloqueia múltiplos comandos
    - Limita a 100 linhas
    - Timeout de 15 segundos
    """
    # 1. Valida
    ok, motivo = validar_sql(query)
    if not ok:
        return {
            "ok": False,
            "erro": f"Query rejeitada: {motivo}",
            "query_recebida": query[:200]
        }

    # 2. Força TOP 100 se não tiver TOP nem FETCH
    query_upper = query.upper()
    if "TOP " not in query_upper and "FETCH " not in query_upper:
        # Injeta TOP 100 depois do primeiro SELECT
        query = re.sub(
            r"^\s*SELECT\s+",
            "SELECT TOP 100 ",
            query,
            count=1,
            flags=re.IGNORECASE
        )

    # 3. Executa
    try:
        con = _conectar()
        con.timeout = 15  # segundos
        cur = con.cursor()
        cur.execute(query)

        colunas = [col[0] for col in cur.description]
        linhas = []
        for row in cur.fetchall():
            linhas.append([
                str(v) if v is not None else None
                for v in row
            ])

        con.close()

        return {
            "ok": True,
            "colunas": colunas,
            "linhas": linhas,
            "total_linhas": len(linhas),
            "query_executada": query
        }
    except Exception as e:
        return {
            "ok": False,
            "erro": str(e),
            "query_executada": query
        }


# ============================================================
# DEFINIÇÕES DAS FERRAMENTAS (formato para a IA)
# ============================================================

# Este dicionário descreve as ferramentas no formato que o
# Ollama/OpenAI espera no "tool calling".
DEFINICOES_FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "listar_tabelas",
            "description": (
                "Lista todas as tabelas disponíveis no banco de dados. "
                "Use quando precisar saber quais tabelas existem antes de consultar."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "descrever_tabela",
            "description": (
                "Retorna as colunas e tipos de uma tabela específica. "
                "Use quando precisar entender a estrutura de uma tabela."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_tabela": {
                        "type": "string",
                        "description": "Nome da tabela (ex: chamados, usuarios)"
                    }
                },
                "required": ["nome_tabela"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executar_sql",
            "description": (
                "Executa uma query SQL SELECT no banco e retorna os dados. "
                "Use para responder perguntas sobre os dados. "
                "Retorna no máximo 100 linhas. "
                "Apenas SELECT é permitido."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A query SQL SELECT completa (ex: SELECT TOP 10 * FROM chamados)"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# Mapeia nome da ferramenta -> função Python
FUNCOES_DISPONIVEIS = {
    "listar_tabelas": listar_tabelas,
    "descrever_tabela": descrever_tabela,
    "executar_sql": executar_sql,
}
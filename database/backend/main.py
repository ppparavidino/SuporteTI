from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.auth import criar_hash, verificar_senha
from backend.database import conectar


class CadastroUsuario(BaseModel):
    nome: str
    login: str
    senha: str
    setor_id: int


class LoginUsuario(BaseModel):
    login: str
    senha: str


app = FastAPI()

# ==========================================================
# CORS — liberado para desenvolvimento local (Live Server)
# ==========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/frontend",
    StaticFiles(directory="frontend"),
    name="frontend"
)


@app.get("/login.html")
def pagina_login():
    return FileResponse("frontend/login.html")


@app.get("/cadastro.html")
def pagina_cadastro():
    return FileResponse("frontend/cadastro.html")


@app.get("/")
def inicio():
    return {"mensagem": "API Suporte TI funcionando"}


# ==========================================================
# CADASTRO
# ==========================================================
@app.post("/cadastro")
def cadastrar_usuario(usuario: CadastroUsuario):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        # Verifica se o login já existe
        cursor.execute(
            "SELECT id FROM usuarios WHERE login = ?",
            (usuario.login,)
        )

        existente = cursor.fetchone()

        if existente:
            conexao.close()
            return {"erro": "Este login já está cadastrado."}

        senha_hash = criar_hash(usuario.senha)

        cursor.execute(
            """
            INSERT INTO usuarios
            (nome, login, senha_hash, setor_id, tipo, ativo)
            VALUES (?, ?, ?, ?, 'FUNCIONARIO', 1)
            """,
            (usuario.nome, usuario.login, senha_hash, usuario.setor_id)
        )

        conexao.commit()
        conexao.close()

        return {"mensagem": "Usuário cadastrado com sucesso!"}

    except Exception as e:
        print("ERRO NO CADASTRO:", e)
        return {"erro": f"Erro interno no cadastro: {str(e)}"}


# ==========================================================
# LOGIN
# ==========================================================
@app.post("/login")
def login_usuario(usuario: LoginUsuario):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                login,
                senha_hash,
                setor_id,
                tipo,
                ativo
            FROM usuarios
            WHERE login = ?
            """,
            (usuario.login,)
        )

        resultado = cursor.fetchone()
        conexao.close()

        if not resultado:
            return {"erro": "Login ou senha inválidos."}

        # pyodbc retorna tupla: [0]=id, [1]=nome, [2]=login,
        # [3]=senha_hash, [4]=setor_id, [5]=tipo, [6]=ativo
        user_id = resultado[0]
        nome = resultado[1]
        login = resultado[2]
        senha_hash = resultado[3]
        setor_id = resultado[4]
        tipo = resultado[5]
        ativo = resultado[6]

        if ativo != 1:
            return {"erro": "Usuário desativado."}

        if not verificar_senha(usuario.senha, senha_hash):
            return {"erro": "Login ou senha inválidos."}

        return {
            "mensagem": "Login realizado com sucesso!",
            "usuario": {
                "id": user_id,
                "nome": nome,
                "login": login,
                "setor_id": setor_id,
                "tipo": tipo
            }
        }

    except Exception as e:
        print("ERRO NO LOGIN:", e)
        return {"erro": f"Erro interno no login: {str(e)}"}


# ==========================================================
# LISTAR CHAMADOS
# ==========================================================
@app.get("/chamados")
def listar_chamados():
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.titulo,
                c.descricao,
                c.prioridade,
                c.status,
                solicitante.nome AS solicitante,
                responsavel.nome AS responsavel,
                s.nome AS setor,
                cat.nome AS categoria,
                c.criado_em,
                c.atualizado_em,
                c.resolvido_em
            FROM chamados c
            INNER JOIN usuarios solicitante
                ON c.solicitante_id = solicitante.id
            LEFT JOIN usuarios responsavel
                ON c.responsavel_id = responsavel.id
            INNER JOIN setores s
                ON solicitante.setor_id = s.id
            INNER JOIN categorias cat
                ON c.categoria_id = cat.id
            ORDER BY c.id DESC
        """)

        chamados = []
        for row in cursor.fetchall():
            chamados.append({
                "id": row[0],
                "titulo": row[1],
                "descricao": row[2],
                "prioridade": row[3],
                "status": row[4],
                "solicitante": row[5],
                "responsavel": row[6],
                "setor": row[7],
                "categoria": row[8],
                "criado_em": str(row[9]) if row[9] else None,
                "atualizado_em": str(row[10]) if row[10] else None,
                "resolvido_em": str(row[11]) if row[11] else None
            })

        cursor.close()
        conexao.close()
        return chamados

    except Exception as e:
        print("ERRO AO LISTAR CHAMADOS:", e)
        return {"erro": f"Erro ao listar chamados: {str(e)}"}


# ==========================================================
# DETALHES DE UM CHAMADO
# ==========================================================
@app.get("/chamados/{chamado_id}")
def detalhes_chamado(chamado_id: int):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.titulo,
                c.descricao,
                c.prioridade,
                c.status,
                solicitante.nome AS solicitante,
                responsavel.nome AS responsavel,
                s.nome AS setor,
                cat.nome AS categoria,
                c.criado_em,
                c.atualizado_em,
                c.resolvido_em
            FROM chamados c
            INNER JOIN usuarios solicitante
                ON c.solicitante_id = solicitante.id
            LEFT JOIN usuarios responsavel
                ON c.responsavel_id = responsavel.id
            INNER JOIN setores s
                ON solicitante.setor_id = s.id
            INNER JOIN categorias cat
                ON c.categoria_id = cat.id
            WHERE c.id = ?
        """, (chamado_id,))

        row = cursor.fetchone()
        cursor.close()
        conexao.close()

        if not row:
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        return {
            "id": row[0],
            "titulo": row[1],
            "descricao": row[2],
            "prioridade": row[3],
            "status": row[4],
            "solicitante": row[5],
            "responsavel": row[6],
            "setor": row[7],
            "categoria": row[8],
            "criado_em": str(row[9]) if row[9] else None,
            "atualizado_em": str(row[10]) if row[10] else None,
            "resolvido_em": str(row[11]) if row[11] else None
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO AO BUSCAR CHAMADO:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# LISTAR USUÁRIOS DA TI
# ==========================================================
@app.get("/usuarios/ti")
def listar_usuarios_ti():
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT
                u.id,
                u.nome
            FROM usuarios u
            INNER JOIN setores s
                ON u.setor_id = s.id
            WHERE s.nome = 'Administracao'
               OR s.nome = 'TI'
            ORDER BY u.nome
        """)

        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                "id": row[0],
                "nome": row[1]
            })

        cursor.close()
        conexao.close()
        return usuarios

    except Exception as e:
        print("ERRO AO LISTAR USUARIOS TI:", e)
        return {"erro": str(e)}


# ==========================================================
# ATUALIZAR CHAMADO
# ==========================================================
@app.put("/chamados/{chamado_id}")
def atualizar_chamado(
    chamado_id: int,
    responsavel_id: int | None = None,
    status: str | None = None
):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            "SELECT id FROM chamados WHERE id = ?",
            (chamado_id,)
        )

        if not cursor.fetchone():
            cursor.close()
            conexao.close()
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        campos = []
        valores = []

        if responsavel_id is not None:
            campos.append("responsavel_id = ?")
            valores.append(responsavel_id)

        if status is not None:
            status_permitidos = ["ABERTO", "EM_ANDAMENTO", "RESOLVIDO"]

            if status not in status_permitidos:
                cursor.close()
                conexao.close()
                raise HTTPException(status_code=400, detail="Status inválido")

            campos.append("status = ?")
            valores.append(status)

            if status == "RESOLVIDO":
                campos.append("resolvido_em = GETDATE()")
            else:
                campos.append("resolvido_em = NULL")

        if not campos:
            cursor.close()
            conexao.close()
            raise HTTPException(status_code=400, detail="Nenhuma alteração informada")

        campos.append("atualizado_em = GETDATE()")
        valores.append(chamado_id)

        sql = f"""
            UPDATE chamados
            SET {", ".join(campos)}
            WHERE id = ?
        """

        cursor.execute(sql, valores)
        conexao.commit()
        cursor.close()
        conexao.close()

        return {"mensagem": "Chamado atualizado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO AO ATUALIZAR CHAMADO:", e)
        raise HTTPException(status_code=500, detail=str(e))

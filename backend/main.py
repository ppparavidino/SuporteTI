from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import secrets
from datetime import datetime, timedelta

from backend.auth import criar_hash, verificar_senha
from backend.database import conectar
from backend.email_service import (
    enviar_email_chamado_resolvido,
    enviar_email_recuperacao_senha,
)


class CadastroUsuario(BaseModel):
    nome: str
    login: str
    senha: str
    email: str
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

@app.get("/chamados/{chamado_id}/historico")

# ==========================================================
# CADASTRO
# ==========================================================
@app.post("/cadastro")
def cadastrar_usuario(usuario: CadastroUsuario):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        # Valida e-mail corporativo
        email = usuario.email.strip().lower()
        dominio_ok = "@viacaopendotiba.com.br"

        if not email or "@" not in email:
            conexao.close()
            return {"erro": "Informe um e-mail válido."}

        if not email.endswith(dominio_ok):
            conexao.close()
            return {
                "erro": f"Use o e-mail corporativo ({dominio_ok})."
            }

        # Verifica se o login já existe
        cursor.execute(
            "SELECT id FROM usuarios WHERE login = ?",
            (usuario.login,)
        )
        if cursor.fetchone():
            conexao.close()
            return {"erro": "Este login já está cadastrado."}

        # Verifica se o e-mail já existe
        cursor.execute(
            "SELECT id FROM usuarios WHERE email = ?",
            (email,)
        )
        if cursor.fetchone():
            conexao.close()
            return {"erro": "Este e-mail já está cadastrado."}

        senha_hash = criar_hash(usuario.senha)

        cursor.execute(
            """
            INSERT INTO usuarios
            (nome, login, senha_hash, email, setor_id, perfil, ativo, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, 1, GETDATE())
            """,
            (
                usuario.nome,
                usuario.login,
                senha_hash,
                email,
                usuario.setor_id,
                "FUNCIONARIO"
            )
        )

        conexao.commit()
        conexao.close()

        return {"mensagem": "Usuário cadastrado com sucesso!"}

    except Exception as e:
        print("ERRO NO CADASTRO:", e)
        return {"erro": f"Erro interno no cadastro: {str(e)}"}


# ==========================================================
# LISTAR SETORES (cadastro)
# ==========================================================
@app.get("/setores")
def listar_setores():
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, nome
            FROM setores
            WHERE ativo = 1
            ORDER BY nome
            """
        )

        setores = []
        for row in cursor.fetchall():
            setores.append({
                "id": row[0],
                "nome": row[1]
            })

        cursor.close()
        conexao.close()
        return setores

    except Exception as e:
        print("ERRO AO LISTAR SETORES:", e)
        return {"erro": str(e)}


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
                perfil,
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

        # pyodbc retorna tupla:
        # [0]=id [1]=nome [2]=login [3]=senha_hash
        # [4]=setor_id [5]=perfil [6]=ativo
        user_id = resultado[0]
        nome = resultado[1]
        login = resultado[2]
        senha_hash = resultado[3]
        setor_id = resultado[4]
        perfil = resultado[5]
        ativo = resultado[6]

        if not ativo:
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
                "perfil": perfil
            }
        }

    except Exception as e:
        print("ERRO NO LOGIN:", e)
        return {"erro": f"Erro interno no login: {str(e)}"}


# ==========================================================
# RECUPERAÇÃO DE SENHA
# ==========================================================
class SolicitarRecuperacao(BaseModel):
    email: str


class RedefinirSenha(BaseModel):
    email: str
    codigo: str
    nova_senha: str


@app.post("/recuperar-senha")
def solicitar_recuperacao(dados: SolicitarRecuperacao):
    """
    Gera código de 6 dígitos, grava na tabela recuperacao_senha
    e envia por e-mail. Resposta genérica para não revelar se o e-mail existe.
    """
    try:
        email = dados.email.strip().lower()
        resposta_padrao = {
            "mensagem": "Se o e-mail estiver cadastrado, você receberá um código em instantes."
        }

        if not email or "@" not in email:
            return {"erro": "Informe um e-mail válido."}

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, nome, ativo
            FROM usuarios
            WHERE email = ?
            """,
            (email,)
        )
        row = cursor.fetchone()

        if not row or not row[2]:
            conexao.close()
            return resposta_padrao

        usuario_id = row[0]
        nome = row[1]

        # Código de 6 dígitos
        codigo = f"{secrets.randbelow(1000000):06d}"
        expira = datetime.now() + timedelta(minutes=30)

        # Invalida códigos anteriores deste usuário
        cursor.execute(
            """
            UPDATE recuperacao_senha
            SET usado = 1
            WHERE usuario_id = ? AND usado = 0
            """,
            (usuario_id,)
        )

        cursor.execute(
            """
            INSERT INTO recuperacao_senha
            (usuario_id, codigo, expira_em, usado, criado_em)
            VALUES (?, ?, ?, 0, GETDATE())
            """,
            (usuario_id, codigo, expira)
        )

        conexao.commit()
        conexao.close()

        resultado_email = enviar_email_recuperacao_senha(
            email_destino=email,
            nome=nome,
            codigo=codigo,
        )
        print("E-MAIL RECUPERAÇÃO:", resultado_email)

        return resposta_padrao

    except Exception as e:
        print("ERRO NA RECUPERAÇÃO:", e)
        return {"erro": f"Erro ao solicitar recuperação: {str(e)}"}


@app.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenha):
    """
    Valida código + e-mail e define a nova senha.
    """
    try:
        email = dados.email.strip().lower()
        codigo = dados.codigo.strip()
        nova_senha = dados.nova_senha

        if not email or not codigo or not nova_senha:
            return {"erro": "Preencha e-mail, código e nova senha."}

        if len(nova_senha) < 4:
            return {"erro": "A nova senha deve ter pelo menos 4 caracteres."}

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT u.id
            FROM usuarios u
            WHERE u.email = ? AND u.ativo = 1
            """,
            (email,)
        )
        user = cursor.fetchone()
        if not user:
            conexao.close()
            return {"erro": "Código inválido ou expirado."}

        usuario_id = user[0]

        cursor.execute(
            """
            SELECT id, codigo, expira_em, usado
            FROM recuperacao_senha
            WHERE usuario_id = ? AND usado = 0
            ORDER BY id DESC
            """,
            (usuario_id,)
        )
        token = cursor.fetchone()

        if not token:
            conexao.close()
            return {"erro": "Código inválido ou expirado."}

        token_id = token[0]
        codigo_salvo = str(token[1]).strip()
        expira_em = token[2]

        if codigo_salvo != codigo:
            conexao.close()
            return {"erro": "Código inválido ou expirado."}

        # Compara expiração
        agora = datetime.now()
        if expira_em is not None:
            exp = expira_em
            if hasattr(exp, "replace"):
                try:
                    exp = exp.replace(tzinfo=None)
                except Exception:
                    pass
            if agora > exp:
                conexao.close()
                return {"erro": "Código expirado. Solicite um novo."}

        senha_hash = criar_hash(nova_senha)

        cursor.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?
            """,
            (senha_hash, usuario_id)
        )

        cursor.execute(
            """
            UPDATE recuperacao_senha
            SET usado = 1
            WHERE id = ?
            """,
            (token_id,)
        )

        conexao.commit()
        conexao.close()

        return {"mensagem": "Senha redefinida com sucesso! Faça login com a nova senha."}

    except Exception as e:
        print("ERRO AO REDEFINIR SENHA:", e)
        return {"erro": f"Erro ao redefinir senha: {str(e)}"}


# ==========================================================
# ABRIR CHAMADO
# ==========================================================
class AbrirChamado(BaseModel):
    titulo: str
    descricao: str
    categoria_id: int
    prioridade: str
    solicitante_id: int



@app.post("/chamados")
def criar_chamado(dados: AbrirChamado):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        prioridades_ok = ["BAIXA", "NORMAL", "ALTA", "URGENTE"]
        prioridade = dados.prioridade.upper().strip()
        if prioridade not in prioridades_ok:
            prioridade = "NORMAL"

        # OUTPUT INSERTED.id é mais confiável que SCOPE_IDENTITY no pyodbc
        cursor.execute(
            """
            INSERT INTO chamados
            (titulo, descricao, categoria_id, prioridade, status,
             solicitante_id, criado_em)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, 'ABERTO', ?, GETDATE())
            """,
            (
                dados.titulo,
                dados.descricao,
                dados.categoria_id,
                prioridade,
                dados.solicitante_id
            )
        )

        row = cursor.fetchone()
        novo_id = int(row[0]) if row else None

        if not novo_id:
            conexao.rollback()
            conexao.close()
            return {"erro": "Não foi possível criar o chamado."}

        # Histórico: abertura do chamado
        cursor.execute(
            """
            INSERT INTO historico_chamados
            (chamado_id, usuario_id, acao, descricao, criado_em)
            VALUES (?, ?, ?, ?, GETDATE())
            """,
            (
                novo_id,
                dados.solicitante_id,
                "CRIADO",
                f"Chamado aberto. Título: {dados.titulo}. Prioridade: {prioridade}."
            )
        )

        conexao.commit()
        conexao.close()

        return {
            "mensagem": "Chamado criado com sucesso!",
            "id": novo_id
        }

    except Exception as e:
        print("ERRO AO CRIAR CHAMADO:", e)
        return {"erro": f"Erro ao criar chamado: {str(e)}"}


# ==========================================================
# LISTAR CHAMADOS
# ==========================================================
@app.get("/chamados")
def listar_chamados():
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        # Kanban: abertos/em andamento = todos
        # resolvidos = somente últimos 30 dias
        cursor.execute("""
            SELECT
                c.id,
                c.titulo,
                c.descricao,
                c.prioridade,
                c.status,
                solicitante.nome AS solicitante,
                solicitante.login AS solicitante_login,
                responsavel.nome AS responsavel,
                responsavel.login AS responsavel_login,
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
            WHERE
                c.status IN ('ABERTO', 'EM_ANDAMENTO')
                OR (
                    c.status = 'RESOLVIDO'
                    AND c.resolvido_em >= DATEADD(day, -30, GETDATE())
                )
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
                "solicitante_login": row[6],
                "responsavel": row[7],
                "responsavel_login": row[8],
                "setor": row[9],
                "categoria": row[10],
                "criado_em": str(row[11]) if row[11] else None,
                "atualizado_em": str(row[12]) if row[12] else None,
                "resolvido_em": str(row[13]) if row[13] else None
            })


        cursor.close()
        conexao.close()
        return chamados

    except Exception as e:
        print("ERRO AO LISTAR CHAMADOS:", e)
        return {"erro": f"Erro ao listar chamados: {str(e)}"}


# ==========================================================
# ARQUIVO / HISTÓRICO COMPLETO (todos os chamados)
# ==========================================================
@app.get("/chamados/arquivo")
def listar_arquivo_chamados():
    """
    Lista todos os chamados (sem filtro de 30 dias),
    com dados completos para a página de histórico da TI.
    """
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
                solicitante.login AS solicitante_login,
                responsavel.nome AS responsavel,
                responsavel.login AS responsavel_login,
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
            ORDER BY c.criado_em DESC, c.id DESC
        """)

        chamados = []
        for row in cursor.fetchall():
            chamado_id = row[0]

            # Relatório de resolução (última ação RESOLVIDO)
            cursor.execute(
                """
                SELECT TOP 1 h.descricao, u.nome, u.login
                FROM historico_chamados h
                INNER JOIN usuarios u ON h.usuario_id = u.id
                WHERE h.chamado_id = ? AND h.acao = 'RESOLVIDO'
                ORDER BY h.id DESC
                """,
                (chamado_id,)
            )
            resolucao = cursor.fetchone()

            chamados.append({
                "id": row[0],
                "titulo": row[1],
                "descricao": row[2],
                "prioridade": row[3],
                "status": row[4],
                "solicitante": row[5],
                "solicitante_login": row[6],
                "responsavel": row[7],
                "responsavel_login": row[8],
                "setor": row[9],
                "categoria": row[10],
                "criado_em": str(row[11]) if row[11] else None,
                "atualizado_em": str(row[12]) if row[12] else None,
                "resolvido_em": str(row[13]) if row[13] else None,
                "relatorio_resolucao": resolucao[0] if resolucao else None,
                "resolvido_por": resolucao[1] if resolucao else None,
                "resolvido_por_login": resolucao[2] if resolucao else None,
            })

        cursor.close()
        conexao.close()
        return chamados

    except Exception as e:
        print("ERRO AO LISTAR ARQUIVO:", e)
        return {"erro": f"Erro ao listar arquivo: {str(e)}"}


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
                solicitante.login AS solicitante_login,
                responsavel.nome AS responsavel,
                responsavel.login AS responsavel_login,
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

        if not row:
            cursor.close()
            conexao.close()
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        # Último relatório de resolução (se houver)
        cursor.execute(
            """
            SELECT TOP 1 h.descricao, u.nome, u.login, h.criado_em
            FROM historico_chamados h
            INNER JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.chamado_id = ? AND h.acao = 'RESOLVIDO'
            ORDER BY h.id DESC
            """,
            (chamado_id,)
        )
        resolucao = cursor.fetchone()

        cursor.close()
        conexao.close()

        return {
            "id": row[0],
            "titulo": row[1],
            "descricao": row[2],
            "prioridade": row[3],
            "status": row[4],
            "solicitante": row[5],
            "solicitante_login": row[6],
            "responsavel": row[7],
            "responsavel_login": row[8],
            "setor": row[9],
            "categoria": row[10],
            "criado_em": str(row[11]) if row[11] else None,
            "atualizado_em": str(row[12]) if row[12] else None,
            "resolvido_em": str(row[13]) if row[13] else None,
            "relatorio_resolucao": resolucao[0] if resolucao else None,
            "resolvido_por": resolucao[1] if resolucao else None,
            "resolvido_por_login": resolucao[2] if resolucao else None,
            "resolvido_em_historico": str(resolucao[3]) if resolucao and resolucao[3] else None
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
# ATUALIZAR CHAMADO (+ histórico + relatório)
# ==========================================================
class AtualizarChamado(BaseModel):
    responsavel_id: int | None = None
    status: str | None = None
    usuario_id: int | None = None          # quem está fazendo a alteração
    relatorio: str | None = None           # relatório de resolução


@app.put("/chamados/{chamado_id}")
def atualizar_chamado(chamado_id: int, dados: AtualizarChamado):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                c.id,
                c.status,
                c.responsavel_id,
                c.titulo,
                solicitante.nome,
                solicitante.email
            FROM chamados c
            INNER JOIN usuarios solicitante
                ON c.solicitante_id = solicitante.id
            WHERE c.id = ?
            """,
            (chamado_id,)
        )
        atual = cursor.fetchone()

        if not atual:
            cursor.close()
            conexao.close()
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        status_atual = atual[1]
        responsavel_atual = atual[2]
        titulo_chamado = atual[3]
        nome_solicitante = atual[4]
        email_solicitante = atual[5]


        campos = []
        valores = []
        acoes_historico = []

        # ----- Responsável -----
        if dados.responsavel_id is not None:
            campos.append("responsavel_id = ?")
            valores.append(dados.responsavel_id)

            if dados.responsavel_id != responsavel_atual:
                acoes_historico.append((
                    "ATRIBUIDO",
                    f"Responsável alterado (ID {dados.responsavel_id})."
                ))

        # ----- Status -----
        if dados.status is not None:
            status_permitidos = ["ABERTO", "EM_ANDAMENTO", "RESOLVIDO"]
            status_novo = dados.status.upper().strip()

            if status_novo not in status_permitidos:
                cursor.close()
                conexao.close()
                raise HTTPException(status_code=400, detail="Status inválido")

            # Relatório obrigatório ao resolver
            if status_novo == "RESOLVIDO":
                if not dados.relatorio or not dados.relatorio.strip():
                    cursor.close()
                    conexao.close()
                    raise HTTPException(
                        status_code=400,
                        detail="Informe o relatório de resolução antes de marcar como resolvido."
                    )
                campos.append("status = ?")
                valores.append(status_novo)
                campos.append("resolvido_em = GETDATE()")
                acoes_historico.append((
                    "RESOLVIDO",
                    dados.relatorio.strip()
                ))
            else:
                campos.append("status = ?")
                valores.append(status_novo)
                campos.append("resolvido_em = NULL")

                if status_novo != status_atual:
                    acoes_historico.append((
                        "STATUS",
                        f"Status alterado de {status_atual} para {status_novo}."
                    ))

        # Relatório avulso (sem mudar status) também pode ser registrado
        if (
            dados.relatorio
            and dados.relatorio.strip()
            and (dados.status is None or dados.status.upper().strip() != "RESOLVIDO")
        ):
            acoes_historico.append((
                "RELATORIO",
                dados.relatorio.strip()
            ))

        if not campos and not acoes_historico:
            cursor.close()
            conexao.close()
            raise HTTPException(status_code=400, detail="Nenhuma alteração informada")

        if campos:
            campos.append("atualizado_em = GETDATE()")
            valores.append(chamado_id)
            sql = f"""
                UPDATE chamados
                SET {", ".join(campos)}
                WHERE id = ?
            """
            cursor.execute(sql, valores)

        # Grava histórico
        usuario_hist = dados.usuario_id
        if usuario_hist is None and dados.responsavel_id is not None:
            usuario_hist = dados.responsavel_id

        if usuario_hist is None:
            # fallback: usa o responsável atual do chamado
            usuario_hist = responsavel_atual or 1

        for acao, descricao in acoes_historico:
            cursor.execute(
                """
                INSERT INTO historico_chamados
                (chamado_id, usuario_id, acao, descricao, criado_em)
                VALUES (?, ?, ?, ?, GETDATE())
                """,
                (chamado_id, usuario_hist, acao, descricao)
            )

        conexao.commit()
        cursor.close()
        conexao.close()

        # E-mail automático ao resolver
        email_info = None
        if dados.status and dados.status.upper().strip() == "RESOLVIDO":
            email_info = enviar_email_chamado_resolvido(
                email_destino=email_solicitante or "",
                nome_solicitante=nome_solicitante or "Colaborador",
                chamado_id=chamado_id,
                titulo_chamado=titulo_chamado or "",
                relatorio=(dados.relatorio or "").strip(),
            )
            print("RESULTADO E-MAIL:", email_info)

        resposta = {
            "mensagem": "Chamado atualizado com sucesso",
            "historico_registrado": len(acoes_historico),
        }
        if email_info is not None:
            resposta["email"] = email_info

        return resposta

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO AO ATUALIZAR CHAMADO:", e)
        raise HTTPException(status_code=500, detail=str(e))



# ==========================================================
# HISTÓRICO DO CHAMADO
# ==========================================================
@app.get("/chamados/{chamado_id}/historico")
def listar_historico(chamado_id: int):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                h.id,
                h.acao,
                h.descricao,
                u.nome AS usuario_nome,
                u.login AS usuario_login,
                h.criado_em
            FROM historico_chamados h
            INNER JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.chamado_id = ?
            ORDER BY h.criado_em ASC, h.id ASC
            """,
            (chamado_id,)
        )

        itens = []
        for row in cursor.fetchall():
            itens.append({
                "id": row[0],
                "acao": row[1],
                "descricao": row[2],
                "usuario": row[3],
                "usuario_nome": row[3],
                "usuario_login": row[4],
                "criado_em": str(row[5]) if row[5] else None
            })


        cursor.close()
        conexao.close()
        return itens

    except Exception as e:
        print("ERRO AO LISTAR HISTORICO:", e)
        return {"erro": str(e)}

# ==========================================================
# AGENTE DE IA
# ==========================================================
from backend.agente import perguntar, ollama_online, gerar_sugestoes

class MensagemHistorico(BaseModel):
    role: str       # "user" ou "assistant"
    content: str


class PerguntaAgente(BaseModel):
    pergunta: str
    historico: list[MensagemHistorico] = []


@app.get("/agente/status")
def agente_status():
    """Verifica se o agente está operacional."""
    online = ollama_online()
    return {
        "ollama_online": online,
        "modelo": "llama3.1:8b",
        "mensagem": "Agente pronto." if online else "Ollama não está rodando."
    }


@app.post("/agente")
def agente_perguntar(dados: PerguntaAgente):
    """
    Recebe uma pergunta em linguagem natural e devolve a resposta
    do agente de IA (que consulta o banco quando necessário).
    Aceita histórico opcional para manter contexto da conversa.
    Também retorna 3 sugestões de follow-up.
    """
    try:
        if not dados.pergunta or not dados.pergunta.strip():
            raise HTTPException(status_code=400, detail="Pergunta vazia.")

        # Converte o histórico recebido pro formato que o agente espera
        historico = [
            {"role": m.role, "content": m.content}
            for m in dados.historico
        ]

        # 1. Resposta principal do agente
        resultado = perguntar(dados.pergunta, historico=historico)
        resposta = resultado.get("resposta", "")

        # 2. Sugestões contextuais (chamada separada e rápida)
        sugestoes = gerar_sugestoes(dados.pergunta, resposta)

        return {
            "resposta": resposta,
            "iteracoes": resultado.get("iteracoes", 0),
            "ferramentas_usadas": resultado.get("ferramentas_usadas", []),
            "sugestoes": sugestoes,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO NO AGENTE:", e)
        raise HTTPException(status_code=500, detail=f"Erro no agente: {str(e)}")
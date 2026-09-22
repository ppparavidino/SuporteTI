# backend/anexos.py
"""
Gerenciamento de anexos de chamados.

Armazena arquivos numa pasta de rede (\\TRUENAS\...) e registra
metadados no banco (tabela anexos_chamado).

Validações aplicadas:
- Tamanho máximo (lido do .env)
- Extensões permitidas (lidas do .env)
- MIME type conferido contra a extensão
- Chamado existe?
- Soft delete (LGPD)
"""

import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from backend.database import conectar

load_dotenv()


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ANEXOS_PATH = os.getenv("ANEXOS_PATH", "")
ANEXOS_MAX_MB = int(os.getenv("ANEXOS_MAX_MB", "50"))
ANEXOS_RETENCAO_DIAS = int(os.getenv("ANEXOS_RETENCAO_DIAS", "365"))

_ext_str = os.getenv("ANEXOS_EXTENSOES_PERMITIDAS", "jpg,jpeg,png,pdf,mp4,mov")
EXTENSOES_PERMITIDAS = {e.strip().lower() for e in _ext_str.split(",") if e.strip()}

# MIME types por extensão (validação dupla)
MIMES_PERMITIDOS = {
    "jpg":  ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "png":  ["image/png"],
    "pdf":  ["application/pdf"],
    "mp4":  ["video/mp4"],
    "mov":  ["video/quicktime", "video/mp4"],  # alguns navegadores enviam mp4 pra .mov
}


# ============================================================
# HELPERS
# ============================================================

def _extensao(nome_arquivo: str) -> str:
    """Retorna a extensão (minúscula, sem ponto)."""
    if "." not in nome_arquivo:
        return ""
    return nome_arquivo.rsplit(".", 1)[-1].lower().strip()


def _sanitizar_nome_original(nome: str) -> str:
    """
    Remove caracteres perigosos do nome original.
    Mantém o nome legível mas seguro.
    """
    if not nome:
        return "arquivo"
    # Remove paths
    nome = os.path.basename(nome)
    # Remove caracteres perigosos
    proibidos = '<>:"/\\|?*\0'
    for c in proibidos:
        nome = nome.replace(c, "_")
    # Limita tamanho
    if len(nome) > 200:
        ext = _extensao(nome)
        nome = nome[:190] + ("." + ext if ext else "")
    return nome.strip() or "arquivo"


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_arquivo(nome_original: str, tamanho_bytes: int, mime: str) -> tuple[bool, str]:
    """
    Valida um arquivo antes de aceitar o upload.
    Retorna (ok, motivo).
    """
    if not nome_original:
        return False, "Nome do arquivo ausente."

    if tamanho_bytes <= 0:
        return False, "Arquivo vazio."

    # Tamanho máximo
    max_bytes = ANEXOS_MAX_MB * 1024 * 1024
    if tamanho_bytes > max_bytes:
        return False, f"Arquivo maior que o limite ({ANEXOS_MAX_MB} MB)."

    # Extensão
    ext = _extensao(nome_original)
    if not ext:
        return False, "Arquivo sem extensão."

    if ext not in EXTENSOES_PERMITIDAS:
        permitidas = ", ".join(sorted(EXTENSOES_PERMITIDAS))
        return False, f"Extensão '.{ext}' não permitida. Aceitas: {permitidas}."

    # MIME
    mimes_esperados = MIMES_PERMITIDOS.get(ext, [])
    if mimes_esperados and mime:
        # Alguns navegadores enviam "application/octet-stream" — aceita como fallback
        if mime not in mimes_esperados and mime != "application/octet-stream":
            return False, f"Tipo MIME '{mime}' não confere com a extensão '.{ext}'."

    return True, "OK"


# ============================================================
# NOME ÚNICO
# ============================================================

def gerar_nome_unico(nome_original: str) -> str:
    """Gera um nome único (UUID) mantendo a extensão original."""
    ext = _extensao(nome_original)
    base = uuid.uuid4().hex
    return f"{base}.{ext}" if ext else base


# ============================================================
# CAMINHOS
# ============================================================

def caminho_absoluto(caminho_relativo: str) -> str:
    """Junta ANEXOS_PATH + caminho relativo."""
    if not ANEXOS_PATH:
        raise RuntimeError("ANEXOS_PATH não configurado no .env")
    return os.path.join(ANEXOS_PATH, caminho_relativo)


def _pasta_chamado(chamado_id: int) -> str:
    """Retorna o caminho absoluto da pasta do chamado."""
    return caminho_absoluto(str(chamado_id))


# ============================================================
# ARMAZENAMENTO FÍSICO
# ============================================================

def salvar_arquivo(conteudo: bytes, chamado_id: int, nome_unico: str) -> str:
    """
    Salva o arquivo na pasta do chamado.
    Retorna o caminho relativo (ex: "89/uuid.png").
    """
    pasta = _pasta_chamado(chamado_id)

    # Cria pasta se não existir
    os.makedirs(pasta, exist_ok=True)

    # Caminho completo
    caminho_completo = os.path.join(pasta, nome_unico)

    # Salva
    with open(caminho_completo, "wb") as f:
        f.write(conteudo)

    # Caminho relativo pra salvar no banco
    caminho_relativo = f"{chamado_id}/{nome_unico}"
    return caminho_relativo


def apagar_arquivo_fisico(caminho_relativo: str) -> bool:
    """
    Remove o arquivo do disco (True se removeu ou se já não existia).
    """
    try:
        caminho = caminho_absoluto(caminho_relativo)
        if os.path.exists(caminho):
            os.remove(caminho)
        return True
    except Exception as e:
        print(f"[Anexos] Erro ao apagar arquivo físico: {e}")
        return False


# ============================================================
# BANCO DE DADOS
# ============================================================

def registrar_no_banco(
    chamado_id: int,
    nome_original: str,
    nome_unico: str,
    mime: str,
    tamanho: int,
    caminho_relativo: str,
    enviado_por: int,
    ip_origem: str | None = None,
) -> int | None:
    """
    Insere o registro do anexo no banco.
    Retorna o id do anexo ou None em caso de erro.
    """
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO anexos_chamado
                (chamado_id, nome_original, nome_arquivo, tipo_mime,
                 tamanho_bytes, caminho_relativo, enviado_por, ip_origem)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chamado_id,
                nome_original,
                nome_unico,
                mime,
                tamanho,
                caminho_relativo,
                enviado_por,
                ip_origem,
            ),
        )

        row = cursor.fetchone()
        novo_id = int(row[0]) if row else None

        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    except Exception as e:
        print(f"[Anexos] Erro ao registrar no banco: {e}")
        return None


def listar_anexos(chamado_id: int) -> list:
    """
    Lista os anexos ativos de um chamado.
    """
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                a.id,
                a.nome_original,
                a.nome_arquivo,
                a.tipo_mime,
                a.tamanho_bytes,
                a.caminho_relativo,
                a.enviado_por,
                u.nome AS enviado_por_nome,
                a.ip_origem,
                a.criado_em
            FROM anexos_chamado a
            INNER JOIN usuarios u ON a.enviado_por = u.id
            WHERE a.chamado_id = ? AND a.deletado_em IS NULL
            ORDER BY a.criado_em ASC
            """,
            (chamado_id,),
        )

        anexos = []
        for row in cursor.fetchall():
            anexos.append({
                "id": row[0],
                "nome_original": row[1],
                "nome_arquivo": row[2],
                "tipo_mime": row[3],
                "tamanho_bytes": row[4],
                "caminho_relativo": row[5],
                "enviado_por": row[6],
                "enviado_por_nome": row[7],
                "ip_origem": row[8],
                "criado_em": str(row[9]) if row[9] else None,
            })

        cursor.close()
        conexao.close()
        return anexos

    except Exception as e:
        print(f"[Anexos] Erro ao listar: {e}")
        return []


def buscar_anexo(anexo_id: int) -> dict | None:
    """
    Busca um anexo pelo ID (inclui deletados, pra auditoria).
    """
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                a.id,
                a.chamado_id,
                a.nome_original,
                a.nome_arquivo,
                a.tipo_mime,
                a.tamanho_bytes,
                a.caminho_relativo,
                a.enviado_por,
                a.ip_origem,
                a.criado_em,
                a.deletado_em,
                a.deletado_por,
                a.motivo_delecao
            FROM anexos_chamado a
            WHERE a.id = ?
            """,
            (anexo_id,),
        )

        row = cursor.fetchone()
        cursor.close()
        conexao.close()

        if not row:
            return None

        return {
            "id": row[0],
            "chamado_id": row[1],
            "nome_original": row[2],
            "nome_arquivo": row[3],
            "tipo_mime": row[4],
            "tamanho_bytes": row[5],
            "caminho_relativo": row[6],
            "enviado_por": row[7],
            "ip_origem": row[8],
            "criado_em": str(row[9]) if row[9] else None,
            "deletado_em": str(row[10]) if row[10] else None,
            "deletado_por": row[11],
            "motivo_delecao": row[12],
        }

    except Exception as e:
        print(f"[Anexos] Erro ao buscar: {e}")
        return None


def deletar_anexo(anexo_id: int, usuario_id: int, motivo: str | None = None) -> tuple[bool, str]:
    """
    Soft delete: marca o anexo como deletado no banco e apaga o arquivo físico.
    Retorna (ok, mensagem).
    """
    if not usuario_id:
        return False, "Usuário não informado."

    anexo = buscar_anexo(anexo_id)
    if not anexo:
        return False, "Anexo não encontrado."

    if anexo["deletado_em"]:
        return False, "Anexo já foi deletado."

    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE anexos_chamado
            SET deletado_em = GETDATE(),
                deletado_por = ?,
                motivo_delecao = ?
            WHERE id = ? AND deletado_em IS NULL
            """,
            (usuario_id, motivo or "Sem motivo informado.", anexo_id),
        )

        conexao.commit()
        cursor.close()
        conexao.close()

    except Exception as e:
        print(f"[Anexos] Erro no soft delete: {e}")
        return False, f"Erro ao deletar: {str(e)}"

    # Apaga arquivo físico (best-effort)
    apagar_arquivo_fisico(anexo["caminho_relativo"])

    return True, "Anexo deletado com sucesso."
# backend/laudo.py
"""
Geração de laudo técnico em PDF.

Um laudo por chamado. Se o chamado for resolvido novamente após
reabertura, o mesmo arquivo é sobrescrito (UPDATE no banco).
"""

import os
import hashlib
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from dotenv import load_dotenv

from backend.database import conectar
from backend.anexos import caminho_absoluto

load_dotenv()

ANEXOS_PATH = os.getenv("ANEXOS_PATH", "")


# ============================================================
# HELPERS DE FORMATAÇÃO
# ============================================================

def _formatar_data(valor) -> str:
    """Converte datetime ou string pra 'DD/MM/AAAA HH:MM'."""
    if not valor:
        return "—"
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor.replace("Z", ""))
        except Exception:
            return valor
    try:
        return valor.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def _formatar_tamanho(bytes_valor) -> str:
    """Converte bytes pra '1.2 MB' ou '450 KB'."""
    if not bytes_valor:
        return "0 B"
    try:
        b = float(bytes_valor)
    except Exception:
        return str(bytes_valor)
    if b < 1024:
        return f"{int(b)} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.2f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


# ============================================================
# BUSCA DE DADOS
# ============================================================

def _buscar_dados_chamado(chamado_id: int) -> dict | None:
    """Busca todos os dados necessários pro laudo."""
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                c.id,
                c.titulo,
                c.descricao,
                c.prioridade,
                c.status,
                c.criado_em,
                c.atualizado_em,
                c.resolvido_em,
                solicitante.nome AS solicitante_nome,
                solicitante.login AS solicitante_login,
                solicitante.email AS solicitante_email,
                s.nome AS setor,
                cat.nome AS categoria,
                responsavel.nome AS responsavel_nome,
                responsavel.login AS responsavel_login
            FROM chamados c
            INNER JOIN usuarios solicitante ON c.solicitante_id = solicitante.id
            INNER JOIN setores s ON solicitante.setor_id = s.id
            INNER JOIN categorias cat ON c.categoria_id = cat.id
            LEFT JOIN usuarios responsavel ON c.responsavel_id = responsavel.id
            WHERE c.id = ?
            """,
            (chamado_id,),
        )

        row = cursor.fetchone()
        if not row:
            cursor.close()
            conexao.close()
            return None

        dados = {
            "id": row[0],
            "titulo": row[1],
            "descricao": row[2],
            "prioridade": row[3],
            "status": row[4],
            "criado_em": row[5],
            "atualizado_em": row[6],
            "resolvido_em": row[7],
            "solicitante_nome": row[8],
            "solicitante_login": row[9],
            "solicitante_email": row[10],
            "setor": row[11],
            "categoria": row[12],
            "responsavel_nome": row[13],
            "responsavel_login": row[14],
        }

        # Relatório de resolução (último histórico RESOLVIDO)
        cursor.execute(
            """
            SELECT TOP 1 h.descricao, u.nome, u.login, h.criado_em
            FROM historico_chamados h
            INNER JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.chamado_id = ? AND h.acao = 'RESOLVIDO'
            ORDER BY h.id DESC
            """,
            (chamado_id,),
        )
        r = cursor.fetchone()
        dados["relatorio"] = r[0] if r else None
        dados["resolvido_por_nome"] = r[1] if r else None
        dados["resolvido_por_login"] = r[2] if r else None
        dados["resolvido_em_hist"] = r[3] if r else None

        cursor.close()
        conexao.close()
        return dados

    except Exception as e:
        print(f"[Laudo] Erro ao buscar dados do chamado: {e}")
        return None


def _listar_anexos_do_chamado(chamado_id: int) -> list:
    """Lista metadados dos anexos ativos (sem deletados)."""
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT nome_original, tipo_mime, tamanho_bytes, criado_em
            FROM anexos_chamado
            WHERE chamado_id = ? AND deletado_em IS NULL
            ORDER BY criado_em ASC
            """,
            (chamado_id,),
        )

        anexos = []
        for row in cursor.fetchall():
            anexos.append({
                "nome": row[0],
                "tipo": row[1],
                "tamanho": row[2],
                "criado_em": row[3],
            })

        cursor.close()
        conexao.close()
        return anexos

    except Exception as e:
        print(f"[Laudo] Erro ao listar anexos: {e}")
        return []


# ============================================================
# GERAÇÃO DO PDF
# ============================================================

def _criar_estilos():
    """Cria os estilos do PDF."""
    estilos = getSampleStyleSheet()

    # Cores da identidade
    azul = colors.HexColor("#1d4ed8")
    cinza_escuro = colors.HexColor("#1f2937")
    cinza_medio = colors.HexColor("#6b7280")
    cinza_claro = colors.HexColor("#f3f4f6")

    estilos.add(ParagraphStyle(
        name="TituloEmpresa",
        fontSize=16, leading=20, textColor=azul,
        alignment=TA_LEFT, fontName="Helvetica-Bold",
    ))
    estilos.add(ParagraphStyle(
        name="Subtitulo",
        fontSize=10, leading=13, textColor=cinza_medio,
        alignment=TA_LEFT,
    ))
    estilos.add(ParagraphStyle(
        name="TituloLaudo",
        fontSize=18, leading=22, textColor=cinza_escuro,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
        spaceBefore=12, spaceAfter=6,
    ))
    estilos.add(ParagraphStyle(
        name="SecaoTitulo",
        fontSize=11, leading=14, textColor=azul,
        fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4,
    ))
    estilos.add(ParagraphStyle(
        name="Label",
        fontSize=9, leading=12, textColor=cinza_medio,
        fontName="Helvetica-Bold",
    ))
    estilos.add(ParagraphStyle(
        name="Valor",
        fontSize=10, leading=13, textColor=cinza_escuro,
    ))
    estilos.add(ParagraphStyle(
        name="Rodape",
        fontSize=8, leading=10, textColor=cinza_medio,
        alignment=TA_CENTER,
    ))
    estilos.add(ParagraphStyle(
        name="Hash",
        fontSize=7, leading=9, textColor=cinza_medio,
        alignment=TA_CENTER, fontName="Courier",
    ))

    return estilos


def _paragrafo_label_valor(label: str, valor: str, estilos) -> Table:
    """Cria uma linha 'Label / Valor' formatada."""
    dados = [[
        Paragraph(label, estilos["Label"]),
        Paragraph(str(valor or "—"), estilos["Valor"]),
    ]]
    tabela = Table(dados, colWidths=[4.5 * cm, 11 * cm])
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tabela


def _gerar_pdf(dados: dict, anexos: list, gerado_por_nome: str, gerado_por_login: str, ip: str, versao: int) -> bytes:
    """Gera o PDF do laudo e retorna como bytes."""
    estilos = _criar_estilos()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Laudo Tecnico - Chamado #{dados['id']}",
        author="Suporte TI - Viacao Pendotiba",
    )

    story = []

    # ============ CABEÇALHO ============
    story.append(Paragraph("Viação Pendotiba", estilos["TituloEmpresa"]))
    story.append(Paragraph("Suporte de TI · Central de Atendimento", estilos["Subtitulo"]))
    story.append(Spacer(1, 0.3 * cm))

    # Linha
    linha = Table([[""]], colWidths=[17 * cm], rowHeights=[0.05 * cm])
    linha.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1d4ed8"))]))
    story.append(linha)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("LAUDO TÉCNICO", estilos["TituloLaudo"]))
    story.append(Spacer(1, 0.3 * cm))

    # ============ IDENTIFICAÇÃO ============
    story.append(Paragraph("Identificação do Chamado", estilos["SecaoTitulo"]))
    story.append(_paragrafo_label_valor("Nº do chamado:", f"#{dados['id']}", estilos))
    story.append(_paragrafo_label_valor("Título:", dados["titulo"], estilos))
    story.append(_paragrafo_label_valor("Categoria:", dados["categoria"], estilos))
    story.append(_paragrafo_label_valor("Prioridade:", dados["prioridade"], estilos))
    story.append(_paragrafo_label_valor("Status atual:", dados["status"], estilos))
    story.append(_paragrafo_label_valor("Aberto em:", _formatar_data(dados["criado_em"]), estilos))
    if dados["resolvido_em"]:
        story.append(_paragrafo_label_valor("Resolvido em:", _formatar_data(dados["resolvido_em"]), estilos))

    # ============ SOLICITANTE ============
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Solicitante", estilos["SecaoTitulo"]))
    story.append(_paragrafo_label_valor("Nome:", dados["solicitante_nome"], estilos))
    story.append(_paragrafo_label_valor("Login:", dados["solicitante_login"], estilos))
    story.append(_paragrafo_label_valor("Setor:", dados["setor"], estilos))
    if dados["solicitante_email"]:
        story.append(_paragrafo_label_valor("E-mail:", dados["solicitante_email"], estilos))

    # ============ DESCRIÇÃO ============
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Descrição do Problema", estilos["SecaoTitulo"]))
    descricao = (dados["descricao"] or "—").replace("\n", "<br/>")
    story.append(Paragraph(descricao, estilos["Valor"]))

    # ============ RESOLUÇÃO ============
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Relatório de Resolução", estilos["SecaoTitulo"]))

    if dados["relatorio"]:
        relatorio = dados["relatorio"].replace("\n", "<br/>")
        story.append(Paragraph(relatorio, estilos["Valor"]))
        story.append(Spacer(1, 0.2 * cm))
        if dados["resolvido_por_nome"]:
            story.append(_paragrafo_label_valor(
                "Resolvido por:",
                f"{dados['resolvido_por_nome']} ({dados['resolvido_por_login']})",
                estilos,
            ))
        if dados["resolvido_em_hist"]:
            story.append(_paragrafo_label_valor(
                "Data:",
                _formatar_data(dados["resolvido_em_hist"]),
                estilos,
            ))
    else:
        story.append(Paragraph("Sem relatório registrado.", estilos["Valor"]))

    # ============ ANEXOS ============
    if anexos:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"Evidências Anexadas ({len(anexos)})", estilos["SecaoTitulo"]))

        for i, a in enumerate(anexos, 1):
            texto = f"{i}. {a['nome']} — {_formatar_tamanho(a['tamanho'])}"
            story.append(Paragraph(texto, estilos["Valor"]))

    # ============ ASSINATURA ============
    story.append(Spacer(1, 0.8 * cm))
    linha2 = Table([[""]], colWidths=[17 * cm], rowHeights=[0.05 * cm])
    linha2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d1d5db"))]))
    story.append(linha2)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Assinatura Digital", estilos["SecaoTitulo"]))
    story.append(_paragrafo_label_valor("Responsável:", f"{gerado_por_nome} (login: {gerado_por_login})", estilos))
    story.append(_paragrafo_label_valor("Data de emissão:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), estilos))
    story.append(_paragrafo_label_valor("IP de origem:", ip or "—", estilos))
    story.append(_paragrafo_label_valor("Versão do laudo:", f"v{versao}", estilos))

    # ============ RODAPÉ ============
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Documento gerado automaticamente pelo sistema Suporte TI · Viação Pendotiba",
        estilos["Rodape"],
    ))

    # ============ GERAR ============
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================
# FUNÇÕES PÚBLICAS
# ============================================================

def gerar_laudo(chamado_id: int, gerado_por: int, ip: str = None) -> dict:
    """
    Gera (ou regenera) o laudo do chamado.
    - Se não existe laudo → cria novo registro, versao=1
    - Se já existe       → sobrescreve arquivo, versao += 1

    Retorna dict com ok, caminho, hash, versao ou erro.
    """
    # 1. Busca dados do chamado
    dados = _buscar_dados_chamado(chamado_id)
    if not dados:
        return {"ok": False, "erro": f"Chamado #{chamado_id} não encontrado."}

    # 2. Busca dados do usuário que está gerando
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT nome, login FROM usuarios WHERE id = ?",
            (gerado_por,),
        )
        row = cursor.fetchone()
        cursor.close()
        conexao.close()
        if not row:
            return {"ok": False, "erro": f"Usuário #{gerado_por} não encontrado."}
        gerado_por_nome, gerado_por_login = row[0], row[1]
    except Exception as e:
        return {"ok": False, "erro": f"Erro ao buscar usuário: {e}"}

    # 3. Verifica laudo existente
    laudo_existente = buscar_laudo_existente(chamado_id)
    versao = (laudo_existente["versao"] + 1) if laudo_existente else 1
    eh_novo = laudo_existente is None

    # 4. Lista anexos
    anexos = _listar_anexos_do_chamado(chamado_id)

    # 5. Gera o PDF
    try:
        pdf_bytes = _gerar_pdf(
            dados=dados,
            anexos=anexos,
            gerado_por_nome=gerado_por_nome,
            gerado_por_login=gerado_por_login,
            ip=ip,
            versao=versao,
        )
    except Exception as e:
        print(f"[Laudo] Erro ao gerar PDF: {e}")
        return {"ok": False, "erro": f"Erro ao gerar PDF: {e}"}

    # 6. Calcula hash
    hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # 7. Salva no disco (TrueNAS)
    nome_arquivo = f"laudo_{chamado_id}.pdf"
    caminho_relativo = f"{chamado_id}/laudos/{nome_arquivo}"

    try:
        caminho_completo = caminho_absoluto(caminho_relativo)
        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

        with open(caminho_completo, "wb") as f:
            f.write(pdf_bytes)

        tamanho = len(pdf_bytes)
    except Exception as e:
        print(f"[Laudo] Erro ao salvar arquivo: {e}")
        return {"ok": False, "erro": f"Erro ao salvar PDF: {e}"}

    # 8. Registra/atualiza no banco
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        if eh_novo:
            cursor.execute(
                """
                INSERT INTO laudos_chamado
                    (chamado_id, nome_arquivo, caminho_relativo, tamanho_bytes,
                     hash_sha256, gerado_por, ip_origem, versao)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (chamado_id, nome_arquivo, caminho_relativo, tamanho,
                 hash_sha256, gerado_por, ip),
            )
            laudo_id = int(cursor.fetchone()[0])
        else:
            laudo_id = laudo_existente["id"]
            cursor.execute(
                """
                UPDATE laudos_chamado
                SET nome_arquivo = ?,
                    caminho_relativo = ?,
                    tamanho_bytes = ?,
                    hash_sha256 = ?,
                    gerado_por = ?,
                    ip_origem = ?,
                    atualizado_em = GETDATE(),
                    versao = ?
                WHERE id = ?
                """,
                (nome_arquivo, caminho_relativo, tamanho, hash_sha256,
                 gerado_por, ip, versao, laudo_id),
            )

        conexao.commit()
        cursor.close()
        conexao.close()

    except Exception as e:
        print(f"[Laudo] Erro ao registrar no banco: {e}")
        return {"ok": False, "erro": f"Erro ao registrar no banco: {e}"}

    return {
        "ok": True,
        "laudo_id": laudo_id,
        "chamado_id": chamado_id,
        "nome_arquivo": nome_arquivo,
        "caminho_relativo": caminho_relativo,
        "tamanho_bytes": tamanho,
        "hash_sha256": hash_sha256,
        "versao": versao,
        "eh_novo": eh_novo,
    }


def buscar_laudo_existente(chamado_id: int) -> dict | None:
    """Retorna o laudo do chamado (se existir)."""
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, chamado_id, nome_arquivo, caminho_relativo,
                   tamanho_bytes, hash_sha256, gerado_por, ip_origem,
                   criado_em, atualizado_em, versao
            FROM laudos_chamado
            WHERE chamado_id = ?
            """,
            (chamado_id,),
        )

        row = cursor.fetchone()
        cursor.close()
        conexao.close()

        if not row:
            return None

        return {
            "id": row[0],
            "chamado_id": row[1],
            "nome_arquivo": row[2],
            "caminho_relativo": row[3],
            "tamanho_bytes": row[4],
            "hash_sha256": row[5],
            "gerado_por": row[6],
            "ip_origem": row[7],
            "criado_em": str(row[8]) if row[8] else None,
            "atualizado_em": str(row[9]) if row[9] else None,
            "versao": row[10],
        }

    except Exception as e:
        print(f"[Laudo] Erro ao buscar laudo: {e}")
        return None
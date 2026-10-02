"""
Envio de e-mail corporativo via SMTP (cPanel).

Configuração típica cPanel:
  host: mail.viacaopendotiba.com.br  (ou o host indicado no cPanel)
  porta: 465 (SSL) ou 587 (TLS)
  usuário: e-mail completo
  senha: senha do e-mail

A porta 2096 é do webmail no navegador, NÃO é SMTP.
"""

import os
import smtplib
import ssl
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# Configuração carregada do ambiente; mantenha os valores reais no .env local.
# ============================================================
load_dotenv()
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
REMETENTE = os.getenv("SMTP_SENDER", SMTP_USER)
REMETENTE_NOME = os.getenv("SMTP_SENDER_NAME", "Suporte de TI")


def enviar_email_chamado_resolvido(
    email_destino: str,
    nome_solicitante: str,
    chamado_id: int,
    titulo_chamado: str,
    relatorio: str,
) -> dict:
    """
    Envia e-mail ao solicitante quando o chamado é resolvido.
    Assunto: Chamado Resolvido
    Corpo: título "Chamado fechado" + relatório de resolução.
    """
    if not email_destino or "@" not in email_destino:
        return {"ok": False, "erro": "E-mail do solicitante inválido ou ausente."}

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not REMETENTE:
        return {
            "ok": False,
            "erro": "Configuração SMTP ausente. Verifique as variáveis de ambiente."
        }

    assunto = "Chamado Resolvido"

    texto_plano = (
        f"Chamado fechado\n\n"
        f"Olá, {nome_solicitante}.\n\n"
        f"Seu chamado #{chamado_id} foi resolvido pela equipe de TI.\n\n"
        f"Título: {titulo_chamado}\n\n"
        f"Relatório de resolução:\n"
        f"{relatorio}\n\n"
        f"—\n"
        f"Suporte de TI\n"
        f"Viação Pendotiba\n"
        f"{REMETENTE}"
    )

    html = f"""
    <html>
      <body style="font-family: Arial, Helvetica, sans-serif; color: #1f2937; line-height: 1.5;">
        <div style="max-width: 560px; margin: 0 auto; padding: 24px;">
          <h2 style="color: #1d4ed8; margin-bottom: 8px;">Chamado fechado</h2>
          <p>Olá, <strong>{nome_solicitante}</strong>.</p>
          <p>
            Seu chamado <strong>#{chamado_id}</strong> foi resolvido pela equipe de TI.
          </p>
          <p><strong>Título:</strong> {titulo_chamado}</p>
          <div style="background: #f3f4f6; border-left: 4px solid #1d4ed8; padding: 14px 16px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0 0 6px; font-weight: bold;">Relatório de resolução</p>
            <p style="margin: 0; white-space: pre-wrap;">{relatorio}</p>
          </div>
          <p style="color: #6b7280; font-size: 13px; margin-top: 28px;">
            Suporte de TI · Viação Pendotiba<br>
            {REMETENTE}
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"{REMETENTE_NOME} <{REMETENTE}>"
    msg["To"] = email_destino

    msg.attach(MIMEText(texto_plano, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(REMETENTE, [email_destino], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(REMETENTE, [email_destino], msg.as_string())

        return {"ok": True, "destino": email_destino}

    except Exception as e:
        print("ERRO AO ENVIAR E-MAIL:", e)
        return {"ok": False, "erro": str(e)}


def enviar_email_recuperacao_senha(
    email_destino: str,
    nome: str,
    codigo: str,
) -> dict:
    """
    Envia código de recuperação de senha.
    """
    if not email_destino or "@" not in email_destino:
        return {"ok": False, "erro": "E-mail inválido."}

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not REMETENTE:
        return {"ok": False, "erro": "Senha do SMTP não configurada."}

    assunto = "Recuperação de senha - Suporte TI"

    texto_plano = (
        f"Olá, {nome}.\n\n"
        f"Você solicitou a redefinição de senha no sistema de Suporte de TI.\n\n"
        f"Seu código de verificação é: {codigo}\n\n"
        f"Este código vale por 30 minutos.\n"
        f"Se você não solicitou isso, ignore este e-mail.\n\n"
        f"—\n"
        f"Suporte de TI\n"
        f"Viação Pendotiba\n"
    )

    html = f"""
    <html>
      <body style="font-family: Arial, Helvetica, sans-serif; color: #1f2937; line-height: 1.5;">
        <div style="max-width: 560px; margin: 0 auto; padding: 24px;">
          <h2 style="color: #1d4ed8; margin-bottom: 8px;">Recuperação de senha</h2>
          <p>Olá, <strong>{nome}</strong>.</p>
          <p>Você solicitou a redefinição de senha no sistema de Suporte de TI.</p>
          <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 20px; text-align: center; margin: 24px 0;">
            <p style="margin: 0 0 8px; font-size: 13px; color: #6b7280;">Seu código de verificação</p>
            <p style="margin: 0; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1d4ed8;">{codigo}</p>
          </div>
          <p style="font-size: 13px; color: #6b7280;">
            Este código vale por <strong>30 minutos</strong>.<br>
            Se você não solicitou isso, ignore este e-mail.
          </p>
          <p style="color: #6b7280; font-size: 13px; margin-top: 28px;">
            Suporte de TI · Viação Pendotiba<br>
            {REMETENTE}
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"{REMETENTE_NOME} <{REMETENTE}>"
    msg["To"] = email_destino
    msg.attach(MIMEText(texto_plano, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(REMETENTE, [email_destino], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(REMETENTE, [email_destino], msg.as_string())

        return {"ok": True, "destino": email_destino}

    except Exception as e:
        print("ERRO AO ENVIAR E-MAIL DE RECUPERAÇÃO:", e)
        return {"ok": False, "erro": str(e)}

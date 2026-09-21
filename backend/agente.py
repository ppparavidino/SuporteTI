# backend/agente.py
"""
Agente de IA que consulta o banco de chamados.

Usa o Ollama local + llama3.1:8b com "tool calling" para:
1. Entender a pergunta do usuário
2. Decidir quais ferramentas usar (listar_tabelas, descrever_tabela, executar_sql)
3. Executar as ferramentas
4. Formular uma resposta em português

Tudo roda localmente. Nenhum dado sai da empresa.
"""

import os
import json
import requests
from dotenv import load_dotenv

from backend.agente_tools import (
    DEFINICOES_FERRAMENTAS,
    FUNCOES_DISPONIVEIS,
)

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

MAX_ITERACOES = 5
TIMEOUT_OLLAMA = 180  # segundos — CPU sem GPU é mais lento


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """Você é um assistente de TI da Viação Pendotiba.

Seu trabalho é responder perguntas sobre os chamados de suporte técnico
consultando o banco de dados SQL Server.

REGRAS IMPORTANTES:
1. Responda SEMPRE em português do Brasil, em texto normal.
2. NUNCA responda com JSON cru. Sempre formule uma frase.
3. Quando precisar de dados, USE a ferramenta executar_sql.
4. NUNCA invente números. Se não consultou, não responde.
5. Se a consulta falhar, TENTE NOVAMENTE com SQL corrigido.
6. Depois de obter o resultado, RESPONDA em português. Não mostre SQL.
7. Se a pergunta for ambígua, peça esclarecimento.

SINTAXE SQL SERVER (NÃO USE MySQL!):
- Para limitar linhas, use: SELECT TOP 5 coluna FROM tabela
- NÃO use LIMIT (isso é MySQL e dá erro no SQL Server).
- Para concatenar, use + (não CONCAT).
- Para data atual, use GETDATE().
- Para diferença de datas, use DATEDIFF(day, data1, data2).

ATENÇÃO À SINTAXE:
- Sempre use "GROUP BY" com espaço (nunca "GROUPBY").
- Sempre use "ORDER BY" com espaço (nunca "ORDERBY").
- Sempre use "LEFT JOIN", "INNER JOIN" com espaço.

ESTRUTURA DO BANCO (SuporteTI):

- categorias (id, nome, ativo)
- chamados (id, titulo, descricao, categoria_id, prioridade, status,
           solicitante_id, responsavel_id, criado_em, atualizado_em, resolvido_em)
    prioridade: BAIXA, NORMAL, ALTA, URGENTE
    status: ABERTO, EM_ANDAMENTO, RESOLVIDO
- usuarios (id, nome, login, email, setor_id, perfil, ativo, criado_em)
    perfil: FUNCIONARIO, TI, ADMIN
- setores (id, nome, ativo)
- historico_chamados (id, chamado_id, usuario_id, acao, descricao, criado_em)

EXEMPLO DE FLUXO CORRETO:

Pergunta: "Qual setor abriu mais chamados?"

Passo 1 — Chamar ferramenta:
executar_sql(query="SELECT TOP 1 s.nome, COUNT(c.id) AS qtd FROM chamados c JOIN usuarios u ON c.solicitante_id = u.id JOIN setores s ON u.setor_id = s.id GROUP BY s.nome ORDER BY qtd DESC")

Passo 2 — Receber resultado (ex: {"nome": "Financeiro", "qtd": 23})

Passo 3 — Responder em português:
"O setor Financeiro foi o que mais abriu chamados, com 23 chamados."
"""


# ============================================================
# COMUNICAÇÃO COM O OLLAMA
# ============================================================

def _chamar_ollama(mensagens: list) -> dict:
    """Envia mensagens pro Ollama e retorna a resposta."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": mensagens,
        "tools": DEFINICOES_FERRAMENTAS,
        "stream": False,
        "options": {
            "temperature": 0.2,
        }
    }

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=TIMEOUT_OLLAMA,
        )
        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.Timeout:
        return {"erro": "O modelo demorou demais para responder. Tente uma pergunta mais simples."}
    except requests.exceptions.ConnectionError:
        return {"erro": "Não consegui conectar ao Ollama. Ele está rodando?"}
    except Exception as e:
        return {"erro": f"Erro ao chamar o Ollama: {str(e)}"}


# ============================================================
# EXECUÇÃO DE FERRAMENTAS
# ============================================================

def _executar_ferramenta(nome: str, argumentos: dict) -> str:
    """Executa uma ferramenta solicitada pela IA."""
    if nome not in FUNCOES_DISPONIVEIS:
        return json.dumps({"erro": f"Ferramenta desconhecida: {nome}"})

    funcao = FUNCOES_DISPONIVEIS[nome]

    try:
        resultado = funcao(**argumentos)
        return json.dumps(resultado, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"erro": f"Erro ao executar {nome}: {str(e)}"})


# ============================================================
# FUNÇÃO PRINCIPAL — O AGENTE
# ============================================================

def perguntar(pergunta: str, historico: list = None) -> dict:
    """
    Recebe uma pergunta em linguagem natural e devolve a resposta
    do agente, depois de ele consultar o banco se necessário.

    Aceita um histórico opcional de mensagens anteriores para
    manter o contexto da conversa.
    """
    if not pergunta or not pergunta.strip():
        return {"resposta": "Pode repetir a pergunta?", "iteracoes": 0, "ferramentas_usadas": []}

    # Monta a lista de mensagens para o Ollama
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Adiciona histórico (se houver), limitado às últimas 10 mensagens
    if historico:
        MAX_HISTORICO = 10
        mensagens.extend(historico[-MAX_HISTORICO:])

    # Adiciona a pergunta atual
    mensagens.append({"role": "user", "content": pergunta.strip()})

    ferramentas_usadas = []

    for iteracao in range(MAX_ITERACOES):
        print(f"\n[Agente] Iteração {iteracao + 1}/{MAX_ITERACOES}")

        resposta_ollama = _chamar_ollama(mensagens)

        if "erro" in resposta_ollama:
            return {
                "resposta": resposta_ollama["erro"],
                "iteracoes": iteracao + 1,
                "ferramentas_usadas": ferramentas_usadas,
            }

        mensagem = resposta_ollama.get("message", {})
        tool_calls = mensagem.get("tool_calls", [])

        if not tool_calls:
            conteudo = mensagem.get("content", "").strip()
            print(f"[Agente] Resposta final após {iteracao + 1} iteração(ões).")
            return {
                "resposta": conteudo or "Não consegui formular uma resposta.",
                "iteracoes": iteracao + 1,
                "ferramentas_usadas": ferramentas_usadas,
            }

        mensagens.append(mensagem)

        for tc in tool_calls:
            nome = tc.get("function", {}).get("name")
            args = tc.get("function", {}).get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            print(f"[Agente] Chamando ferramenta: {nome}({args})")
            ferramentas_usadas.append(nome)

            resultado = _executar_ferramenta(nome, args)

            mensagens.append({
                "role": "tool",
                "content": resultado,
            })

    return {
        "resposta": "Não consegui concluir a consulta em tempo hábil. Tente reformular.",
        "iteracoes": MAX_ITERACOES,
        "ferramentas_usadas": ferramentas_usadas,
    }


# ============================================================
# VERIFICAR SE O OLLAMA ESTÁ NO AR
# ============================================================

def ollama_online() -> bool:
    """Verifica se o Ollama está rodando e o modelo existe."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        modelos = [m["name"] for m in resp.json().get("models", [])]
        return any(OLLAMA_MODEL.split(":")[0] in m for m in modelos)
    except Exception:
        return False
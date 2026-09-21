// ==========================================================
// WIDGET DE CHAT COM AGENTE DE IA
// ==========================================================

const CHAT_API_URL = window.location.origin || "http://127.0.0.1:8000";

const SUGESTOES = [
    "Qual setor abriu mais chamados?",
    "Quantos chamados estão abertos?",
    "Tem chamado urgente sem responsável?",
    "Quem resolveu mais chamados?",
    "Qual foi o último chamado aberto?",
];

let processando = false;
let historico = [];


// ==========================================================
// ABRIR/FECHAR
// ==========================================================

function toggleChat() {
    const janela = document.getElementById("chat-janela");
    if (!janela) return;

    janela.classList.toggle("escondido");

    if (!janela.classList.contains("escondido")) {
        setTimeout(() => {
            const input = document.getElementById("chat-input");
            if (input) input.focus();
        }, 100);
    }
}


// ==========================================================
// STATUS DO AGENTE
// ==========================================================

async function verificarStatusAgente() {
    const el = document.getElementById("chat-status");
    if (!el) return;

    try {
        const resp = await fetch(`${CHAT_API_URL}/agente/status`);
        const dados = await resp.json();

        if (dados.ollama_online) {
            el.className = "online";
            el.textContent = "Online · " + (dados.modelo || "llama3.1");
        } else {
            el.className = "offline";
            el.textContent = "Offline · Ollama não está rodando";
        }
    } catch (e) {
        el.className = "offline";
        el.textContent = "Offline · API inacessível";
    }
}


// ==========================================================
// MENSAGENS
// ==========================================================

function adicionarMensagem(texto, tipo) {
    const body = document.getElementById("chat-body");
    const div = document.createElement("div");
    div.className = `chat-msg ${tipo}`;
    div.textContent = texto;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
}

function adicionarSugestoes(sugestoes) {
    if (!sugestoes || sugestoes.length === 0) return;

    const body = document.getElementById("chat-body");
    const div = document.createElement("div");
    div.className = "chat-sugestoes-resposta";

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = "💡 Perguntas relacionadas";
    div.appendChild(label);

    sugestoes.forEach(s => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = s;
        b.onclick = () => {
            document.getElementById("chat-input").value = s;
            enviarPergunta();
        };
        div.appendChild(b);
    });

    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

function mostrarDigitando() {
    const body = document.getElementById("chat-body");
    const div = document.createElement("div");
    div.className = "chat-digitando";
    div.id = "chat-digitando";
    div.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

function removerDigitando() {
    const el = document.getElementById("chat-digitando");
    if (el) el.remove();
}


// ==========================================================
// ENVIAR PERGUNTA
// ==========================================================

async function enviarPergunta() {
    if (processando) return;

    const input = document.getElementById("chat-input");
    const btnEnviar = document.getElementById("chat-enviar");
    const botoesSugestao = document.querySelectorAll(".chat-sugestoes button");

    const pergunta = input.value.trim();
    if (!pergunta) return;

    processando = true;
    input.disabled = true;
    btnEnviar.disabled = true;
    botoesSugestao.forEach(b => b.disabled = true);

    adicionarMensagem(pergunta, "user");
    historico.push({ role: "user", content: pergunta });

    input.value = "";
    mostrarDigitando();

    try {
                // Envia a pergunta + histórico das últimas mensagens (contexto)
        const historicoEnxuto = historico.slice(-10).map(m => ({
            role: m.role,
            content: m.content.length > 500
                ? m.content.slice(0, 500) + "..."
                : m.content
        }));

        const resp = await fetch(`${CHAT_API_URL}/agente`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                pergunta: pergunta,
                historico: historicoEnxuto
            })
        });

        removerDigitando();

        if (!resp.ok) {
            const erro = await resp.json().catch(() => ({}));
            adicionarMensagem("❌ " + (erro.detail || `Erro HTTP ${resp.status}`), "erro");
            return;
        }

                const dados = await resp.json();
        const resposta = dados.resposta || "(resposta vazia)";

        adicionarMensagem(resposta, "bot");
        historico.push({ role: "assistant", content: resposta });

        // Renderiza as sugestões contextuais (se houver)
        if (dados.sugestoes && dados.sugestoes.length > 0) {
            adicionarSugestoes(dados.sugestoes);
        }

    } catch (e) {
        removerDigitando();
        console.error(e);
        adicionarMensagem("❌ Não consegui conectar ao servidor.", "erro");
    } finally {
        processando = false;
        input.disabled = false;
        btnEnviar.disabled = false;
        botoesSugestao.forEach(b => b.disabled = false);
        input.focus();
    }
}


// ==========================================================
// INICIALIZAÇÃO
// ==========================================================

function iniciarChat() {
    // Renderiza sugestões
    const box = document.getElementById("chat-sugestoes");
    if (box && box.children.length === 0) {
        SUGESTOES.forEach(s => {
            const b = document.createElement("button");
            b.type = "button";
            b.textContent = s;
            b.onclick = () => {
                document.getElementById("chat-input").value = s;
                enviarPergunta();
            };
            box.appendChild(b);
        });
    }

    // Checa status
    verificarStatusAgente();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciarChat);
} else {
    iniciarChat();
}

window.toggleChat = toggleChat;
window.enviarPergunta = enviarPergunta;
window.verificarStatusAgente = verificarStatusAgente;
window.iniciarChat = iniciarChat;
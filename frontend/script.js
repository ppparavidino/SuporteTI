// URL base da API (FastAPI rodando na porta 8000)
const API_URL = "http://127.0.0.1:8000";

// ==========================================================
// VERIFICAR USUÁRIO LOGADO
// ==========================================================

function obterUsuarioLogado() {

    const usuario = sessionStorage.getItem("usuario");

    if (!usuario) {
        window.location.href = "login.html";
        return null;
    }

    return JSON.parse(usuario);
}


// ==========================================================
// ABRIR CHAMADO
// ==========================================================

async function abrirChamado() {

    const usuario = obterUsuarioLogado();

    if (!usuario) {
        return;
    }

    const titulo = document.getElementById("titulo").value.trim();
    const descricao = document.getElementById("descricao").value.trim();
    const categoria = document.getElementById("categoria").value;
    const prioridade = document.getElementById("prioridade").value;

    if (!titulo || !descricao) {
        alert("Preencha o título e a descrição do problema.");
        return;
    }

    const dados = {
        titulo: titulo,
        descricao: descricao,
        categoria_id: parseInt(categoria),
        prioridade: prioridade,
        solicitante_id: usuario.id
    };

    try {

        const resposta = await fetch(`${API_URL}/chamados`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(dados)
        });

        const resultado = await resposta.json();

        if (resultado.erro) {
            alert("Erro ao criar chamado: " + resultado.erro);
            return;
        }

        if (resposta.ok) {
            alert("Chamado criado com sucesso!");
            document.getElementById("titulo").value = "";
            document.getElementById("descricao").value = "";
            document.getElementById("categoria").value = "1";
            document.getElementById("prioridade").value = "NORMAL";
        } else {
            alert("Erro ao criar chamado: " + JSON.stringify(resultado));
        }

    } catch (erro) {
        console.error(erro);
        alert("Não foi possível conectar ao servidor.");
    }
}


// ==========================================================
// LIMPAR FORMULÁRIO
// ==========================================================

function limparFormulario() {
    document.getElementById("titulo").value = "";
    document.getElementById("descricao").value = "";
    document.getElementById("categoria").value = "1";
    document.getElementById("prioridade").value = "NORMAL";
}


// ==========================================================
// MOSTRAR USUÁRIO LOGADO NO HEADER
// ==========================================================

function mostrarUsuario() {

    const usuario = obterUsuarioLogado();

    if (!usuario) {
        return;
    }

    // Nome completo
    const nomeEl = document.getElementById("nomeUsuario");
    if (nomeEl) {
        nomeEl.innerText = usuario.nome;
    }

    // Perfil / tipo
    const perfilEl = document.getElementById("perfilUsuario");
    if (perfilEl) {
        perfilEl.innerText = usuario.perfil || "Funcionário";
    }

    // Avatar com inicial do nome
    const avatarEl = document.getElementById("avatarUsuario");
    if (avatarEl && usuario.nome) {
        avatarEl.innerText = usuario.nome.trim().charAt(0).toUpperCase();
    }

    // Saudação antiga (se ainda existir)
    const saudacao = document.getElementById("usuarioLogado");
    if (saudacao) {
        saudacao.innerText = "Olá, " + usuario.nome;
    }
}


// ==========================================================
// SAIR
// ==========================================================

function sair() {
    sessionStorage.removeItem("usuario");
    window.location.href = "login.html";
}


// ==========================================================
// EXECUTAR AO CARREGAR A PÁGINA
// ==========================================================

document.addEventListener("DOMContentLoaded", function () {
    mostrarUsuario();
});

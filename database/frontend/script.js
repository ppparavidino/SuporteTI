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

    const usuarioSalvo = localStorage.getItem("usuario");

    if (!usuarioSalvo) {

        alert("Você precisa fazer login para abrir um chamado.");

        window.location.href = "login.html";

        return;
    }

    const usuario = JSON.parse(usuarioSalvo);

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

        const resposta = await fetch(
            `${API_URL}/chamados`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(dados)
            }
        );


        const resultado = await resposta.json();


        if (resposta.ok) {

            alert("Chamado criado com sucesso!");

            document.getElementById("titulo").value = "";

            document.getElementById("descricao").value = "";

        } else {

            alert(
                "Erro ao criar chamado: " +
                JSON.stringify(resultado)
            );

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
// MOSTRAR USUÁRIO LOGADO
// ==========================================================

function mostrarUsuario() {

    const usuario = obterUsuarioLogado();

    if (!usuario) {
        return;
    }

    const elemento = document.getElementById("usuarioLogado");

    if (elemento) {

        elemento.innerText =
            "Olá, " + usuario.nome;

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
// URL base da API (FastAPI rodando na porta 8000)
const API_URL = "http://127.0.0.1:8000";

async function carregarSetores() {
    const select = document.getElementById("setor");
    const mensagem = document.getElementById("mensagem");

    try {
        const resposta = await fetch(`${API_URL}/setores`);
        const setores = await resposta.json();

        if (!Array.isArray(setores) || setores.length === 0) {
            select.innerHTML = '<option value="">Nenhum setor disponível</option>';
            return;
        }

        select.innerHTML = '<option value="">Selecione o setor</option>';

        setores.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.textContent = s.nome;
            select.appendChild(opt);
        });

    } catch (erro) {
        console.error(erro);
        select.innerHTML = '<option value="">Erro ao carregar setores</option>';
        if (mensagem) {
            mensagem.innerText = "Não foi possível carregar os setores. Verifique se a API está rodando.";
        }
    }
}

async function cadastrar() {

    const nome = document.getElementById("nome").value.trim();
    const login = document.getElementById("login").value.trim();
    const email = document.getElementById("email").value.trim();
    const senha = document.getElementById("senha").value;
    const setor = document.getElementById("setor").value;

    const mensagem = document.getElementById("mensagem");

    if (!nome || !login || !email || !senha || !setor) {
        mensagem.innerText = "Preencha todos os campos.";
        return;
    }

    const emailLower = email.toLowerCase();
    if (!emailLower.endsWith("@viacaopendotiba.com.br")) {
        mensagem.innerText =
            "Use o e-mail corporativo (@viacaopendotiba.com.br).";
        return;
    }

    try {

        const resposta = await fetch(`${API_URL}/cadastro`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                nome: nome,
                login: login,
                email: emailLower,
                senha: senha,
                setor_id: Number(setor)
            })
        });

        const dados = await resposta.json();

        if (dados.erro) {
            mensagem.innerText = dados.erro;
            return;
        }

        alert("Cadastro realizado com sucesso!");
        window.location.href = "login.html";

    } catch (erro) {

        console.error(erro);

        mensagem.innerText =
            "Não foi possível conectar ao servidor. Verifique se a API está rodando na porta 8000.";
    }
}

document.addEventListener("DOMContentLoaded", carregarSetores);

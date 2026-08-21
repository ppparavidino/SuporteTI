// URL base da API (FastAPI rodando na porta 8000)
const API_URL = "http://127.0.0.1:8000";

async function fazerLogin() {

    const login = document.getElementById("login").value.trim();
    const senha = document.getElementById("senha").value;

    const mensagem = document.getElementById("mensagem");

    if (!login || !senha) {
        mensagem.innerText = "Preencha login e senha.";
        return;
    }

    try {

        const resposta = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                login: login,
                senha: senha
            })
        });

        const dados = await resposta.json();

        if (dados.erro) {
            mensagem.innerText = dados.erro;
            return;
        }

        sessionStorage.setItem(
            "usuario",
            JSON.stringify(dados.usuario)
        );

        window.location.href = "index.html";

    } catch (erro) {

        console.error("ERRO NO LOGIN:", erro);

        mensagem.innerText =
            "Não foi possível conectar ao servidor. Verifique se a API está rodando na porta 8000.";
    }
}

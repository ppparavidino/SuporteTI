// URL base da API (FastAPI rodando na porta 8000)
const API_URL = "http://127.0.0.1:8000";

async function cadastrar() {

    const nome = document.getElementById("nome").value.trim();
    const login = document.getElementById("login").value.trim();
    const email = document.getElementById("email").value.trim();
    const senha = document.getElementById("senha").value;
    const setor = document.getElementById("setor").value;

    const mensagem = document.getElementById("mensagem");

    if (!nome || !login || !email || !senha) {
        mensagem.innerText = "Preencha todos os campos.";
        return;
    }

    // Validação básica no frontend
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

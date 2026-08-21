// URL base da API (FastAPI rodando na porta 8000)
const API_URL = "http://127.0.0.1:8000";

let chamadoSelecionado = null;


/* =====================================================
   CARREGAR CHAMADOS
===================================================== */

async function carregarChamados() {

    try {

        const resposta = await fetch(
            `${API_URL}/chamados`
        );


        if (!resposta.ok) {

            throw new Error(
                "Erro ao buscar chamados"
            );

        }


        const chamados =
            await resposta.json();


        const abertos =
            document.getElementById("abertos");

        const andamento =
            document.getElementById("andamento");

        const resolvidos =
            document.getElementById("resolvidos");


        abertos.innerHTML = "";

        andamento.innerHTML = "";

        resolvidos.innerHTML = "";


        let contadorAbertos = 0;

        let contadorAndamento = 0;

        let contadorResolvidos = 0;


        chamados.forEach(chamado => {

            const card =
                criarCard(chamado);


            if (
                chamado.status === "ABERTO"
            ) {

                abertos.appendChild(card);

                contadorAbertos++;

            }


            else if (
                chamado.status === "EM_ANDAMENTO"
            ) {

                andamento.appendChild(card);

                contadorAndamento++;

            }


            else if (
                chamado.status === "RESOLVIDO"
            ) {

                resolvidos.appendChild(card);

                contadorResolvidos++;

            }

        });


        document.getElementById(
            "contador-abertos"
        ).textContent =
            contadorAbertos;


        document.getElementById(
            "contador-andamento"
        ).textContent =
            contadorAndamento;


        document.getElementById(
            "contador-resolvidos"
        ).textContent =
            contadorResolvidos;


    }

    catch (erro) {

        console.error(erro);

        alert(
            "Não foi possível carregar os chamados."
        );

    }

}


/* =====================================================
   CRIAR CARD
===================================================== */

function criarCard(chamado) {

    const card =
        document.createElement("div");


    card.className =
        "chamado";


    const prioridadeClass =
        chamado.prioridade === "URGENTE"
            ? "urgente"
            : "normal";


    card.innerHTML = `

        <h3>
            #${chamado.id}
            -
            ${chamado.titulo}
        </h3>

        <p>
            👤 ${chamado.solicitante}
        </p>

        <p>
            🏢 ${chamado.setor}
        </p>

        <p>
            🖥️ ${chamado.categoria}
        </p>

        <p>
            👨‍💻 ${
                chamado.responsavel
                || "Não atribuído"
            }
        </p>

        <span
            class="prioridade ${prioridadeClass}"
        >
            ${chamado.prioridade}
        </span>

    `;


    /*
        Quando clicar no card,
        abre os detalhes
    */

    card.addEventListener(
        "click",
        () => {

            abrirDetalhes(chamado.id);

        }
    );


    return card;
}


/* =====================================================
   ABRIR DETALHES
===================================================== */

async function abrirDetalhes(id) {

    try {

        const resposta =
            await fetch(
                `${API_URL}/chamados/${id}`
            );


        if (!resposta.ok) {

            throw new Error(
                "Chamado não encontrado"
            );

        }


        const chamado =
            await resposta.json();


        chamadoSelecionado =
            chamado;


        document.getElementById(
            "modal-titulo"
        ).textContent =
            `Chamado #${chamado.id}`;


        const fmt = (d) => {
            if (!d) return "—";
            try {
                return new Date(d).toLocaleString("pt-BR");
            } catch (e) {
                return d;
            }
        };

        const solicitanteTxt = chamado.solicitante_login
            ? `${chamado.solicitante} (login: ${chamado.solicitante_login})`
            : (chamado.solicitante || "—");

        const responsavelTxt = chamado.responsavel
            ? (chamado.responsavel_login
                ? `${chamado.responsavel} (login: ${chamado.responsavel_login})`
                : chamado.responsavel)
            : "Não atribuído";

        let blocoResolucao = "";
        if (chamado.status === "RESOLVIDO") {
            blocoResolucao = `
                <div class="detalhe">
                    <strong>Resolvido em</strong>
                    ${fmt(chamado.resolvido_em)}
                </div>
                <div class="detalhe">
                    <strong>Resolvido por</strong>
                    ${
                        chamado.resolvido_por
                            ? `${chamado.resolvido_por}${chamado.resolvido_por_login ? " (login: " + chamado.resolvido_por_login + ")" : ""}`
                            : (chamado.responsavel || "—")
                    }
                </div>
                <div class="detalhe">
                    <strong>Como foi resolvido (relatório)</strong>
                    ${chamado.relatorio_resolucao || "Sem relatório registrado"}
                </div>
            `;
        }

        document.getElementById("modal-detalhes").innerHTML = `
            <div class="detalhe">
                <strong>Título</strong>
                ${chamado.titulo || "—"}
            </div>
            <div class="detalhe">
                <strong>Descrição do problema</strong>
                ${chamado.descricao || "Sem descrição"}
            </div>
            <div class="detalhe">
                <strong>Solicitante</strong>
                ${solicitanteTxt}
            </div>
            <div class="detalhe">
                <strong>Setor</strong>
                ${chamado.setor || "—"}
            </div>
            <div class="detalhe">
                <strong>Categoria</strong>
                ${chamado.categoria || "—"}
            </div>
            <div class="detalhe">
                <strong>Prioridade</strong>
                ${chamado.prioridade || "—"}
            </div>
            <div class="detalhe">
                <strong>Status</strong>
                ${chamado.status || "—"}
            </div>
            <div class="detalhe">
                <strong>Responsável (TI)</strong>
                ${responsavelTxt}
            </div>
            <div class="detalhe">
                <strong>Aberto em</strong>
                ${fmt(chamado.criado_em)}
            </div>
            <div class="detalhe">
                <strong>Última atualização</strong>
                ${fmt(chamado.atualizado_em)}
            </div>
            ${blocoResolucao}
        `;



        document.getElementById("status").value = chamado.status;

        // Limpa relatório e ajusta visibilidade
        const relatorioEl = document.getElementById("relatorio");
        if (relatorioEl) relatorioEl.value = "";
        toggleRelatorio();

        await carregarResponsaveis();
        await carregarHistorico(chamado.id);

        document.getElementById("modal").classList.remove("escondido");


    }

    catch (erro) {

        console.error(erro);

        alert(
            "Erro ao carregar detalhes."
        );

    }

}


/* =====================================================
   CARREGAR RESPONSÁVEIS
===================================================== */

async function carregarResponsaveis() {

    const select =
        document.getElementById(
            "responsavel"
        );


    select.innerHTML = `

        <option value="">
            Não atribuído
        </option>

    `;


    try {

        const resposta =
            await fetch(
                `${API_URL}/usuarios/ti`
            );


        const usuarios =
            await resposta.json();


        usuarios.forEach(usuario => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                usuario.id;


            option.textContent =
                usuario.nome;


            select.appendChild(
                option
            );


        });


        /*
            Seleciona o responsável atual
        */

        if (
            chamadoSelecionado &&
            chamadoSelecionado.responsavel
        ) {

            const option =
                [...select.options]
                    .find(
                        opcao =>
                            opcao.textContent ===
                            chamadoSelecionado.responsavel
                    );


            if (option) {

                select.value =
                    option.value;

            }

        }

    }

    catch (erro) {

        console.error(
            "Erro ao carregar responsáveis:",
            erro
        );

    }

}


/* =====================================================
   MOSTRAR / ESCONDER RELATÓRIO
===================================================== */

function toggleRelatorio() {
    const status = document.getElementById("status").value;
    const bloco = document.getElementById("bloco-relatorio");
    if (!bloco) return;

    if (status === "RESOLVIDO") {
        bloco.style.display = "block";
    } else {
        bloco.style.display = "none";
    }
}


/* =====================================================
   CARREGAR HISTÓRICO
===================================================== */

async function carregarHistorico(chamadoId) {
    const lista = document.getElementById("lista-historico");
    if (!lista) return;

    lista.innerHTML = "Carregando...";

    try {
        const resposta = await fetch(
            `${API_URL}/chamados/${chamadoId}/historico`
        );
        const itens = await resposta.json();

        if (!Array.isArray(itens) || itens.length === 0) {
            lista.innerHTML = "<p style='color:#9ca3af'>Nenhum registro no histórico.</p>";
            return;
        }

        lista.innerHTML = itens.map(item => {
            const data = item.criado_em
                ? new Date(item.criado_em).toLocaleString("pt-BR")
                : "";
            const quem = item.usuario_login
                ? `${item.usuario_nome || item.usuario || "—"} (login: ${item.usuario_login})`
                : (item.usuario_nome || item.usuario || "—");
            return `
                <div style="padding:10px 0; border-bottom:1px solid #f3f4f6;">
                    <div style="display:flex; justify-content:space-between; gap:8px;">
                        <strong style="color:#1d4ed8">${item.acao}</strong>
                        <span style="color:#9ca3af; font-size:12px;">${data}</span>
                    </div>
                    <div style="margin-top:4px; white-space:pre-wrap;">${item.descricao || ""}</div>
                    <div style="margin-top:4px; color:#6b7280; font-size:12px;">
                        por ${quem}
                    </div>
                </div>
            `;
        }).join("");


    } catch (erro) {
        console.error(erro);
        lista.innerHTML = "<p style='color:#dc2626'>Erro ao carregar histórico.</p>";
    }
}


/* =====================================================
   SALVAR ALTERAÇÕES
===================================================== */

async function salvarAlteracoes() {

    if (!chamadoSelecionado) {
        return;
    }

    const responsavel = document.getElementById("responsavel").value;
    const status = document.getElementById("status").value;
    const relatorioEl = document.getElementById("relatorio");
    const relatorio = relatorioEl ? relatorioEl.value.trim() : "";

    if (status === "RESOLVIDO" && !relatorio) {
        alert("Preencha o relatório de resolução antes de marcar como resolvido.");
        return;
    }

    // Quem está logado no painel (TI)
    let usuarioId = null;
    try {
        const u = JSON.parse(sessionStorage.getItem("usuario") || "null");
        if (u && u.id) usuarioId = u.id;
    } catch (e) {}

    const body = {
        status: status,
        usuario_id: usuarioId,
        relatorio: relatorio || null
    };

    if (responsavel !== "") {
        body.responsavel_id = parseInt(responsavel);
    }

    try {
        const resposta = await fetch(
            `${API_URL}/chamados/${chamadoSelecionado.id}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(body)
            }
        );

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.detail || dados.erro || "Erro ao atualizar chamado"
            );
        }

        alert("Chamado atualizado com sucesso!");
        fecharModal();
        await carregarChamados();

    } catch (erro) {
        console.error(erro);
        alert("Erro ao salvar alterações: " + erro.message);
    }
}



/* =====================================================
   FECHAR MODAL
===================================================== */

function fecharModal() {

    document.getElementById(
        "modal"
    ).classList.add(
        "escondido"
    );


    chamadoSelecionado =
        null;

}


/* =====================================================
   INICIALIZAÇÃO
===================================================== */

carregarChamados();
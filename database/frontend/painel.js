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


        document.getElementById(
            "modal-detalhes"
        ).innerHTML = `

            <div class="detalhe">

                <strong>Título:</strong>

                ${chamado.titulo}

            </div>


            <div class="detalhe">

                <strong>Descrição:</strong>

                ${
                    chamado.descricao
                    || "Sem descrição"
                }

            </div>


            <div class="detalhe">

                <strong>Solicitante:</strong>

                ${chamado.solicitante}

            </div>


            <div class="detalhe">

                <strong>Setor:</strong>

                ${chamado.setor}

            </div>


            <div class="detalhe">

                <strong>Categoria:</strong>

                ${chamado.categoria}

            </div>


            <div class="detalhe">

                <strong>Prioridade:</strong>

                ${chamado.prioridade}

            </div>


            <div class="detalhe">

                <strong>Responsável atual:</strong>

                ${
                    chamado.responsavel
                    || "Não atribuído"
                }

            </div>

        `;


        document.getElementById(
            "status"
        ).value =
            chamado.status;


        await carregarResponsaveis();


        document.getElementById(
            "modal"
        ).classList.remove(
            "escondido"
        );

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
   SALVAR ALTERAÇÕES
===================================================== */

async function salvarAlteracoes() {

    if (!chamadoSelecionado) {

        return;

    }


    const responsavel =
        document.getElementById(
            "responsavel"
        ).value;


    const status =
        document.getElementById(
            "status"
        ).value;


    const params =
        new URLSearchParams();


    if (responsavel !== "") {

        params.append(
            "responsavel_id",
            responsavel
        );

    }


    params.append(
        "status",
        status
    );


    try {

        const resposta =
            await fetch(
                `${API_URL}/chamados/${chamadoSelecionado.id}?${params.toString()}`,
                {
                    method: "PUT"
                }
            );


        if (!resposta.ok) {

            const erro =
                await resposta.json();


            throw new Error(
                erro.detail ||
                "Erro ao atualizar chamado"
            );

        }


        alert(
            "Chamado atualizado com sucesso!"
        );


        fecharModal();


        await carregarChamados();

    }

    catch (erro) {

        console.error(erro);

        alert(
            "Erro ao salvar alterações: " +
            erro.message
        );

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
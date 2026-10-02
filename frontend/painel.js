// Permite configurar a API em implantação; por padrão usa a porta 8000 do mesmo host.
const API_URL = window.SUPORTE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

let chamadoSelecionado = null;

// =========================================================
// ANEXOS — estado global
// =========================================================
let anexosSelecionados = [];   // { file, id_temp } — arquivos escolhidos ainda não enviados
let anexosExistentes = [];     // anexos já salvos no servidor (vindos do banco)


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
    const blocoAnexos = document.getElementById("bloco-anexos");
    const blocoReabertura = document.getElementById("bloco-controle-reabertura");
    const btnReabrir = document.getElementById("btn-reabrir");

    const resolvido = status === "RESOLVIDO";

    if (bloco) {
        bloco.style.display = resolvido ? "block" : "none";
    }
    if (blocoAnexos) {
        blocoAnexos.style.display = resolvido ? "block" : "none";
    }
    if (blocoReabertura) {
        blocoReabertura.style.display = resolvido ? "block" : "none";
    }
    if (btnReabrir) {
        btnReabrir.style.display = resolvido ? "inline-flex" : "none";
    }

    // Se virou RESOLVIDO, carrega anexos existentes
    if (resolvido && chamadoSelecionado) {
        anexosSelecionados = [];
        carregarAnexosExistentes(chamadoSelecionado.id);
    } else if (blocoAnexos) {
        blocoAnexos.style.display = "none";
    }
}

function reabrirChamado() {
    const status = document.getElementById("status");
    if (status) {
        status.value = "ABERTO";
        toggleRelatorio();
    }
}

async function carregarAnexosExistentes(chamadoId) {
    try {
        const resp = await fetch(`${API_URL}/chamados/${chamadoId}/anexos`);
        if (!resp.ok) return;

        const dados = await resp.json();
        anexosExistentes = Array.isArray(dados.anexos) ? dados.anexos : [];

        renderizarListaAnexos();
    } catch (e) {
        console.error("Erro ao carregar anexos:", e);
    }
}

function formatarTamanhoArquivo(bytes) {
    if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) {
        return "—";
    }

    const unidades = ["B", "KB", "MB", "GB"];
    let tamanho = Number(bytes);
    let indice = 0;

    while (tamanho >= 1024 && indice < unidades.length - 1) {
        tamanho /= 1024;
        indice++;
    }

    const valor = tamanho >= 10 || indice === 0 ? tamanho.toFixed(0) : tamanho.toFixed(1);
    return `${valor} ${unidades[indice]}`;
}

function getArquivoPreview(item) {
    if (item.tipo === "local") {
        const file = item.file;
        if (file && file.type && file.type.startsWith("image/")) {
            const url = URL.createObjectURL(file);
            return `<img src="${url}" alt="${file.name}" />`;
        }
        if (file && file.type && file.type.startsWith("video/")) {
            return "🎬";
        }
        if (file && (file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf")) {
            return "📄";
        }
        return "📎";
    }

    const mime = (item.tipo_mime || "").toLowerCase();
    const nome = (item.nome_original || item.nome_arquivo || "arquivo").toLowerCase();

    if (mime.startsWith("image/")) {
        return `<img src="${API_URL}/anexos/${item.id}/download" alt="${item.nome_original || item.nome_arquivo || "arquivo"}" />`;
    }
    if (mime.startsWith("video/")) {
        return "🎬";
    }
    if (mime.includes("pdf") || nome.endsWith(".pdf")) {
        return "📄";
    }
    return "📎";
}

function getStatusTexto(item) {
    if (item.tipo === "local") {
        return item.status || "pendente";
    }
    return "enviado";
}

async function removerAnexoExistente(anexoId) {
    try {
        const usuario = JSON.parse(sessionStorage.getItem("usuario") || "null");
        const usuarioId = usuario && usuario.id ? Number(usuario.id) : null;

        if (!usuarioId) {
            alert("Sessão expirada. Faça login novamente.");
            return;
        }

        const resposta = await fetch(`${API_URL}/anexos/${anexoId}`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                usuario_id: usuarioId,
                motivo: "Remoção via painel"
            })
        });

        const dados = await resposta.json();
        if (!resposta.ok) {
            throw new Error(dados.detail || dados.erro || "Erro ao remover anexo.");
        }

        anexosExistentes = anexosExistentes.filter(item => item.id !== anexoId);
        renderizarListaAnexos();
    } catch (erro) {
        console.error("Erro ao remover anexo existente:", erro);
        alert("Erro ao remover anexo: " + erro.message);
    }
}

function renderizarListaAnexos() {
    const lista = document.getElementById("lista-anexos");
    const areaDrop = document.getElementById("area-drop");
    const inputAnexos = document.getElementById("input-anexos");

    if (!lista) return;

    const todos = [
        ...anexosSelecionados.map(item => ({ ...item, tipo: "local" })),
        ...anexosExistentes.map(item => ({ ...item, tipo: "existente" }))
    ];

    if (!todos.length) {
        lista.innerHTML = "<div style='color:#6b7280; font-size:12px;'>Nenhum anexo adicionado.</div>";
    } else {
        lista.innerHTML = todos.map(item => {
            const isLocal = item.tipo === "local";
            const nome = isLocal
                ? (item.file?.name || "Arquivo")
                : (item.nome_original || item.nome_arquivo || "Arquivo");
            const tamanho = isLocal
                ? formatarTamanhoArquivo(item.file?.size)
                : formatarTamanhoArquivo(item.tamanho_bytes);
            const status = getStatusTexto(item);
            const previewHtml = getArquivoPreview(item);

            return `
                <div class="anexo-item">
                    <div class="anexo-preview">${previewHtml}</div>
                    <div class="anexo-info">
                        <span class="anexo-nome" title="${nome}">${nome}</span>
                        <div class="anexo-meta">
                            <span>${tamanho}</span>
                            <span class="anexo-status ${status}">${status}</span>
                        </div>
                    </div>
                    <button type="button" class="anexo-remover" title="Remover anexo" aria-label="Remover anexo">
                        ×
                    </button>
                </div>
            `;
        }).join("");
    }

    const total = todos.length;
    const limite = total >= 5;

    if (areaDrop) {
        areaDrop.classList.toggle("limite-atingido", limite);
        areaDrop.classList.toggle("desabilitada", limite);
    }

    if (inputAnexos) {
        inputAnexos.disabled = limite;
    }

    const botoesRemover = lista.querySelectorAll(".anexo-remover");
    botoesRemover.forEach((botao, index) => {
        botao.addEventListener("click", async () => {
            const item = todos[index];
            if (!item) return;

            if (item.tipo === "existente") {
                await removerAnexoExistente(item.id);
                return;
            }

            anexosSelecionados = anexosSelecionados.filter(anexo => anexo.id_temp !== item.id_temp);
            renderizarListaAnexos();
        });
    });
}

function adicionarArquivosSelecionados(arquivos) {
    const listaArquivos = Array.from(arquivos || []);
    const restante = Math.max(0, 5 - (anexosSelecionados.length + anexosExistentes.length));

    if (restante === 0) {
        const areaDrop = document.getElementById("area-drop");
        if (areaDrop) areaDrop.classList.add("limite-atingido");
        return;
    }

    const paraAdicionar = listaArquivos.slice(0, restante);

    paraAdicionar.forEach(file => {
        anexosSelecionados.push({
            file,
            id_temp: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            status: "pendente"
        });
    });

    renderizarListaAnexos();
}

function inicializarAnexos() {
    const areaDrop = document.getElementById("area-drop");
    const inputAnexos = document.getElementById("input-anexos");

    if (!areaDrop || !inputAnexos) return;

    areaDrop.addEventListener("click", () => {
        const limite = anexosSelecionados.length + anexosExistentes.length >= 5;
        if (!limite) {
            inputAnexos.click();
        }
    });

    inputAnexos.addEventListener("change", (evento) => {
        adicionarArquivosSelecionados(evento.target.files);
        inputAnexos.value = "";
    });

    areaDrop.addEventListener("dragover", (evento) => {
        evento.preventDefault();
        const limite = anexosSelecionados.length + anexosExistentes.length >= 5;
        if (!limite) {
            areaDrop.classList.add("arrastando");
        }
    });

    areaDrop.addEventListener("dragleave", () => {
        areaDrop.classList.remove("arrastando");
    });

    areaDrop.addEventListener("drop", (evento) => {
        evento.preventDefault();
        areaDrop.classList.remove("arrastando");
        adicionarArquivosSelecionados(evento.dataTransfer.files);
    });
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

async function enviarArquivosDoChamado(chamadoId) {
    const usuario = JSON.parse(sessionStorage.getItem("usuario") || "null");
    const usuarioId = usuario && usuario.id ? usuario.id : null;

    if (!usuarioId || !anexosSelecionados.length) {
        return;
    }

    for (const anexo of anexosSelecionados) {
        const formData = new FormData();
        formData.append("arquivo", anexo.file);
        formData.append("usuario_id", String(usuarioId));
        formData.append("ip_origem", window.location.hostname || "painel");

        const resposta = await fetch(`${API_URL}/chamados/${chamadoId}/anexos`, {
            method: "POST",
            body: formData,
        });

        if (!resposta.ok) {
            const dados = await resposta.json().catch(() => ({}));
            throw new Error(dados.detail || dados.erro || "Erro ao enviar anexo.");
        }
    }
}

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

        if (anexosSelecionados.length > 0) {
            await enviarArquivosDoChamado(chamadoSelecionado.id);
        }

        if (status === "RESOLVIDO") {
            chamadoSelecionado = null;
            window.location.assign("historico.html");
            return;
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

inicializarAnexos();
carregarChamados();



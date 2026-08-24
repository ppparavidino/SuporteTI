const API_URL = "http://127.0.0.1:8000";

let todosChamados = [];

const MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
];

function verificarAcesso() {
    const raw = sessionStorage.getItem("usuario");
    if (!raw) {
        window.location.href = "login.html";
        return null;
    }
    const u = JSON.parse(raw);
    const perfil = (u.perfil || "").toUpperCase();
    if (perfil !== "TI" && perfil !== "ADMIN" && perfil !== "ADMINISTRADOR") {
        alert("Acesso restrito à equipe de TI.");
        window.location.href = "index.html";
        return null;
    }
    return u;
}

function sair() {
    sessionStorage.removeItem("usuario");
    window.location.href = "login.html";
}

function fmtData(d) {
    if (!d) return "—";
    try {
        return new Date(d).toLocaleString("pt-BR");
    } catch (e) {
        return d;
    }
}

function chaveMes(dataStr) {
    if (!dataStr) return { key: "0000-00", label: "Sem data" };
    const d = new Date(dataStr);
    if (isNaN(d.getTime())) return { key: "0000-00", label: "Sem data" };
    const y = d.getFullYear();
    const m = d.getMonth();
    return {
        key: `${y}-${String(m + 1).padStart(2, "0")}`,
        label: `${MESES[m]} / ${y}`
    };
}

async function carregar() {
    verificarAcesso();

    const pastasEl = document.getElementById("pastas");
    const resumo = document.getElementById("resumo");

    try {
        const resp = await fetch(`${API_URL}/chamados/arquivo`);
        const dados = await resp.json();

        if (!Array.isArray(dados)) {
            resumo.textContent = dados.erro || "Erro ao carregar histórico.";
            return;
        }

        todosChamados = dados;
        resumo.textContent = `${dados.length} chamado(s) no arquivo.`;
        aplicarFiltros();

    } catch (e) {
        console.error(e);
        resumo.textContent = "Não foi possível conectar à API.";
        pastasEl.innerHTML = "";
    }
}

function aplicarFiltros() {
    const busca = (document.getElementById("busca").value || "").toLowerCase().trim();
    const status = document.getElementById("filtro-status").value;

    let lista = todosChamados.slice();

    if (status) {
        lista = lista.filter(c => c.status === status);
    }

    if (busca) {
        lista = lista.filter(c => {
            const txt = [
                c.titulo, c.descricao, c.solicitante, c.solicitante_login,
                c.responsavel, c.responsavel_login, c.setor, c.categoria,
                c.relatorio_resolucao, String(c.id)
            ].join(" ").toLowerCase();
            return txt.includes(busca);
        });
    }

    renderPastas(lista);
    document.getElementById("resumo").textContent =
        `${lista.length} chamado(s) exibido(s)` +
        (lista.length !== todosChamados.length ? ` de ${todosChamados.length}` : "") +
        ".";
}

function renderPastas(lista) {
    const pastasEl = document.getElementById("pastas");

    if (!lista.length) {
        pastasEl.innerHTML = "<p style='color:#64748b'>Nenhum chamado encontrado.</p>";
        return;
    }

    // Agrupa por mês da data de criação (ou resolução se existir)
    const grupos = {};

    lista.forEach(c => {
        const base = c.resolvido_em || c.criado_em;
        const { key, label } = chaveMes(base);
        if (!grupos[key]) grupos[key] = { label, itens: [] };
        grupos[key].itens.push(c);
    });

    const keys = Object.keys(grupos).sort().reverse();

    pastasEl.innerHTML = keys.map((key, idx) => {
        const g = grupos[key];
        const aberta = idx === 0 ? " aberta" : "";
        const itensHtml = g.itens.map(c => {
            const badgeClass =
                c.status === "RESOLVIDO" ? "badge-resolvido" :
                c.status === "EM_ANDAMENTO" ? "badge-andamento" : "badge-aberto";
            return `
                <div class="item" onclick="abrirDetalhe(${c.id})">
                    <div class="item-titulo">
                        #${c.id} — ${c.titulo || "Sem título"}
                        <span class="badge ${badgeClass}">${c.status}</span>
                    </div>
                    <div class="item-meta">
                        <span>Solicitante: ${c.solicitante || "—"} (${c.solicitante_login || "—"})</span>
                        <span>Setor: ${c.setor || "—"}</span>
                        <span>Aberto: ${fmtData(c.criado_em)}</span>
                        ${c.resolvido_em ? `<span>Resolvido: ${fmtData(c.resolvido_em)}</span>` : ""}
                    </div>
                </div>
            `;
        }).join("");

        return `
            <div class="pasta${aberta}" data-key="${key}">
                <div class="pasta-cabecalho" onclick="togglePasta(this)">
                    <h2>📁 ${g.label}</h2>
                    <span>${g.itens.length}</span>
                </div>
                <div class="pasta-lista">${itensHtml}</div>
            </div>
        `;
    }).join("");
}

function togglePasta(el) {
    el.parentElement.classList.toggle("aberta");
}

function abrirDetalhe(id) {
    const c = todosChamados.find(x => x.id === id);
    if (!c) return;

    document.getElementById("modal-titulo").textContent = `Chamado #${c.id}`;

    const resolvidoPor = c.resolvido_por
        ? `${c.resolvido_por}${c.resolvido_por_login ? " (login: " + c.resolvido_por_login + ")" : ""}`
        : (c.responsavel
            ? `${c.responsavel}${c.responsavel_login ? " (login: " + c.responsavel_login + ")" : ""}`
            : "—");

    document.getElementById("modal-corpo").innerHTML = `
        <div class="detalhe"><strong>Título</strong>${c.titulo || "—"}</div>
        <div class="detalhe"><strong>Descrição do problema</strong>${c.descricao || "—"}</div>
        <div class="detalhe"><strong>Status</strong>${c.status || "—"}</div>
        <div class="detalhe"><strong>Prioridade</strong>${c.prioridade || "—"}</div>
        <div class="detalhe"><strong>Categoria</strong>${c.categoria || "—"}</div>
        <div class="detalhe"><strong>Setor</strong>${c.setor || "—"}</div>
        <div class="detalhe"><strong>Solicitante</strong>${c.solicitante || "—"} (login: ${c.solicitante_login || "—"})</div>
        <div class="detalhe"><strong>Responsável TI</strong>${c.responsavel || "Não atribuído"}${c.responsavel_login ? " (login: " + c.responsavel_login + ")" : ""}</div>
        <div class="detalhe"><strong>Aberto em</strong>${fmtData(c.criado_em)}</div>
        <div class="detalhe"><strong>Resolvido em</strong>${fmtData(c.resolvido_em)}</div>
        <div class="detalhe"><strong>Resolvido por</strong>${resolvidoPor}</div>
        <div class="detalhe"><strong>Como foi resolvido</strong>${c.relatorio_resolucao || "Sem relatório registrado"}</div>
    `;

    document.getElementById("modal").classList.remove("escondido");
}

function fecharModal() {
    document.getElementById("modal").classList.add("escondido");
}

document.addEventListener("DOMContentLoaded", carregar);

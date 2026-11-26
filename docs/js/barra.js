import { perfis } from "./permissoes.js";
import { botao, el, iconeSvg, link } from "./ui.js";

const icones = {
  marca: "M4 6h16v10H9l-5 4V6zm4 5h8",
  fila: "M4 5h16v14H4zM8 9h8M8 14h8",
  atendimento: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  chamados: "M6 4h12v16H6zM9 9h6M9 13h6",
  usuarios: "M16 20H4v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2zm-2-12a4 4 0 1 1-8 0 4 4 0 0 1 8 0zm3 6h1a3 3 0 0 1 3 3v3h-2",
  categorias: "M4 5h7l9 9-6 6-9-9V5zm4 3h.01",
  conta: "M4 20v-2a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5v2M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z",
  sair: "M10 4H4v16h6m-1-8h11m-4-4 4 4-4 4",
  recolher: "M4 5h16v14H4zM9 5v14m7-10-3 3 3 3",
  expandir: "M4 5h16v14H4zM9 5v14m4-10 3 3-3 3",
  menu: "M4 6h16M4 12h16M4 18h16",
  fechar: "m6 6 12 12M18 6 6 18",
};

const icone = (nome) => iconeSvg(icones[nome]);
let recolhida = false;

export function marca() {
  return el("span", { class: "marca" }, icone("marca"), el("span", {}, "HelpDesk"));
}

function iniciais(nome) {
  const partes = nome.trim().split(/\s+/);
  const nomes = partes.length > 1 ? [partes[0], partes.at(-1)] : partes;
  return nomes.map((parte) => [...parte][0] ?? "").join("").toLocaleUpperCase("pt-BR");
}

function itensMenu(usuario, rota) {
  const itens = [];
  if (usuario.tipo === "tecnico") {
    itens.push(["Fila", "/fila", "fila"], ["Em meu atendimento", "/atendimento", "atendimento"]);
  }
  itens.push([usuario.tipo === "funcionario" ? "Meus chamados" : "Chamados", "/chamados", "chamados"]);
  if (usuario.tipo === "administrador") {
    itens.push(["Usuários", "/usuarios", "usuarios"], ["Categorias", "/categorias", "categorias"]);
  }
  itens.push(["Minha conta", "/conta", "conta"]);

  return itens.map(([texto, destino, simbolo]) => {
    const atual = rota === destino || (destino === "/chamados" && rota.startsWith("/chamados/"));
    const item = link(el("span", {}, icone(simbolo), el("span", { class: "menu-rotulo" }, texto)),
      destino, "menu-item", atual);
    item.title = texto;
    return item;
  });
}

function painel(usuario, rota, inicio, encerrar, controle) {
  const sair = botao(icone("sair"), encerrar, "barra-controle barra-sair");
  sair.setAttribute("aria-label", "Sair");
  sair.title = "Sair";

  return [
    el("div", { class: "barra-topo" }, link(marca(), inicio, "marca-link"), controle),
    el("nav", { class: "menu", "aria-label": "Menu principal" }, itensMenu(usuario, rota)),
    el("div", { class: "identidade" },
      el("span", { class: "avatar", "aria-hidden": "true" }, iniciais(usuario.nome)),
      el("div", { class: "perfil", title: usuario.nome }, el("strong", {}, usuario.nome),
        el("span", {}, perfis[usuario.tipo])),
      sair,
    ),
  ];
}

export function estruturaAutenticada({ usuario, rota, inicio, encerrar, tela, sinal }) {
  const controle = botao(null, () => {
    recolhida = !recolhida;
    atualizarBarra();
  }, "barra-controle");
  controle.setAttribute("aria-controls", "barra-desktop");

  const fechar = botao(icone("fechar"), () => gaveta.close(), "barra-controle");
  fechar.setAttribute("aria-label", "Fechar menu");
  fechar.setAttribute("autofocus", "");
  const gaveta = el("dialog", { class: "barra-gaveta", id: "barra-mobile", "aria-label": "Navegação HelpDesk" },
    el("div", { class: "barra" }, painel(usuario, rota, inicio, encerrar, fechar)));
  const abrir = botao(icone("menu"), () => gaveta.showModal(), "barra-controle");
  abrir.setAttribute("aria-label", "Abrir menu");
  abrir.setAttribute("aria-haspopup", "dialog");
  abrir.setAttribute("aria-controls", gaveta.id);
  gaveta.addEventListener("click", ({ target }) => {
    if (target === gaveta || target.closest("a")?.hash === location.hash) gaveta.close();
  });

  const mobile = matchMedia("(max-width: 58rem)");
  mobile.addEventListener("change", ({ matches }) => {
    if (!matches && gaveta.open) gaveta.close();
  }, { signal: sinal });

  const estrutura = el("div", { class: "aplicacao" },
    el("aside", { class: "barra barra-desktop", id: "barra-desktop" },
      painel(usuario, rota, inicio, encerrar, controle)),
    el("header", { class: "barra-mobile" }, abrir, link(marca(), inicio, "marca-link")),
    tela,
    gaveta,
  );

  function atualizarBarra() {
    const rotulo = recolhida ? "Expandir menu" : "Recolher menu";
    controle.title = rotulo;
    controle.setAttribute("aria-label", rotulo);
    controle.setAttribute("aria-expanded", String(!recolhida));
    controle.replaceChildren(icone(recolhida ? "expandir" : "recolher"));
    estrutura.classList.toggle("aplicacao-recolhida", recolhida);
  }

  atualizarBarra();
  return estrutura;
}

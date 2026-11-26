import "../css/tokens.css";
import "../css/base.css";
import "../css/interface.css";
import "../css/login.css";
import "../css/chamados.css";
import { sair, usuarioAtual } from "./api.js";
import { estruturaAutenticada, marca } from "./barra.js";
import { detalheChamado, listarChamados, novoChamado } from "./chamados.js";
import { gestaoCategorias, gestaoUsuarios, minhaConta } from "./gestao.js";
import { telaAcesso } from "./login.js";
import { avisar, botao, cabecalho, el, erroVisivel, link } from "./ui.js";

const raiz = document.querySelector("#aplicacao");
let visualizacao;
let ultimaLista;
let destinoAposLogin;

function rotaInicial(usuario) {
  return usuario.tipo === "tecnico" ? "/fila" : "/chamados";
}

function navegar(destino, substituir = false) {
  if (location.hash !== `#${destino}`) {
    if (substituir) history.replaceState(null, "", `#${destino}`);
    else history.pushState(null, "", `#${destino}`);
  }
  mostrar();
}

function encerrarSessao() {
  sair();
  ultimaLista = undefined;
  destinoAposLogin = undefined;
  navegar("/entrar", true);
  avisar("Sessão encerrada.");
}

function concluirLogin() {
  const usuario = usuarioAtual();
  if (!usuario) return;

  const destino = destinoAposLogin || rotaInicial(usuario);
  destinoAposLogin = undefined;
  avisar("");
  navegar(destino, true);
}

async function mostrar() {
  const restaurarFoco = raiz.contains(document.activeElement) || document.activeElement === document.body
    || Boolean(document.querySelector("dialog[open]"));
  visualizacao?.abort();
  document.querySelector("dialog[open]")?.close();
  const { signal: sinal } = visualizacao = new AbortController();
  const [rota, busca] = location.hash.slice(1).split("?", 2);
  const usuario = usuarioAtual();

  if (!usuario) {
    const solicitarAcesso = rota === "/solicitar-acesso";
    if (!solicitarAcesso && rota !== "/entrar") {
      if (rota.startsWith("/")) destinoAposLogin = `${rota}${busca ? `?${busca}` : ""}`;
      history.replaceState(null, "", "#/entrar");
    }

    raiz.replaceChildren(telaAcesso(marca(), solicitarAcesso, concluirLogin));
    document.title = `${solicitarAcesso ? "Solicitar acesso" : "Entrar"} | HelpDesk`;
    raiz.querySelector("h1").focus({ preventScroll: true });
    window.scrollTo(0, 0);
    return;
  }

  const inicio = rotaInicial(usuario);
  if (!rota || rota === "/entrar" || rota === "/solicitar-acesso") {
    navegar(inicio, true);
    return;
  }

  const tela = el("main", { id: "conteudo", class: "conteudo", tabindex: "-1" });
  raiz.replaceChildren(estruturaAutenticada({ usuario, rota, inicio, encerrar: encerrarSessao, tela, sinal }));
  if (restaurarFoco) tela.focus({ preventScroll: true });

  try {
    const contexto = { usuario, sinal, tela, navegar, rota, recarregar: mostrar, consulta: new URLSearchParams(busca) };
    const id = /^\/chamados\/([1-9]\d*)$/.exec(rota)?.[1];
    if (rota === "/chamados" || (["/fila", "/atendimento"].includes(rota) && usuario.tipo === "tecnico")) {
      ultimaLista = `${rota}${busca ? `?${busca}` : ""}`;
      await listarChamados(contexto);
    } else if (rota === "/chamados/novo") {
      await novoChamado(contexto);
    } else if (id && Number(id) <= 2 ** 31 - 1) {
      await detalheChamado({ ...contexto, id, inicio: ultimaLista || inicio });
    } else if (rota === "/conta") {
      minhaConta(contexto);
    } else if (rota === "/usuarios" && usuario.tipo === "administrador") {
      await gestaoUsuarios(contexto);
    } else if (rota === "/categorias" && usuario.tipo === "administrador") {
      await gestaoCategorias(contexto);
    } else {
      tela.append(cabecalho("Página indisponível", "Esta página não existe ou não está disponível para seu perfil.",
        link("Voltar aos chamados", inicio, "botao")));
    }
  } catch (erro) {
    if (sinal.aborted) return;
    const indisponivel = [403, 404].includes(erro.status);
    tela.replaceChildren(cabecalho(indisponivel ? "Página indisponível" : "Não foi possível carregar a página"),
      el("section", { class: "painel estado" }, erroVisivel(erro), indisponivel
        ? link("Voltar aos chamados", inicio, "botao") : botao("Tentar novamente", mostrar)));
  } finally {
    if (!sinal.aborted) {
      const titulo = tela.querySelector("h1");
      if (titulo) document.title = `${titulo.textContent} | Help Desk`;
      if (document.activeElement === tela) titulo?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    }
  }
}

document.querySelector(".atalho").addEventListener("click", (evento) => {
  evento.preventDefault();
  document.querySelector("#conteudo")?.focus();
});
window.addEventListener("hashchange", mostrar);
window.addEventListener("sessao-expirada", () => {
  ultimaLista = undefined;
  mostrar();
  avisar("Sua sessão expirou. Entre novamente para continuar.");
});
mostrar();

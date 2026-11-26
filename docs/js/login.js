import ilustracao from "../assets/fluxo-chamados.svg";
import { entrar } from "./api.js";
import { botao, el, entrada, formulario, iconeSvg, link } from "./ui.js";

const icones = {
  email: "M4 6h16v12H4zM4 7l8 6 8-6",
  senha: "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3m-4 7v-3",
  mostrar: "M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6zm13 0a3 3 0 1 0-6 0 3 3 0 0 0 6 0z",
  ocultar: "m3 3 18 18M10 6.2c.6-.1 1.3-.2 2-.2 6.5 0 10 6 10 6a16 16 0 0 1-3 3.3M6.4 7.6A16 16 0 0 0 2 12s3.5 6 10 6c1.4 0 2.7-.3 3.8-.8",
};

function campoLogin(rotulo, nome, opcoes) {
  const id = `login-${nome}`;
  const controle = entrada(nome, { id, ...opcoes });
  const linha = el("div", { class: "login-controle" }, iconeSvg(icones[nome]), controle);

  if (nome === "senha") {
    const alternar = botao(iconeSvg(icones.mostrar), () => {
      const exibir = controle.type === "password";
      controle.type = exibir ? "text" : "password";
      alternar.setAttribute("aria-label", exibir ? "Ocultar senha" : "Mostrar senha");
      alternar.replaceChildren(iconeSvg(exibir ? icones.ocultar : icones.mostrar));
    }, "login-alternar-senha");
    alternar.setAttribute("aria-label", "Mostrar senha");
    alternar.setAttribute("aria-controls", id);
    linha.append(alternar);
  }

  return el("div", { class: "campo" }, el("label", { for: id }, el("span", {}, rotulo)), linha);
}

function formularioLogin(concluirLogin) {
  return formulario([
    campoLogin("E-mail", "email", { type: "email", autocomplete: "username", maxlength: 254 }),
    campoLogin("Senha", "senha", { type: "password", autocomplete: "current-password", spellcheck: "false" }),
  ], "Entrar", async ({ email, senha }) => {
    await entrar(email, senha);
    concluirLogin();
  });
}

export function telaAcesso(marca, solicitarAcesso, concluirLogin) {
  const titulo = solicitarAcesso ? "Solicitar acesso" : "Bem-vindo de volta";
  const descricao = solicitarAcesso
    ? "Peça ao administrador do HelpDesk da sua empresa para criar sua conta. Depois, volte para entrar."
    : "Use seu e-mail e sua senha para acessar a conta.";

  const institucional = el("div", { class: "login-marca" },
    marca,
    el("div", { class: "login-institucional" },
      el("p", { class: "login-chamada" }, "Suporte eficiente. ", el("br"), "Problemas resolvidos."),
      el("p", { class: "login-descricao" },
        "Abra chamados de TI, acompanhe o atendimento e consulte a solução em um só lugar."),
      el("img", { class: "login-ilustracao", src: ilustracao, alt: "", width: 400, height: 232 }),
    ),
  );

  const autenticacao = el("main", { id: "conteudo", class: "login-form", tabindex: "-1" },
    el("div", { class: "login-conteudo" },
      el("header", { class: "login-cabecalho" },
        el("h1", { tabindex: "-1" }, titulo),
        el("p", {}, descricao),
      ),
      solicitarAcesso
        ? link("Voltar para o login", "/entrar")
        : [
          formularioLogin(concluirLogin),
          el("p", { class: "login-cadastro" },
            "Ainda não possui uma conta? ", link("Solicite uma conta", "/solicitar-acesso")),
        ],
    ),
  );

  return el("div", { class: "login" }, institucional, autenticacao);
}

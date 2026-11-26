let temporizadorAviso;
let proximoErroCampo = 0;

export function el(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);

  for (const [nome, valor] of Object.entries(atributos)) {
    if (valor !== false && valor != null) elemento.setAttribute(nome, valor === true ? "" : valor);
  }

  elemento.append(...filhos.flat().filter((filho) => filho != null));
  return elemento;
}

export function iconeSvg(caminho) {
  const namespace = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(namespace, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");

  const desenho = document.createElementNS(namespace, "path");
  desenho.setAttribute("d", caminho);
  svg.append(desenho);
  return svg;
}

export function link(texto, rota, classe, atual = false) {
  return el("a", { href: `#${rota}`, class: classe, "aria-current": atual ? "page" : null }, texto);
}

export function botao(texto, clicou, classe = "botao") {
  const elemento = el("button", { type: "button", class: classe }, texto);
  elemento.addEventListener("click", clicou);
  return elemento;
}

export function cabecalho(titulo, texto, acao) {
  return el("header", { class: "cabecalho" },
    el("div", {}, el("h1", { tabindex: "-1" }, titulo), texto && el("p", {}, texto) || null),
    acao,
  );
}

export function estado(titulo, texto, acao) {
  return el("section", { class: "painel estado" }, el("h2", {}, titulo), el("p", {}, texto), acao);
}

export function carregando() {
  return el("p", { class: "estado", role: "status" }, "Carregando…");
}

export function avisar(texto) {
  const notificacao = document.querySelector("#notificacao");
  clearTimeout(temporizadorAviso);
  notificacao.textContent = texto;
  if (texto) temporizadorAviso = setTimeout(() => { notificacao.textContent = ""; }, 6000);
}

export function erroVisivel(erro) {
  const explicacoes = {
    401: "Não foi possível confirmar o acesso. Verifique suas credenciais ou entre novamente.",
    403: "Você não tem permissão para esta operação.",
    404: "O registro não foi encontrado ou não está disponível para você.",
    500: "O servidor não conseguiu concluir a solicitação.",
  };
  const texto = explicacoes[erro.status] || erro.message || "Não foi possível concluir a solicitação.";
  const segundos = Number(erro.retryAfter);
  const espera = erro.status === 429 && segundos > 0 ? ` Tente novamente em ${segundos} s.` : "";
  return el("p", { class: "mensagem erro", role: "alert" }, `${texto}${espera}`);
}

export function campo(rotulo, controle) {
  return el("label", { class: "campo" }, el("span", {}, rotulo), controle);
}

export function entrada(nome, opcoes = {}) {
  return el("input", { name: nome, required: true, ...opcoes });
}

export function seletor(nome, opcoes, valor = "", obrigatorio = false) {
  const controle = el("select", { name: nome, required: obrigatorio },
    opcoes.map(([chave, texto]) => el("option", { value: chave }, texto)),
  );
  if ([...controle.options].some((opcao) => opcao.value === String(valor))) controle.value = valor;
  return controle;
}

export function area(nome, linhas = 5) {
  return el("textarea", { name: nome, rows: linhas, required: true, "data-limite-texto": true });
}

export function formulario(campos, rotulo, enviar, { extra, cancelar } = {}) {
  const retorno = el("div");
  const enviarBotao = el("button", { class: "botao primaria", type: "submit" }, rotulo);
  const form = el("form", { class: "formulario" }, extra, campos, retorno,
    el("div", { class: "acoes" }, enviarBotao, cancelar),
  );

  form.addEventListener("input", ({ target }) => {
    if (typeof target.setCustomValidity === "function") target.setCustomValidity("");
    const descricao = target.getAttribute("aria-describedby");
    if (descricao) {
      const item = retorno.querySelector(`#${descricao}`);
      item?.remove();
      target.removeAttribute("aria-describedby");
      if (!retorno.querySelector("li")) retorno.replaceChildren();
    }
    target.removeAttribute("aria-invalid");
  });
  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (enviarBotao.disabled) return;
    retorno.replaceChildren();
    for (const controle of form.querySelectorAll("[aria-invalid]")) {
      controle.removeAttribute("aria-invalid");
      controle.removeAttribute("aria-describedby");
    }

    const dados = Object.fromEntries(new FormData(form));
    for (const [nome, bruto] of Object.entries(dados)) {
      const controle = form.elements.namedItem(nome);
      const senha = controle.type === "password" || controle.autocomplete === "current-password";
      const valor = senha ? bruto : bruto.trim();
      let erro;

      if (controle.required && !valor.trim()) erro = "Preencha este campo.";
      if (controle.hasAttribute("data-limite-texto") && new TextEncoder().encode(valor).length > 65535) {
        erro = "O texto ultrapassa o limite de 65.535 bytes.";
      }
      if (erro) {
        controle.setCustomValidity(erro);
        controle.reportValidity();
        return;
      }
      dados[nome] = valor;
    }

    enviarBotao.disabled = true;
    enviarBotao.textContent = "Aguarde…";
    try {
      await enviar(dados);
    } catch (erro) {
      const detalhes = erro.detalhes ?? [];
      const lista = el("ul");
      let primeiro;
      for (const detalhe of detalhes) {
        const nome = detalhe.loc?.at(-1);
        const controle = form.elements.namedItem(nome ?? "");
        if (!controle?.setCustomValidity) continue;
        const rotuloCampo = controle.labels?.[0]?.querySelector("span")?.textContent || nome;
        const mensagens = {
          missing: "Preencha este campo.",
          string_too_short: "Digite um valor mais longo.",
          string_too_long: "Reduza o tamanho do texto.",
          value_error: controle.type === "email" ? "Informe um e-mail válido." : "Revise o valor informado.",
        };
        const id = `erro-campo-${++proximoErroCampo}`;
        controle.setAttribute("aria-invalid", "true");
        controle.setAttribute("aria-describedby", id);
        primeiro ??= controle;
        lista.append(el("li", { id }, `${rotuloCampo}: ${mensagens[detalhe.type] || "Confira o valor informado."}`));
      }
      if (lista.childElementCount) {
        retorno.append(el("div", { class: "mensagem erro", role: "alert" }, "Revise os campos abaixo.", lista));
        primeiro.focus();
      } else {
        retorno.append(erroVisivel(erro));
      }
    } finally {
      enviarBotao.disabled = false;
      enviarBotao.textContent = rotulo;
    }
  });
  return form;
}

export function dialogo(titulo, campos, acao, enviar, texto) {
  const caixa = el("dialog", { "aria-labelledby": "titulo-dialogo" },
    el("h2", { id: "titulo-dialogo" }, titulo),
  );
  const cancelar = botao("Cancelar", () => caixa.close());
  if (!campos.length) cancelar.setAttribute("autofocus", "");
  caixa.append(formulario(campos, acao, async (dados) => {
    await enviar(dados);
    caixa.close();
  }, { extra: texto ? el("p", {}, texto) : null, cancelar }));
  caixa.addEventListener("close", () => caixa.remove(), { once: true });
  document.body.append(caixa);
  caixa.showModal();
}

export function dataHora(valor) {
  if (!valor) return "—";
  const instante = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(valor) ? valor : `${valor}Z`);
  if (Number.isNaN(instante.getTime())) return "—";
  return el("time", { datetime: instante.toISOString() },
    new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(instante),
  );
}

export function tabela(colunas, linhas, rotulo) {
  return el("table", { role: "table", "aria-label": rotulo },
    el("thead", { role: "rowgroup" }, el("tr", { role: "row" },
      colunas.map((coluna) => el("th", { scope: "col", role: "columnheader" }, coluna)))),
    el("tbody", { role: "rowgroup" }, linhas.map((linha) => el("tr", { role: "row" },
      linha.map((celula, indice) => el("td", { role: "cell" },
        el("span", { class: "rotulo-celula", "aria-hidden": "true" }, colunas[indice]),
        el("div", {}, celula),
      )),
    ))),
  );
}

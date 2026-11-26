import { permissoes } from "./permissoes.js";
import { chamados, categorias, usuarios } from "./servicos.js";
import {
  area, avisar, botao, cabecalho, campo, carregando, dataHora, dialogo, el, entrada,
  erroVisivel, estado, formulario, iconeSvg, link, seletor, tabela,
} from "./ui.js";

const STATUS = {
  aberto: "Aberto", em_andamento: "Em atendimento", aguardando_resposta: "Aguardando resposta",
  resolvido: "Resolvido", fechado: "Fechado",
};
const PRIORIDADES = {
  nao_classificada: "Não classificada", baixa: "Baixa", media: "Média", alta: "Alta", critica: "Crítica",
};
const ORDENACOES = { aberto_em: "Abertura", id: "Número", prioridade: "Prioridade", status: "Status" };
const ESTADOS = {
  aberto: "info", em_andamento: "alerta", aguardando_resposta: "alerta", resolvido: "sucesso",
  fechado: "neutro", nao_classificada: "neutro", baixa: "neutro", media: "info", alta: "prioridade-alta", critica: "erro",
};
const TAMANHO_PAGINA = 20;
const PADROES = { ordem: "aberto_em", direcao: "desc" };
const DIRECOES = { desc: "Decrescente", asc: "Crescente" };
const FILTROS_AVANCADOS = ["id_tecnico", "sem_tecnico", "ordem", "direcao"];
const COLUNAS = ["ID", "Título", "Categoria", "Status", "Prioridade", "Solicitante", "Responsável", "Abertura", "Ações"];
const ICONE_CHAMADOS = "M6 4h12v16H6zM9 9h6M9 13h6";
const ICONE_FILTRO = "M4 6h16M7 12h10m-7 6h4";
const ICONE_ALERTA = "M12 8v5m0 3v.01M4 20h16L12 4z";
const ICONE_PERMISSAO = "M6 10h12v10H6zM9 10V7a3 3 0 0 1 6 0v3m-3 4v2";
const ICONE_PROXIMA = "m9 6 6 6-6 6";
const ICONE_ANTERIOR = "m15 6-6 6 6 6";

function etiqueta(valor, rotulos) {
  return el("span", { class: `etiqueta ${ESTADOS[valor] || "neutro"}` }, rotulos[valor] || "Não informado");
}

function opcoesCategorias(lista) {
  return lista.map(({ id, nome }) => [id, nome]);
}

function selecaoCategoria(lista, valor, titulo = "Selecione uma categoria") {
  return seletor("id_categoria", [["", titulo], ...opcoesCategorias(lista)], valor, true);
}

function mapaNomes(lista) {
  return new Map(lista.map(({ id, nome }) => [id, nome]));
}

function identificador(valor) {
  return /^\d+$/.test(valor ?? "") && Number(valor) > 0 && Number(valor) <= 2 ** 31 - 1;
}

function filtrosDaConsulta(consulta, fila, permiteAtribuicao) {
  const parametros = new URLSearchParams();
  for (const [chave, valores] of Object.entries({
    status: STATUS, prioridade: PRIORIDADES, ordem: ORDENACOES, direcao: DIRECOES,
  })) {
    const valor = consulta.get(chave);
    if (chave === "status" && fila) continue;
    if (valor !== PADROES[chave] && Object.hasOwn(valores, valor)) parametros.set(chave, valor);
  }
  if (identificador(consulta.get("id_categoria"))) parametros.set("id_categoria", consulta.get("id_categoria"));
  if (permiteAtribuicao) {
    if (consulta.get("sem_tecnico") === "true") parametros.set("sem_tecnico", "true");
    else if (identificador(consulta.get("id_tecnico"))) parametros.set("id_tecnico", consulta.get("id_tecnico"));
  }
  return parametros;
}

function seletorFiltro(nome, rotulo, opcoes, valor) {
  const itens = [...opcoes];
  if (valor && !itens.some(([chave]) => String(chave) === valor)) itens.push([valor, `${rotulo} #${valor}`]);
  return seletor(nome, itens, valor);
}

function painelFiltros({ parametros, rota, fila, admin, permiteAtribuicao, listaCategorias, diretorio, irPara }) {
  const valor = (chave, padrao = "") => parametros.get(chave) ?? padrao;
  const principais = el("div", { class: "filtros-principais" },
    !fila ? campo("Status", seletor("status", [["", "Todos"], ...Object.entries(STATUS)], valor("status"))) : null,
    campo("Prioridade", seletor("prioridade", [["", "Todas"], ...Object.entries(PRIORIDADES)], valor("prioridade"))),
    campo("Categoria", seletorFiltro("id_categoria", "Categoria",
      [["", "Todas"], ...opcoesCategorias(listaCategorias)], valor("id_categoria"))),
  );

  const avancados = el("div", { class: "filtros-avancados", id: "filtros-avancados" });
  if (permiteAtribuicao) {
    const tecnico = admin
      ? seletorFiltro("id_tecnico", "Técnico", [["", "Todos"], ...diretorio.map(({ id, nome }) => [id, `${nome} (#${id})`])],
        valor("id_tecnico"))
      : entrada("id_tecnico", { type: "number", min: 1, max: 2 ** 31 - 1, value: valor("id_tecnico"), required: false });
    const atribuicao = seletor("sem_tecnico", [["", "Qualquer"], ["true", "Sem técnico"]], valor("sem_tecnico"));
    const atualizarResponsavel = () => { tecnico.disabled = atribuicao.value === "true"; };
    atribuicao.addEventListener("change", atualizarResponsavel);
    atualizarResponsavel();
    avancados.append(campo(admin ? "Responsável" : "Responsável (ID do técnico)", tecnico), campo("Atribuição", atribuicao));
  }
  avancados.append(
    campo("Ordenação", seletor("ordem", Object.entries(ORDENACOES), valor("ordem", PADROES.ordem))),
    campo("Direção", seletor("direcao", Object.entries(DIRECOES), valor("direcao", PADROES.direcao))),
  );

  const seta = iconeSvg("m6 9 6 6 6-6");
  const alternar = botao(el("span", {}, "Mais filtros", seta), () => {
    avancados.hidden = !avancados.hidden;
    alternar.setAttribute("aria-expanded", String(!avancados.hidden));
  }, "botao filtros-alternar");
  avancados.hidden = !FILTROS_AVANCADOS.some((chave) => parametros.has(chave));
  alternar.setAttribute("aria-controls", avancados.id);
  alternar.setAttribute("aria-expanded", String(!avancados.hidden));

  const formularioFiltros = el("form", { class: "filtros-formulario", "aria-labelledby": "titulo-filtros" },
    principais, alternar, avancados,
    el("div", { class: "acoes filtros-acoes" },
      link("Limpar filtros", rota, "botao filtros-limpar"),
      el("button", { class: "botao primaria", type: "submit" }, "Aplicar filtros")),
  );
  for (const controle of formularioFiltros.elements) {
    if (parametros.has(controle.name)) controle.dataset.filtroAtivo = "";
  }
  formularioFiltros.addEventListener("submit", (evento) => {
    evento.preventDefault();
    irPara(filtrosDaConsulta(new URLSearchParams(new FormData(formularioFiltros)), fila, permiteAtribuicao));
  });

  const quantidade = parametros.size;
  return el("section", { class: "painel filtros", "aria-labelledby": "titulo-filtros" },
    el("div", { class: "filtros-topo" },
      el("h2", { id: "titulo-filtros" }, iconeSvg(ICONE_FILTRO), "Filtros"),
      quantidade ? el("span", { class: "filtros-ativos" },
        `${quantidade} ${quantidade === 1 ? "filtro ativo" : "filtros ativos"}`) : null),
    formularioFiltros,
  );
}

function estadoChamados(icone, titulo, texto, acao, mensagem) {
  const painel = estado(titulo, texto, acao);
  painel.classList.add("chamados-estado");
  painel.prepend(el("span", { class: "estado-icone" }, iconeSvg(icone)));
  if (mensagem) painel.querySelector("p").replaceWith(mensagem);
  return painel;
}

function tabelaChamados({ registros, listaCategorias, diretorio, usuario, parametros, destino, deslocamento, titulo }) {
  const nomesCategorias = mapaNomes(listaCategorias);
  const nomesPessoas = mapaNomes(diretorio);
  const pessoa = (id, funcao) => id === usuario.id ? usuario.nome : nomesPessoas.get(id) ?? `${funcao} #${id}`;
  const linhas = registros.slice(0, TAMANHO_PAGINA).map((registro) => {
    const rota = `/chamados/${registro.id}`;
    const acao = link(iconeSvg(ICONE_PROXIMA), rota, "botao chamado-abrir");
    acao.setAttribute("aria-label", `Ver chamado #${registro.id}`);
    acao.title = "Ver chamado";

    return [
      el("span", { class: "numero" }, `#${registro.id}`),
      link(registro.titulo, rota, "chamado-link"),
      nomesCategorias.get(registro.id_categoria) ?? `Categoria #${registro.id_categoria}`,
      etiqueta(registro.status, STATUS),
      etiqueta(registro.prioridade, PRIORIDADES),
      pessoa(registro.id_usuario, "Usuário"),
      registro.id_tecnico === null ? el("span", { class: "texto-secundario" }, "Não atribuído")
        : pessoa(registro.id_tecnico, "Técnico"),
      dataHora(registro.aberto_em),
      acao,
    ];
  });

  function pagina(offset) {
    const proxima = new URLSearchParams(parametros);
    if (offset > 0) proxima.set("deslocamento", offset);
    return destino(proxima);
  }

  const anterior = el("span", {}, iconeSvg(ICONE_ANTERIOR), "Anterior");
  const proxima = el("span", {}, "Próxima", iconeSvg(ICONE_PROXIMA));
  const tabelaRolavel = el("div", { class: "chamados-rolagem" }, tabela(COLUNAS, linhas, titulo));
  const observarTabela = new ResizeObserver(() => {
    const temRolagem = tabelaRolavel.scrollWidth > tabelaRolavel.clientWidth;
    if (temRolagem) {
      tabelaRolavel.tabIndex = 0;
      tabelaRolavel.setAttribute("role", "region");
      tabelaRolavel.setAttribute("aria-label", "Rolagem horizontal da tabela");
    } else {
      for (const atributo of ["tabindex", "role", "aria-label"]) tabelaRolavel.removeAttribute(atributo);
    }
  });
  observarTabela.observe(tabelaRolavel);

  const painel = el("div", { class: "painel lista chamados-tabela" },
    el("p", { class: "chamados-dica", "aria-hidden": "true" }, "Deslize a tabela para ver mais colunas."),
    tabelaRolavel,
    el("nav", { class: "paginacao", "aria-label": "Paginação de chamados" },
      el("span", { class: "paginacao-faixa" }, `Exibindo ${deslocamento + 1}–${deslocamento + linhas.length}`),
      el("div", { class: "acoes" },
        deslocamento ? link(anterior, pagina(Math.max(0, deslocamento - TAMANHO_PAGINA)), "botao")
          : el("button", { class: "botao", type: "button", disabled: true }, anterior),
        registros.length > TAMANHO_PAGINA ? link(proxima, pagina(deslocamento + TAMANHO_PAGINA), "botao")
          : el("button", { class: "botao", type: "button", disabled: true }, proxima)),
    ),
  );
  return { painel, observarTabela };
}

export async function listarChamados({ usuario, rota, consulta, sinal, tela, navegar, recarregar }) {
  const fila = rota === "/fila";
  const meusAtendimentos = rota === "/atendimento";
  const admin = usuario.tipo === "administrador";
  const permiteAtribuicao = usuario.tipo !== "funcionario" && !fila && !meusAtendimentos;
  const titulo = fila ? "Fila de atendimento" : meusAtendimentos ? "Em meu atendimento" : "Chamados";
  const subtitulo = fila ? "Chamados abertos sem responsável." : meusAtendimentos ? "Chamados atribuídos a você."
    : "Gerencie e acompanhe os chamados de suporte.";
  const acaoNovo = (comIcone = false) =>
    link(el("span", {}, comIcone ? iconeSvg("M12 5v14M5 12h14") : null, "Novo chamado"), "/chamados/novo", "botao primaria");

  tela.classList.add("chamados-pagina");
  tela.append(cabecalho(titulo, subtitulo, acaoNovo(true)));
  const conteudo = el("div", { class: "chamados-conteudo" },
    el("div", { class: "painel chamados-carregando", role: "status" }, "Carregando chamados…"));
  tela.append(conteudo);

  const parametros = filtrosDaConsulta(consulta, fila, permiteAtribuicao);
  const deslocamentoInformado = Number(consulta.get("deslocamento"));
  const deslocamento = Number.isSafeInteger(deslocamentoInformado) && deslocamentoInformado > 0
    ? deslocamentoInformado : 0;
  const dados = new URLSearchParams(parametros);
  dados.set("limite", TAMANHO_PAGINA + 1);
  dados.set("deslocamento", deslocamento);
  if (fila) {
    dados.set("status", "aberto");
    dados.set("sem_tecnico", "true");
  }
  if (meusAtendimentos) dados.set("id_tecnico", usuario.id);

  const destino = (valores) => valores.size ? `${rota}?${valores}` : rota;
  try {
    const [registros, listaCategorias, diretorio] = await Promise.all([
      chamados.listar(dados, sinal),
      categorias.listar(sinal, admin),
      admin ? usuarios.listar(sinal) : [],
    ]);
    if (sinal.aborted) return;

    const filtros = painelFiltros({ parametros, rota, fila, admin, permiteAtribuicao, listaCategorias, diretorio,
      irPara: (valores) => navegar(destino(valores)) });
    if (registros.length) {
      const { painel, observarTabela } = tabelaChamados({
        registros, listaCategorias, diretorio, usuario, parametros, destino, deslocamento, titulo,
      });
      sinal.addEventListener("abort", () => observarTabela.disconnect(), { once: true });
      conteudo.replaceChildren(filtros, painel);
      return;
    }

    let vazio;
    const temFiltros = [...parametros.keys()].some((chave) => !Object.hasOwn(PADROES, chave));
    if (deslocamento) {
      const anterior = new URLSearchParams(parametros);
      if (deslocamento > TAMANHO_PAGINA) anterior.set("deslocamento", deslocamento - TAMANHO_PAGINA);
      vazio = estadoChamados(ICONE_CHAMADOS, "Esta página está vazia", "Volte à página anterior para continuar.",
        link("Página anterior", destino(anterior), "botao"));
    } else if (temFiltros) {
      vazio = estadoChamados(ICONE_FILTRO, "Nenhum resultado para os filtros",
        "Altere ou limpe os filtros para ampliar a busca.", link("Limpar filtros", rota, "botao"));
    } else {
      const texto = fila ? "Os chamados abertos e sem responsável aparecem aqui."
        : meusAtendimentos ? "Os chamados atribuídos a você aparecem aqui."
          : "Os chamados de suporte aparecem aqui assim que são abertos.";
      const acao = fila ? link("Ver meus atendimentos", "/atendimento", "botao")
        : meusAtendimentos ? link("Ver fila", "/fila", "botao") : acaoNovo();
      vazio = estadoChamados(ICONE_CHAMADOS, "Nenhum chamado nesta lista", texto, acao);
    }
    conteudo.replaceChildren(filtros, vazio);
  } catch (erro) {
    if (sinal.aborted) return;
    const semPermissao = erro.status === 403;
    conteudo.replaceChildren(estadoChamados(semPermissao ? ICONE_PERMISSAO : ICONE_ALERTA,
      semPermissao ? "Acesso não permitido" : "Não foi possível carregar os chamados", "",
      semPermissao ? link("Ir para minha conta", "/conta", "botao") : botao("Tentar novamente", recarregar),
      erroVisivel(erro)));
  }
}

export async function novoChamado({ tela, sinal, navegar }) {
  tela.append(cabecalho("Novo chamado", "Descreva o problema para que a equipe possa ajudar."));
  const conteudo = el("div", {}, carregando());
  tela.append(conteudo);
  const lista = await categorias.listar(sinal);

  if (!lista.length) {
    conteudo.replaceChildren(estado("Nenhuma categoria ativa",
      "Peça à administração para cadastrar ou ativar uma categoria antes de abrir um chamado."));
    return;
  }

  conteudo.replaceChildren(el("section", { class: "painel editor" }, formulario([
    campo("Título", entrada("titulo", { maxlength: 150 })),
    campo("Categoria", selecaoCategoria(lista)),
    campo("Descrição do problema", area("descricao", 7)),
  ], "Abrir chamado", async (dados) => {
    const novo = await chamados.criar({ ...dados, id_categoria: Number(dados.id_categoria) });
    if (sinal.aborted) return;
    navegar(`/chamados/${novo.id}`);
    avisar(`Chamado #${novo.id} aberto.`);
  })));
}

function dado(rotulo, valor) {
  return el("div", {}, el("dt", {}, rotulo), el("dd", {}, valor));
}

function bloco(titulo, ...filhos) {
  return el("section", { class: "painel bloco" }, el("h2", {}, titulo), filhos);
}

async function preencherSecao(destino, obter, desenhar, { ausente, sinal } = {}) {
  destino.replaceChildren(carregando());
  try {
    const dados = await obter();
    if (!sinal?.aborted) destino.replaceChildren(desenhar(dados));
  } catch (erro) {
    if (erro.name === "AbortError" || sinal?.aborted) return;
    destino.replaceChildren(
      erro.status === 404 && ausente ? el("p", {}, ausente) : erroVisivel(erro),
      erro.status === 404 && ausente ? null
        : botao("Tentar novamente", () => preencherSecao(destino, obter, desenhar, { ausente, sinal })),
    );
  }
}

function nota(conteudo, criadoEm, autor) {
  return el("li", {},
    el("div", { class: "metadados" }, autor && el("strong", {}, autor), dataHora(criadoEm)),
    el("p", { class: "texto-livre" }, conteudo),
  );
}

const EVENTOS = {
  criacao: "Abertura", prioridade: "Prioridade", categoria: "Categoria", atribuicao: "Atribuição",
  redistribuicao: "Redistribuição", status: "Status", resolucao: "Resolução", fechamento: "Fechamento",
  devolucao: "Devolução",
};

export async function detalheChamado({ id, tela, sinal, usuario, recarregar, inicio }) {
  const espera = carregando();
  tela.append(espera);
  const chamado = await chamados.obter(id, sinal);
  const pode = permissoes(usuario, chamado);
  const admin = usuario.tipo === "administrador";
  const [listaCategorias, diretorio] = await Promise.all([
    categorias.listar(sinal, admin),
    admin ? usuarios.listar(sinal) : [],
  ]);
  if (sinal.aborted) return;

  const nomesCategorias = mapaNomes(listaCategorias);
  const nomesPessoas = mapaNomes(diretorio);
  const pessoa = (identidade, funcao) => identidade == null ? "Sem técnico"
    : identidade === usuario.id ? usuario.nome : nomesPessoas.get(identidade) ?? `${funcao} #${identidade}`;
  const acoes = el("div", { class: "acoes" });
  const criarAcao = (rotulo, operacao, opcoes = {}) => {
    const { campos = [], metodo = "POST", texto, preparar = (dados) => dados, primaria, sucesso } = opcoes;
    acoes.append(botao(rotulo, () => {
      dialogo(rotulo, campos.map(([titulo, controle]) => campo(titulo, controle())), rotulo, async (dados) => {
        try {
          await chamados.agir(id, operacao, metodo, campos.length ? preparar(dados) : undefined);
        } catch (erro) {
          if (erro.status === 409 && !sinal.aborted) {
            recarregar();
            avisar("O chamado mudou. Confira o estado atualizado antes de tentar novamente.");
            return;
          }
          throw erro;
        }
        if (!sinal.aborted) {
          recarregar();
          avisar(sucesso);
        }
      }, texto);
    }, primaria ? "botao primaria" : "botao"));
  };

  const categoriasAtivas = listaCategorias.filter(({ ativo }) => ativo);
  const tecnicos = diretorio.filter(({ id, tipo, ativo }) => tipo === "tecnico" && ativo && id !== chamado.id_tecnico);
  if (pode.assumir) criarAcao("Assumir chamado", "assumir", {
    primaria: true, texto: "Você passará a ser o técnico responsável e o chamado ficará em andamento.",
    sucesso: "Chamado assumido.",
  });
  if (pode.resolver) criarAcao("Registrar solução", "resolver", {
    primaria: true, campos: [["Solução para o solicitante", () => area("resolucao")]], sucesso: "Solução registrada.",
  });
  if (pode.aguardar) criarAcao("Aguardar resposta", "aguardar-resposta", {
    texto: "O chamado passará a aguardar resposta.", sucesso: "Chamado aguardando resposta.",
  });
  if (pode.retomar) criarAcao("Retomar atendimento", "retomar", {
    primaria: true, texto: "O chamado voltará para Em atendimento.", sucesso: "Atendimento retomado.",
  });
  if (pode.classificar) {
    criarAcao("Alterar prioridade", "prioridade", {
      metodo: "PUT", campos: [["Prioridade", () => seletor("prioridade", Object.entries(PRIORIDADES), chamado.prioridade, true)]],
      sucesso: "Prioridade atualizada.",
    });
    if (categoriasAtivas.length) criarAcao("Corrigir categoria", "categoria", {
      metodo: "PUT", campos: [["Categoria ativa", () => selecaoCategoria(categoriasAtivas, chamado.id_categoria)]],
      preparar: ({ id_categoria }) => ({ id_categoria: Number(id_categoria) }), sucesso: "Categoria atualizada.",
    });
  }
  if (pode.redistribuir && tecnicos.length) criarAcao("Redistribuir chamado", "responsavel", {
    metodo: "PUT", campos: [["Novo técnico", () => seletor("id_tecnico",
      [["", "Selecione um técnico"], ...tecnicos.map(({ id, nome }) => [id, `${nome} (#${id})`])], "", true)]],
    preparar: ({ id_tecnico }) => ({ id_tecnico: Number(id_tecnico) }), sucesso: "Chamado redistribuído.",
  });
  if (pode.confirmar) {
    criarAcao("Confirmar fechamento", "fechar", {
      primaria: true, texto: "Confirme somente se o problema foi resolvido. Isso encerra o chamado.",
      sucesso: "Chamado fechado.",
    });
    criarAcao("Devolver para atendimento", "devolver", {
      campos: [["Por que o problema persiste?", () => area("motivo")]], sucesso: "Chamado devolvido para atendimento.",
    });
  }

  const resolucao = el("div");
  const comentarios = el("div");
  const historico = el("div");
  const classeAcoes = acoes.childElementCount || pode.redistribuir
    ? bloco("Ações do chamado", acoes, pode.redistribuir && !tecnicos.length
      ? el("p", {}, "Não há outro técnico ativo para receber este chamado.") : null)
    : null;
  espera.replaceWith(
    link("Voltar aos chamados", inicio, "voltar"),
    cabecalho(chamado.titulo, `Chamado #${id}`, etiqueta(chamado.status, STATUS)),
    el("div", { class: "detalhe" },
      el("aside", { class: "pilha", "aria-label": "Dados e ações" },
        classeAcoes,
        bloco("Dados do chamado", el("dl", { class: "dados" },
          dado("Prioridade", etiqueta(chamado.prioridade, PRIORIDADES)),
          dado("Categoria", nomesCategorias.get(chamado.id_categoria) ?? `Categoria #${chamado.id_categoria}`),
          dado("Solicitante", pessoa(chamado.id_usuario, "Usuário")),
          dado("Responsável", pessoa(chamado.id_tecnico, "Técnico")),
          dado("Abertura", dataHora(chamado.aberto_em)),
          chamado.concluido_em ? dado("Fechamento", dataHora(chamado.concluido_em)) : null,
        )),
      ),
      el("div", { class: "pilha" },
        bloco("Descrição do problema", el("p", { class: "texto-livre" }, chamado.descricao)),
        bloco("Última solução registrada", resolucao),
        pode.lerComentarios ? bloco("Comentários internos",
          el("p", {}, "Visíveis apenas para técnicos e administradores."), comentarios,
          pode.comentar ? formulario([campo("Novo comentário interno", area("conteudo", 3))],
            "Adicionar comentário", async (dados) => {
              await chamados.agir(id, "comentarios", "POST", dados);
              if (!sinal.aborted) {
                recarregar();
                avisar("Comentário adicionado.");
              }
            }) : null,
        ) : null,
        pode.auditar ? bloco("Histórico de atendimento", historico) : null,
      ),
    ),
  );

  preencherSecao(resolucao, () => chamados.secao(id, "resolucao", sinal),
    (dados) => el("ul", { class: "registros" }, nota(dados.resolucao, dados.criado_em)),
    { sinal, ausente: "Ainda não há solução registrada." });

  if (pode.lerComentarios) preencherSecao(comentarios, () => chamados.secao(id, "comentarios", sinal),
    (itens) => itens.length ? el("ul", { class: "registros" }, itens.map((item) =>
      nota(item.conteudo, item.criado_em, pessoa(item.id_usuario, "Usuário"))))
      : el("p", {}, "Ainda não há comentários internos."), { sinal });

  if (pode.auditar) preencherSecao(historico, () => chamados.secao(id, "historico", sinal),
    (itens) => itens.length ? el("ol", { class: "registros" }, itens.map((item) =>
      el("li", {}, el("h3", {}, EVENTOS[item.tipo] || item.tipo),
        el("div", { class: "metadados" }, pessoa(item.id_usuario, "Usuário"), dataHora(item.criado_em)),
        item.anterior !== null ? el("p", { class: "texto-livre" }, `Anterior: ${item.anterior}`) : null,
        item.novo !== null ? el("p", { class: "texto-livre" }, `Novo: ${item.novo}`) : null,
      ))) : el("p", {}, "Ainda não há eventos registrados."), { sinal });
}

import { atualizarUsuario, sair } from "./api.js";
import { perfis } from "./permissoes.js";
import { categorias, usuarios } from "./servicos.js";
import {
  avisar, botao, cabecalho, campo, carregando, dialogo, el, entrada, estado, formulario, seletor, tabela,
} from "./ui.js";

const situacoes = [["true", "Ativo"], ["false", "Inativo"]];

function situacao(ativo) {
  return el("span", { class: `etiqueta ${ativo ? "sucesso" : "neutro"}` }, ativo ? "Ativo" : "Inativo");
}

const campoNome = (valor = "") => campo("Nome", entrada("nome", { value: valor, maxlength: 150, autocomplete: "name" }));
const campoEmail = (valor = "") => campo("E-mail", entrada("email", {
  type: "email", value: valor, maxlength: 254, autocomplete: "email",
}));
const campoSenha = (obrigatorio = true) => campo(obrigatorio ? "Senha inicial" : "Nova senha (opcional)", entrada("senha", {
  type: "password", required: obrigatorio, minlength: 8, maxlength: 128, autocomplete: "new-password",
}));

function atualizarTela(sinal, recarregar, mensagem) {
  if (sinal.aborted) return;
  recarregar();
  avisar(mensagem);
}

export async function gestaoUsuarios({ tela, sinal, recarregar, usuario }) {
  const criar = botao("Novo usuário", () => dialogo("Novo usuário",
    [campoNome(), campoEmail(), campoSenha()], "Criar usuário", async (dados) => {
      await usuarios.criar(dados);
      atualizarTela(sinal, recarregar, "Usuário criado como funcionário.");
    }, "A conta será criada como funcionário. Depois, use Editar acesso para mudar o perfil."), "botao primaria");
  tela.append(cabecalho("Usuários", "Crie contas e gerencie perfis e acessos.", criar));
  const conteudo = el("div", {}, carregando());
  tela.append(conteudo);
  const lista = await usuarios.listar(sinal);

  const linhas = lista.map((item) => {
    const editar = botao("Editar acesso", () => dialogo(`Editar acesso de ${item.nome}`, [
      campo("Perfil", seletor("tipo", Object.entries(perfis), item.tipo, true)),
      campo("Situação", seletor("ativo", situacoes, String(item.ativo), true)),
    ], "Salvar acesso", async ({ tipo, ativo }) => {
      const atualizado = await usuarios.editar(item.id, { tipo, ativo: ativo === "true" });
      if (item.id === usuario.id && (!atualizado.ativo || atualizado.tipo !== usuario.tipo)) {
        sair();
        recarregar();
        avisar("Seu acesso mudou. Entre novamente para continuar.");
      } else {
        atualizarTela(sinal, recarregar, "Acesso atualizado.");
      }
    }, item.id === usuario.id ? "Mudar seu perfil ou desativar sua conta encerra a sessão nesta interface." : null));
    editar.setAttribute("aria-label", `Editar acesso de ${item.nome}`);
    return [item.nome, item.email, perfis[item.tipo] ?? item.tipo, situacao(item.ativo), editar];
  });

  conteudo.replaceChildren(linhas.length
    ? el("div", { class: "painel lista" }, tabela(["Nome", "E-mail", "Perfil", "Situação", "Ações"], linhas, "Usuários"))
    : estado("Nenhum usuário encontrado", "Use Novo usuário para cadastrar uma conta."));
}

export async function gestaoCategorias({ tela, sinal, recarregar }) {
  const criar = botao("Nova categoria", () => dialogo("Nova categoria", [campoNome()], "Criar categoria",
    async (dados) => {
      await categorias.criar(dados);
      atualizarTela(sinal, recarregar, "Categoria criada.");
    }), "botao primaria");
  tela.append(cabecalho("Categorias", "Organize os assuntos dos chamados sem apagar vínculos antigos.", criar));
  const conteudo = el("div", {}, carregando());
  tela.append(conteudo);
  const lista = await categorias.listar(sinal, true);
  const linhas = lista.map((item) => {
    const editar = botao("Editar", () => dialogo(`Editar ${item.nome}`, [campoNome(item.nome)], "Salvar nome", async (dados) => {
      await categorias.editar(item.id, dados);
      atualizarTela(sinal, recarregar, "Categoria atualizada.");
    }));
    const rotulo = item.ativo ? "Desativar" : "Reativar";
    const alternar = botao(rotulo, () => dialogo(`${rotulo} ${item.nome}`, [], `${rotulo} categoria`, async () => {
      if (item.ativo) await categorias.desativar(item.id);
      else await categorias.editar(item.id, { ativo: true });
      atualizarTela(sinal, recarregar, item.ativo ? "Categoria desativada." : "Categoria reativada.");
    }, item.ativo ? "Os chamados antigos manterão esta categoria. Ela não poderá ser escolhida em novos chamados." : null));

    editar.setAttribute("aria-label", `Editar categoria ${item.nome}`);
    alternar.setAttribute("aria-label", `${rotulo} categoria ${item.nome}`);
    return [item.nome, situacao(item.ativo), el("div", { class: "acoes" }, editar, alternar)];
  });

  conteudo.replaceChildren(linhas.length
    ? el("div", { class: "painel lista" }, tabela(["Nome", "Situação", "Ações"], linhas, "Categorias"))
    : estado("Nenhuma categoria cadastrada", "Crie uma categoria para permitir a abertura de chamados."));
}

export function minhaConta({ tela, sinal, recarregar, usuario }) {
  tela.append(cabecalho("Minha conta", `Perfil: ${perfis[usuario.tipo]}`),
    el("section", { class: "painel editor" }, formulario([
      campoNome(usuario.nome), campoEmail(usuario.email), campoSenha(false),
    ], "Salvar meus dados", async ({ nome, email, senha }) => {
      const dados = {};
      if (nome !== usuario.nome) dados.nome = nome;
      if (email !== usuario.email) dados.email = email;
      if (senha) dados.senha = senha;
      if (!Object.keys(dados).length) {
        avisar("Nenhum dado foi alterado.");
        return;
      }
      const atualizado = await usuarios.atualizarConta(dados);
      if (senha) {
        sair();
        recarregar();
        avisar("Senha alterada. Entre com a nova senha.");
      } else {
        atualizarUsuario(atualizado);
        atualizarTela(sinal, recarregar, "Dados atualizados.");
      }
    }, { extra: el("p", {}, "Se alterar a senha, será necessário entrar novamente.") })),
  );
}

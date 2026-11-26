const base = (import.meta.env.VITE_API_BASE || "/api").replace(/\/+$/, "");
const limites = new Map();
let sessao = null;
let geracao = 0;

export class ErroApi extends Error {
  constructor(mensagem, status = 0, detalhes = [], retryAfter = null) {
    super(mensagem);
    this.status = status;
    this.detalhes = detalhes;
    this.retryAfter = retryAfter;
  }
}

function segundosRestantes(valor) {
  if (valor === null) return null;
  if (/^\d+$/.test(valor)) return Number(valor);
  const instante = Date.parse(valor);
  return Number.isFinite(instante) ? Math.max(0, Math.ceil((instante - Date.now()) / 1000)) : null;
}

async function enviar(caminho, { metodo = "GET", corpo, token, sinal } = {}) {
  const chave = `${metodo} ${caminho.split("?", 1)[0]}`;
  const restante = Math.ceil(((limites.get(chave) ?? 0) - Date.now()) / 1000);
  const mensagemLimite = "Muitas solicitações. Aguarde antes de tentar novamente.";
  if (restante > 0) throw new ErroApi(mensagemLimite, 429, [], restante);
  limites.delete(chave);

  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let body = corpo;
  if (corpo !== undefined && !(corpo instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(`${base}${caminho}`, {
      method: metodo, headers, body, signal: sinal, cache: "no-store", redirect: "error",
    });
  } catch (erro) {
    if (erro.name === "AbortError") throw erro;
    throw new ErroApi("Não foi possível comunicar com o servidor. Verifique a conexão.");
  }

  if (resposta.status === 204) return null;

  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = dados?.detail;
    const espera = resposta.status === 429 ? segundosRestantes(resposta.headers.get("Retry-After")) : null;
    if (Number.isFinite(espera) && espera > 0) limites.set(chave, Date.now() + espera * 1000);
    const mensagem = resposta.status === 429
      ? mensagemLimite
      : typeof detalhe === "string" && resposta.status < 500
        ? detalhe
        : "Não foi possível concluir a solicitação.";

    throw new ErroApi(mensagem, resposta.status, Array.isArray(detalhe) ? detalhe : [], espera);
  }

  if (dados === null) throw new ErroApi("O servidor retornou uma resposta inesperada.");
  return dados;
}

export function sair(expirada = false) {
  geracao++;
  sessao = null;
  if (expirada) window.dispatchEvent(new Event("sessao-expirada"));
}

export async function entrar(email, senha) {
  const tentativa = ++geracao;
  const tokens = await enviar("/auth/login", {
    metodo: "POST",
    corpo: new URLSearchParams({ username: email, password: senha }),
  });
  const usuario = await enviar("/usuario/me", { token: tokens.access_token });
  if (tentativa === geracao) {
    sessao = { acesso: tokens.access_token, renovacao: tokens.refresh_token, usuario };
  }
}

export function usuarioAtual() {
  return sessao?.usuario;
}

export function atualizarUsuario(usuario) {
  if (sessao?.usuario.id === usuario.id) sessao.usuario = usuario;
}

function renovar(atual) {
  if (!atual.pendente) {
    atual.pendente = enviar("/auth/refresh", {
      metodo: "POST", corpo: { refresh_token: atual.renovacao },
    }).then((tokens) => {
      atual.acesso = tokens.access_token;
    }).catch((erro) => {
      if (sessao === atual && [401, 403, 422].includes(erro.status)) sair(true);
      throw erro;
    }).finally(() => {
      atual.pendente = null;
    });
  }

  return atual.pendente;
}

export async function requisitar(caminho, opcoes = {}) {
  const atual = sessao;
  if (!atual) throw new ErroApi("Entre novamente para continuar.", 401);

  const token = atual.acesso;
  try {
    return await enviar(caminho, { ...opcoes, token });
  } catch (erro) {
    if (erro.status !== 401 || sessao !== atual || opcoes.sinal?.aborted) throw erro;
    if (atual.acesso === token) await renovar(atual);
    if (sessao !== atual) throw erro;

    try {
      return await enviar(caminho, { ...opcoes, token: atual.acesso });
    } catch (falha) {
      if (falha.status === 401 && sessao === atual) sair(true);
      throw falha;
    }
  }
}

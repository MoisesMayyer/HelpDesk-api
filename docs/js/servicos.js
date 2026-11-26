import { requisitar } from "./api.js";

function listar(caminho, consulta, sinal) {
  const busca = new URLSearchParams(consulta ?? undefined).toString();
  return requisitar(busca ? `${caminho}?${busca}` : caminho, { sinal });
}

function gravar(caminho, metodo, corpo) {
  return requisitar(caminho, { metodo, corpo });
}

export const chamados = {
  listar: (consulta, sinal) => listar("/chamados", consulta, sinal),
  criar: (dados) => gravar("/chamados", "POST", dados),
  obter: (id, sinal) => listar(`/chamados/${id}`, null, sinal),
  secao: (id, nome, sinal) => listar(`/chamados/${id}/${nome}`, null, sinal),
  agir: (id, nome, metodo, dados) => gravar(`/chamados/${id}/${nome}`, metodo, dados),
};

export const categorias = {
  listar: (sinal, incluirInativas = false) => listar("/categoria", { incluir_inativas: incluirInativas }, sinal),
  criar: (dados) => gravar("/categoria", "POST", dados),
  editar: (id, dados) => gravar(`/categoria/${id}`, "PUT", dados),
  desativar: (id) => gravar(`/categoria/${id}`, "DELETE"),
};

export const usuarios = {
  listar: (sinal) => listar("/usuario", null, sinal),
  criar: (dados) => gravar("/usuario", "POST", dados),
  editar: (id, dados) => gravar(`/usuario/${id}`, "PUT", dados),
  atualizarConta: (dados) => gravar("/usuario/me", "PUT", dados),
};

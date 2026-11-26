export const perfis = {
  funcionario: "Funcionário",
  tecnico: "Técnico",
  administrador: "Administrador",
};

export function permissoes(usuario, chamado) {
  const tecnico = usuario.tipo === "tecnico";
  const admin = usuario.tipo === "administrador";
  const responsavel = tecnico && chamado.id_tecnico === usuario.id;
  const solicitante = chamado.id_usuario === usuario.id;
  const aberto = chamado.status === "aberto";
  const fechado = chamado.status === "fechado";
  const emAtendimento = chamado.status === "em_andamento";

  return {
    classificar: tecnico && !fechado,
    assumir: tecnico && aberto && chamado.id_tecnico === null,
    aguardar: responsavel && emAtendimento,
    retomar: responsavel && chamado.status === "aguardando_resposta",
    resolver: responsavel && emAtendimento,
    confirmar: solicitante && chamado.status === "resolvido",
    redistribuir: admin && !fechado && chamado.id_tecnico !== null,
    lerComentarios: tecnico || admin,
    comentar: tecnico,
    auditar: admin,
  };
}

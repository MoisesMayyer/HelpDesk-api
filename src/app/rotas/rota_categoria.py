from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dados.dependencies import SessaoDb, UsuarioAtual, exigir_administrador
from app.dados.models.categoria import Categoria
from app.dados.perfis import PerfilUsuario
from app.rotas.validacao import RotaComValidacaoProtegida
from app.schemas.categoria import CategoriaAtualizacao, CategoriaCriacao, CategoriaLeitura

rota_categoria = APIRouter(
    prefix="/categoria", tags=["categoria"], route_class=RotaComValidacaoProtegida
)
SomenteAdmin = [Depends(exigir_administrador)]
CategoriaId = Annotated[int, Path(gt=0, le=2**31 - 1)]


def _buscar_categoria(categoria_id: int, db: Session) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada.")
    return categoria


@rota_categoria.get("", response_model=list[CategoriaLeitura])
def get_categorias(
    db: SessaoDb, usuario: UsuarioAtual, incluir_inativas: bool = False
) -> list[Categoria]:
    consulta = select(Categoria).order_by(Categoria.id)
    if incluir_inativas:
        if usuario.tipo != PerfilUsuario.ADMINISTRADOR:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Operação restrita a administradores."
            )
    else:
        consulta = consulta.where(Categoria.ativo.is_(True))
    return list(db.scalars(consulta))


@rota_categoria.get("/{categoria_id}", response_model=CategoriaLeitura)
def get_categoria(categoria_id: CategoriaId, db: SessaoDb, usuario: UsuarioAtual) -> Categoria:
    categoria = _buscar_categoria(categoria_id, db)
    if not categoria.ativo and usuario.tipo != PerfilUsuario.ADMINISTRADOR:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada.")
    return categoria


@rota_categoria.post(
    "", response_model=CategoriaLeitura, status_code=status.HTTP_201_CREATED,
    dependencies=SomenteAdmin,
)
def post_categoria(dados: CategoriaCriacao, db: SessaoDb) -> Categoria:
    categoria = Categoria(nome=dados.nome)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@rota_categoria.put(
    "/{categoria_id}", response_model=CategoriaLeitura, dependencies=SomenteAdmin
)
def put_categoria(
    categoria_id: CategoriaId, dados: CategoriaAtualizacao, db: SessaoDb
) -> Categoria:
    categoria = _buscar_categoria(categoria_id, db)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria


@rota_categoria.delete(
    "/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=SomenteAdmin
)
def delete_categoria(categoria_id: CategoriaId, db: SessaoDb) -> None:
    categoria = _buscar_categoria(categoria_id, db)
    categoria.ativo = False
    db.commit()

# app/utils/auth_middleware.py
# Middleware de autorização para controle de acesso individualizado
# Sistema Horário Inteligente - Marco

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, Dict
from app.api.auth import get_current_user

class AuthMiddleware:
    """
    Middleware para controle de acesso individualizado
    - Médicos: acesso apenas à própria agenda
    - Secretárias: acesso a todas as agendas
    """

    @staticmethod
    def check_medico_access(
        current_user: dict,
        medico_id: int,
        raise_exception: bool = True
    ) -> bool:
        """
        Verifica se o usuário tem permissão para acessar dados do médico

        Args:
            current_user: Dados do usuário logado (get_current_user)
            medico_id: ID do médico que está sendo acessado
            raise_exception: Se True, lança HTTPException ao negar acesso

        Returns:
            True se tem permissão, False caso contrário

        Raises:
            HTTPException: Se raise_exception=True e acesso negado
        """
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        # Secretárias têm acesso a tudo
        if user_type == "secretaria":
            return True

        # Médicos só acessam seus próprios dados
        if user_type == "medico":
            if user_id == medico_id:
                return True
            else:
                if raise_exception:
                    raise HTTPException(
                        status_code=403,
                        detail="Você não tem permissão para acessar dados deste médico"
                    )
                return False

        # Tipo de usuário desconhecido
        if raise_exception:
            raise HTTPException(
                status_code=403,
                detail="Tipo de usuário inválido"
            )
        return False

    @staticmethod
    def get_medico_filter(current_user: dict) -> Optional[int]:
        """
        Retorna o filtro de médico baseado no tipo de usuário

        Args:
            current_user: Dados do usuário logado

        Returns:
            - None: Se secretária (sem filtro, vê tudo)
            - medico_id: Se médico (filtra apenas seus dados)
        """
        user_type = current_user.get("tipo")
        user_id = current_user.get("id")

        if user_type == "secretaria":
            return None  # Vê todos os médicos
        elif user_type == "medico":
            return user_id  # Vê apenas seus próprios dados
        else:
            raise HTTPException(
                status_code=403,
                detail="Tipo de usuário inválido"
            )

    @staticmethod
    def is_secretaria(current_user: dict) -> bool:
        """Verifica se o usuário é secretária"""
        return current_user.get("tipo") == "secretaria"

    @staticmethod
    def is_medico(current_user: dict) -> bool:
        """Verifica se o usuário é médico"""
        return current_user.get("tipo") == "medico"

    @staticmethod
    def get_user_info(current_user: dict) -> Dict[str, any]:
        """
        Retorna informações estruturadas do usuário

        Returns:
            {
                "id": int,
                "tipo": str,
                "nome": str,
                "email": str,
                "is_secretaria": bool,
                "is_medico": bool,
                "medico_filter": Optional[int]
            }
        """
        return {
            "id": current_user.get("id"),
            "tipo": current_user.get("tipo"),
            "nome": current_user.get("nome"),
            "email": current_user.get("email"),
            "is_secretaria": AuthMiddleware.is_secretaria(current_user),
            "is_medico": AuthMiddleware.is_medico(current_user),
            "medico_filter": AuthMiddleware.get_medico_filter(current_user)
        }


# Função helper para usar como dependency
async def require_medico_access(
    medico_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Dependency para rotas que precisam verificar acesso a médico específico

    Usage:
        @router.get("/medico/{medico_id}/agenda")
        async def get_agenda(
            medico_id: int,
            _: None = Depends(lambda m_id=medico_id: require_medico_access(m_id))
        ):
            # Código da rota
    """
    AuthMiddleware.check_medico_access(current_user, medico_id, raise_exception=True)
    return True


# Função helper para obter filtro de médico
async def get_medico_filter_dependency(
    current_user: dict = Depends(get_current_user)
) -> Optional[int]:
    """
    Dependency que retorna o filtro de médico

    Usage:
        @router.get("/agendamentos")
        async def listar_agendamentos(
            medico_filter: Optional[int] = Depends(get_medico_filter_dependency)
        ):
            # Se medico_filter for None, usuário é secretária (vê tudo)
            # Se medico_filter for um ID, usuário é médico (vê só seus dados)
    """
    return AuthMiddleware.get_medico_filter(current_user)

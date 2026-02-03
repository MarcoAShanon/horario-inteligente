"""
Modelos do Sistema de Agendamento Médico SaaS
Desenvolvido por Marco
"""

from app.models.base import BaseModel, Base

# Models principais (importar primeiro - são dependências)
from app.models.cliente import Cliente

# Models de Planos e Pagamentos (dependem de Cliente)
from app.models.plano import Plano
from app.models.assinatura import Assinatura
from app.models.pagamento import Pagamento
from app.models.medico import Medico
from app.models.paciente import Paciente
from app.models.agendamento import Agendamento
from app.models.convenio import Convenio
from app.models.configuracao import Configuracao

from app.models.calendario import HorarioAtendimento
from app.models.configuracoes import ConfiguracoesMedico, BloqueioAgenda, HorarioEspecial

# Novos models para gestão interna
from app.models.usuario_interno import UsuarioInterno
from app.models.parceiro_comercial import ParceiroComercial
from app.models.cliente_parceiro import ClienteParceiro
from app.models.custo_operacional import CustoOperacional
from app.models.log_auditoria import LogAuditoria
from app.models.pre_cadastro import PreCadastro
from app.models.historico_aceite import HistoricoAceite
from app.models.historico_aceite_parceiro import HistoricoAceiteParceiro
from app.models.historico_inadimplencia import HistoricoInadimplencia
from app.models.comissionamento_parceiro import ComissionamentoParceiro
from app.models.convite_cliente import ConviteCliente

# Models de Conversas WhatsApp
from app.models.conversa import Conversa, StatusConversa, NivelUrgencia
from app.models.mensagem import Mensagem, DirecaoMensagem, RemetenteMensagem, TipoMensagem
from app.models.alerta_urgencia import AlertaUrgencia

# Model de Lembretes Inteligentes
from app.models.lembrete import Lembrete, TipoLembrete, StatusLembrete

# Model de Push Notifications
from app.models.push_subscription import PushSubscription

__all__ = [
    "Base",
    "BaseModel",
    "Cliente",
    "Medico",
    "Paciente",
    "Agendamento",
    "Convenio",
    "Configuracao",
    "HorarioAtendimento",
    "BloqueioAgenda",
    "ConfiguracoesMedico",
    "HorarioEspecial",
    # Novos models
    "UsuarioInterno",
    "ParceiroComercial",
    "ClienteParceiro",
    "CustoOperacional",
    "LogAuditoria",
    # Models de Planos e Assinaturas
    "Plano",
    "Assinatura",
    "Pagamento",
    # Model de Pré-Cadastro
    "PreCadastro",
    # Model de Histórico de Aceites
    "HistoricoAceite",
    "HistoricoAceiteParceiro",
    # Model de Histórico de Inadimplência
    "HistoricoInadimplencia",
    # Model de Comissionamento Parceiro
    "ComissionamentoParceiro",
    # Model de Convites de Clientes
    "ConviteCliente",
    # Models de Conversas WhatsApp
    "Conversa",
    "StatusConversa",
    "NivelUrgencia",
    "Mensagem",
    "DirecaoMensagem",
    "RemetenteMensagem",
    "TipoMensagem",
    "AlertaUrgencia",
    # Model de Lembretes Inteligentes
    "Lembrete",
    "TipoLembrete",
    "StatusLembrete",
    # Model de Push Notifications
    "PushSubscription",
]

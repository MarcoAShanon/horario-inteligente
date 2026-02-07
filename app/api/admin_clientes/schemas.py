"""
Schemas Pydantic para API de Gestão de Clientes - Painel Admin
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import re


class MedicoPrincipalCreate(BaseModel):
    """Dados do médico principal/admin da clínica"""
    nome: str
    especialidade: str
    registro_profissional: str  # CRM, CRO, etc
    email: EmailStr
    telefone: Optional[str] = None

    @validator('nome')
    def nome_valido(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Nome deve ter pelo menos 3 caracteres')
        return v.strip()

    @validator('registro_profissional')
    def registro_valido(cls, v):
        if len(v.strip()) < 4:
            raise ValueError('Registro profissional inválido')
        return v.strip().upper()


class MedicoAdicionalOnboarding(BaseModel):
    """Dados de médico adicional no onboarding"""
    nome: str
    especialidade: str
    registro_profissional: str
    email: EmailStr
    telefone: Optional[str] = None


class SecretariaOnboarding(BaseModel):
    """Dados da secretária no onboarding"""
    nome: str
    email: EmailStr
    telefone: Optional[str] = None


class AssinaturaOnboarding(BaseModel):
    """Dados da assinatura no onboarding"""
    periodo_cobranca: str = "mensal"  # mensal, trimestral, semestral, anual
    percentual_periodo: float = 0  # Desconto pelo período (10%, 15%, 20%)
    linha_dedicada: bool = False  # Se usa linha WhatsApp dedicada (+R$40)
    dia_vencimento: int = 10  # Dia do vencimento: 1, 5 ou 10
    desconto_percentual: Optional[float] = None  # Desconto promocional percentual
    desconto_valor_fixo: Optional[float] = None  # Desconto promocional fixo
    desconto_duracao_meses: Optional[int] = None  # Duração do desconto (null=permanente)
    desconto_motivo: Optional[str] = None  # Motivo do desconto
    ativacao_cortesia: bool = False  # Isentar taxa de ativação (cortesia)


class ClienteCreate(BaseModel):
    """Dados para criar nova clínica"""
    nome_fantasia: str
    razao_social: Optional[str] = None
    documento: str  # CPF ou CNPJ
    email: EmailStr
    telefone: str
    endereco: Optional[str] = None
    plano_id: int = 1  # 1=Individual, 2=Consultório

    # Médico principal (obrigatório)
    medico_principal: MedicoPrincipalCreate

    # Médicos adicionais (opcional, para plano Consultório)
    medicos_adicionais: Optional[List[MedicoAdicionalOnboarding]] = None

    # Secretária (opcional, para plano Consultório)
    secretaria: Optional[SecretariaOnboarding] = None

    # Dados da assinatura (período, descontos, etc)
    assinatura: Optional[AssinaturaOnboarding] = None

    # Parceiro comercial (indicação)
    parceiro_id: Optional[int] = None

    @validator('documento')
    def documento_valido(cls, v):
        # Remove formatação
        doc = re.sub(r'[^0-9]', '', v)
        if len(doc) == 11:  # CPF
            return doc
        elif len(doc) == 14:  # CNPJ
            return doc
        raise ValueError('Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos)')

    @validator('telefone')
    def telefone_valido(cls, v):
        tel = re.sub(r'[^0-9]', '', v)
        if len(tel) < 10 or len(tel) > 11:
            raise ValueError('Telefone inválido')
        return tel


class ClienteUpdate(BaseModel):
    """Dados para editar clínica"""
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


class MedicoAdicionalCreate(BaseModel):
    """Dados para adicionar médico à clínica"""
    nome: str
    especialidade: str
    registro_profissional: str
    email: EmailStr
    telefone: Optional[str] = None
    pode_fazer_login: bool = True
    is_admin: bool = False


class UsuarioCreate(BaseModel):
    """Dados para criar usuário (secretária)"""
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    tipo: str = "secretaria"  # secretaria, admin


class StatusUpdate(BaseModel):
    """Dados para ativar/desativar cliente"""
    ativo: bool
    motivo: Optional[str] = None


class EnviarCredenciaisRequest(BaseModel):
    """Request para enviar credenciais - permite selecionar destinatários"""
    profissional_ids: Optional[List[int]] = None  # Se None, envia para todos


class AprovacaoClienteRequest(BaseModel):
    """Dados para aprovar cliente pendente"""
    plano_id: int
    assinatura: Optional[AssinaturaOnboarding] = None
    medicos_adicionais: Optional[List[MedicoAdicionalOnboarding]] = None
    secretaria: Optional[SecretariaOnboarding] = None
    parceiro_id: Optional[int] = None


class RejeicaoClienteRequest(BaseModel):
    """Dados para rejeitar cliente pendente"""
    motivo: Optional[str] = None
    notificar_email: bool = False


class PlanoUpdate(BaseModel):
    """Dados para atualizar plano do cliente"""
    plano: str  # 'individual', 'clinica', 'profissional'
    valor_mensalidade: str  # ex: "150.00"
    linha_dedicada: bool = False  # Linha WhatsApp dedicada (+R$40)

    @validator('plano')
    def plano_valido(cls, v):
        planos_validos = ('individual', 'clinica', 'profissional')
        if v not in planos_validos:
            raise ValueError(f'Plano deve ser um de: {", ".join(planos_validos)}')
        return v

    @validator('valor_mensalidade')
    def valor_valido(cls, v):
        try:
            valor = float(v.replace(',', '.'))
            if valor < 0:
                raise ValueError('Valor nao pode ser negativo')
            return f"{valor:.2f}"
        except (ValueError, AttributeError):
            raise ValueError('Valor de mensalidade invalido')


class ConfiguracaoWhatsAppUpdate(BaseModel):
    """Schema para atualizar configuracoes do WhatsApp"""
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    whatsapp_display_name: Optional[str] = None
    whatsapp_token: Optional[str] = None
    whatsapp_ativo: Optional[bool] = None


class ConfiguracaoGeralUpdate(BaseModel):
    """Schema para atualizar configuracoes gerais"""
    horario_funcionamento: Optional[dict] = None
    mensagem_boas_vindas: Optional[str] = None
    mensagem_despedida: Optional[str] = None
    timezone: Optional[str] = None
    sistema_ativo: Optional[bool] = None


class TesteWhatsAppRequest(BaseModel):
    """Schema para testar conexao WhatsApp"""
    phone_number_id: str
    access_token: str

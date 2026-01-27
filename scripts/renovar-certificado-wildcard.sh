#!/bin/bash
# =============================================================================
# Script de Renovação do Certificado Wildcard - Horário Inteligente
# =============================================================================
# Este script guia o processo de renovação do certificado SSL wildcard
# para *.horariointeligente.com.br
#
# Uso: sudo ./renovar-certificado-wildcard.sh
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
DOMAIN="horariointeligente.com.br"
CERT_PATH="/etc/letsencrypt/live/horariointeligente.com.br-0001"

echo -e "${BLUE}"
echo "============================================================================="
echo "   RENOVAÇÃO DO CERTIFICADO WILDCARD - HORÁRIO INTELIGENTE"
echo "============================================================================="
echo -e "${NC}"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Este script precisa ser executado como root (sudo)${NC}"
    exit 1
fi

# Mostrar informações do certificado atual
echo -e "${YELLOW}Certificado atual:${NC}"
if [ -f "$CERT_PATH/fullchain.pem" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_PATH/fullchain.pem" | cut -d= -f2)
    echo -e "  Expira em: ${GREEN}$EXPIRY${NC}"

    # Calcular dias restantes
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

    if [ $DAYS_LEFT -gt 30 ]; then
        echo -e "  Dias restantes: ${GREEN}$DAYS_LEFT dias${NC}"
        echo ""
        echo -e "${YELLOW}O certificado ainda tem mais de 30 dias de validade.${NC}"
        read -p "Deseja renovar mesmo assim? (s/N): " CONFIRM
        if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
            echo "Renovação cancelada."
            exit 0
        fi
    else
        echo -e "  Dias restantes: ${RED}$DAYS_LEFT dias${NC}"
    fi
else
    echo -e "${RED}  Certificado não encontrado!${NC}"
fi

echo ""
echo -e "${BLUE}Iniciando processo de renovação...${NC}"
echo ""

# Criar arquivo temporário para capturar os desafios
CHALLENGE_FILE=$(mktemp)
trap "rm -f $CHALLENGE_FILE" EXIT

# Executar certbot e capturar os desafios
echo -e "${YELLOW}Solicitando novos desafios do Let's Encrypt...${NC}"
echo ""

# Usar expect para interagir com certbot
if ! command -v expect &> /dev/null; then
    echo -e "${YELLOW}Instalando expect...${NC}"
    apt-get update && apt-get install -y expect
fi

# Criar script expect
EXPECT_SCRIPT=$(mktemp)
cat > "$EXPECT_SCRIPT" << 'EXPECT_EOF'
#!/usr/bin/expect -f
set timeout 120

spawn certbot certonly --manual --preferred-challenges dns -d "horariointeligente.com.br" -d "*.horariointeligente.com.br" --agree-tos --no-eff-email --force-renewal --cert-name horariointeligente.com.br-0001

set challenge_count 0
set challenges {}

expect {
    "Please deploy a DNS TXT record under the name:" {
        expect -re {with the following value:\s+(\S+)}
        set value $expect_out(1,string)
        lappend challenges $value
        incr challenge_count

        puts "\n\033\[1;33m============================================\033\[0m"
        puts "\033\[1;33m DESAFIO $challenge_count \033\[0m"
        puts "\033\[1;33m============================================\033\[0m"
        puts "\033\[0;36m Adicione este registro TXT no DNS da Hostinger:\033\[0m"
        puts ""
        puts "   Nome:  \033\[1;32m_acme-challenge\033\[0m"
        puts "   Tipo:  \033\[1;32mTXT\033\[0m"
        puts "   Valor: \033\[1;32m$value\033\[0m"
        puts ""

        if {$challenge_count == 1} {
            puts "\033\[1;33mAguardando segundo desafio...\033\[0m\n"
            send "\r"
            exp_continue
        } else {
            puts "\033\[1;33m============================================\033\[0m"
            puts "\033\[1;33m AMBOS OS REGISTROS TXT NECESSARIOS: \033\[0m"
            puts "\033\[1;33m============================================\033\[0m"
            puts ""
            puts "1. _acme-challenge = [lindex $challenges 0]"
            puts "2. _acme-challenge = [lindex $challenges 1]"
            puts ""
            puts "\033\[1;31mIMPORTANTE: Adicione AMBOS os registros TXT!\033\[0m"
            puts ""
            puts "Pressione ENTER quando ambos estiverem configurados..."

            expect_user -re "(.*)\n"

            # Verificar propagação DNS
            puts "\n\033\[0;36mVerificando propagação DNS...\033\[0m"
            set max_attempts 12
            set attempt 0
            set dns_ok 0

            while {$attempt < $max_attempts && $dns_ok == 0} {
                incr attempt
                puts "Tentativa $attempt de $max_attempts..."

                if {[catch {exec dig TXT _acme-challenge.horariointeligente.com.br +short @8.8.8.8} result]} {
                    puts "Erro ao verificar DNS"
                } else {
                    set found_count 0
                    foreach challenge $challenges {
                        if {[string match "*$challenge*" $result]} {
                            incr found_count
                        }
                    }
                    if {$found_count == 2} {
                        set dns_ok 1
                        puts "\033\[1;32mDNS propagado com sucesso!\033\[0m"
                    } else {
                        puts "Encontrados $found_count de 2 registros. Aguardando 10s..."
                        sleep 10
                    }
                }
            }

            if {$dns_ok == 0} {
                puts "\033\[1;33mDNS ainda não propagou completamente, mas vamos tentar...\033\[0m"
            }

            send "\r"
        }
        exp_continue
    }
    "Successfully received certificate" {
        puts "\n\033\[1;32m============================================\033\[0m"
        puts "\033\[1;32m CERTIFICADO RENOVADO COM SUCESSO! \033\[0m"
        puts "\033\[1;32m============================================\033\[0m"
    }
    "Congratulations" {
        puts "\n\033\[1;32mCertificado renovado!\033\[0m"
    }
    "too many certificates" {
        puts "\n\033\[1;31mERRO: Limite de certificados atingido. Aguarde antes de tentar novamente.\033\[0m"
        exit 1
    }
    "Challenge failed" {
        puts "\n\033\[1;31mERRO: Validação do desafio falhou. Verifique os registros DNS.\033\[0m"
        exit 1
    }
    timeout {
        puts "\n\033\[1;31mERRO: Timeout durante a renovação.\033\[0m"
        exit 1
    }
    eof {
        # Fim normal
    }
}
EXPECT_EOF

chmod +x "$EXPECT_SCRIPT"

# Executar o script expect
"$EXPECT_SCRIPT"
RESULT=$?

rm -f "$EXPECT_SCRIPT"

if [ $RESULT -eq 0 ]; then
    echo ""
    echo -e "${BLUE}Recarregando Nginx...${NC}"
    nginx -t && systemctl reload nginx

    echo ""
    echo -e "${GREEN}=============================================================================${NC}"
    echo -e "${GREEN}   RENOVAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
    echo -e "${GREEN}=============================================================================${NC}"
    echo ""
    echo -e "Novo certificado válido até:"
    openssl x509 -enddate -noout -in "$CERT_PATH/fullchain.pem" | cut -d= -f2
    echo ""
    echo -e "${YELLOW}Lembrete: Você pode remover os registros TXT _acme-challenge do DNS.${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}=============================================================================${NC}"
    echo -e "${RED}   ERRO NA RENOVAÇÃO${NC}"
    echo -e "${RED}=============================================================================${NC}"
    echo ""
    echo "Verifique os logs em /var/log/letsencrypt/letsencrypt.log"
    exit 1
fi

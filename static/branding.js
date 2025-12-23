/**
 * Sistema de Branding Dinâmico Multi-Tenant
 * Carrega automaticamente logo, cores e nome do cliente baseado no subdomínio
 * Versão: 1.0.0
 */

// Cache do branding para evitar múltiplas requisições
let brandingCache = null;

/**
 * Carrega os dados de branding do tenant atual
 * @returns {Promise<Object>} Dados de branding
 */
async function carregarBranding() {
    // Retornar cache se já foi carregado
    if (brandingCache) {
        return brandingCache;
    }

    try {
        const response = await fetch('/api/tenant/branding');
        if (response.ok) {
            brandingCache = await response.json();
            return brandingCache;
        } else {
            console.error('Erro ao carregar branding:', response.statusText);
            // Retornar valores padrão
            return {
                nome: 'Horário Inteligente',
                logo_icon: 'fa-heartbeat',
                cor_primaria: '#3b82f6',
                cor_secundaria: '#1e40af'
            };
        }
    } catch (error) {
        console.error('Erro ao carregar branding:', error);
        // Retornar valores padrão
        return {
            nome: 'ProSaúde',
            logo_icon: 'fa-heartbeat',
            cor_primaria: '#3b82f6',
            cor_secundaria: '#1e40af'
        };
    }
}

/**
 * Aplica o branding em elementos específicos da página
 * @param {Object} branding Dados de branding
 */
function aplicarBranding(branding) {
    // Atualizar título da página
    const currentTitle = document.title;
    if (currentTitle.includes('Horário Inteligente')) {
        document.title = currentTitle.replace('Horário Inteligente', branding.nome);
    } else if (currentTitle.includes('-')) {
        // Formato: "Página - Sistema"
        const parts = currentTitle.split('-');
        document.title = `${parts[0]}- ${branding.nome}`;
    } else {
        document.title = `${currentTitle} - ${branding.nome}`;
    }

    // Atualizar elementos com classe 'clinica-nome'
    document.querySelectorAll('.clinica-nome').forEach(el => {
        el.textContent = branding.nome;
    });

    // Atualizar elementos com classe 'logo-icon'
    document.querySelectorAll('.logo-icon').forEach(el => {
        el.className = `fas ${branding.logo_icon} ${el.className.split(' ').slice(2).join(' ')}`;
    });

    // Atualizar elementos com classe 'logo-container'
    document.querySelectorAll('.logo-container').forEach(el => {
        el.style.backgroundColor = branding.cor_primaria;
    });

    // Se tiver logo URL, substituir em elementos com classe 'logo-image'
    if (branding.logo_url) {
        document.querySelectorAll('.logo-image-placeholder').forEach(el => {
            const img = document.createElement('img');
            img.src = branding.logo_url;
            img.alt = branding.nome;
            img.className = el.dataset.imgClass || 'w-full h-full object-contain';
            el.innerHTML = '';
            el.appendChild(img);
        });
    }

    // Atualizar favicon se disponível
    if (branding.favicon_url) {
        const favicon = document.querySelector('link[rel="icon"]') || document.createElement('link');
        favicon.rel = 'icon';
        favicon.href = branding.favicon_url;
        if (!document.querySelector('link[rel="icon"]')) {
            document.head.appendChild(favicon);
        }
    }

    // Aplicar cor primária em botões com classe 'btn-primary-dynamic'
    document.querySelectorAll('.btn-primary-dynamic').forEach(el => {
        el.style.backgroundColor = branding.cor_primaria;
    });

    // Aplicar cor secundária em botões com classe 'btn-secondary-dynamic'
    document.querySelectorAll('.btn-secondary-dynamic').forEach(el => {
        el.style.backgroundColor = branding.cor_secundaria;
    });
}

/**
 * Inicializa o branding automaticamente ao carregar a página
 */
document.addEventListener('DOMContentLoaded', async function() {
    const branding = await carregarBranding();
    aplicarBranding(branding);

    console.log('✅ Branding dinâmico carregado:', branding.nome);
});

// Exportar funções para uso em outras páginas
window.brandingAPI = {
    carregarBranding,
    aplicarBranding,
    getBranding: () => brandingCache
};

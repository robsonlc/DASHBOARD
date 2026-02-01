"""
Web App para Gestão de Negócios Imobiliários
Dashboard da Meta 2030 - Engesud Smart

Uso: python webapp.py
Acesso: http://localhost:8501
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Configuração da página
st.set_page_config(
    page_title="Engesud Smart - Dashboard 2030",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações (usa secrets: NOTION_TOKEN no Streamlit Cloud ou .streamlit/secrets.toml localmente)
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
except:
    # Fallback local - crie um arquivo .streamlit/secrets.toml com NOTION_TOKEN = "seu-token"
    NOTION_TOKEN = ""
    st.warning("⚠️ Token do Notion não encontrado. Configure os secrets para rodar.")

NOTION_VERSION = "2022-06-28"
META_FINANCEIRA = 20000000

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json'
}


@st.cache_data(ttl=300)  # Cache de 5 minutos
def buscar_projetos():
    """Busca todos os projetos da esteira"""
    r = requests.post(
        'https://api.notion.com/v1/databases/d342aea5-0997-4410-b9f9-0ad4524fd596/query',
        headers=HEADERS,
        json={'page_size': 100},
        timeout=20
    )
    return r.json().get('results', [])


@st.cache_data(ttl=300)
def buscar_meta_financeira():
    """Busca valores da Meta Financeira (projetos fechados via rollup)"""
    r = requests.post(
        'https://api.notion.com/v1/databases/2f16d0373889807ba8c8db65ded46e57/query',
        headers=HEADERS,
        json={'page_size': 100},
        timeout=20
    )
    return r.json().get('results', [])


def extrair_valor(props, nome_campo):
    """Extrai valor de diferentes estruturas de campo do Notion (inclui rollups de relations)"""
    campo = props.get(nome_campo, {})
    
    # Estrutura direta (number) - verifica se o valor não é None
    if campo.get('type') == 'number':
        valor = campo.get('number')
        if valor is not None:
            return valor
    
    # Estrutura rollup (pode ser number ou array)
    rollup = campo.get('rollup', {})
    rollup_type = rollup.get('type', '')
    
    # Rollup tipo number
    if rollup_type == 'number':
        valor = rollup.get('number')
        if valor is not None:
            return valor
    
    # Rollup tipo array (soma de relação)
    if rollup_type == 'array':
        array = rollup.get('array', [])
        total = 0
        for item in array:
            # Cada item pode ter 'number' ou ser outro rollup
            if item.get('type') == 'number':
                valor = item.get('number')
                if valor is not None:
                    total += valor
            elif item.get('type') == 'rollup':
                inner_rollup = item.get('rollup', {})
                if inner_rollup.get('type') == 'number':
                    valor = inner_rollup.get('number')
                    if valor is not None:
                        total += valor
        return total
    
    # Fallback: tenta extrair number direto
    valor = campo.get('number')
    if valor is not None:
        return valor
    
    return 0


def extrair_status(props):
    """Extrai status do rollup na Meta Financeira"""
    status_rollup = props.get('Status', {}).get('rollup', {})
    array = status_rollup.get('array', [])
    if array:
        primeiro = array[0]
        if primeiro.get('type') == 'status':
            return primeiro.get('status', {}).get('name', 'Sem status')
    return 'Sem status'


@st.cache_data(ttl=300)
def calcular_metricas(projetos, meta_financeira):
    """Calcula métricas da esteira usando Meta Financeira para valores fechados"""
    total = len(projetos)
    
    por_status = {}
    por_cidade = {}
    valor_total = 0
    fechado_valor = 0
    fechados = 0
    
    # Debug: mostrar estrutura dos campos disponíveis
    # st.write("Meta Financeira items:", len(meta_financeira))
    
    # Mostrar debug info (remover em produção)
    with st.expander("🔍 Debug - Estrutura da Meta Financeira"):
        st.write(f"Total de registros: {len(meta_financeira)}")
        if meta_financeira:
            # Mostra todos os registros com seus valores
            st.write("### Valores extraídos:")
            for i, m in enumerate(meta_financeira):
                props = m.get('properties', {})
                realizado = extrair_valor(props, 'Realizado')
                valor = extrair_valor(props, 'Valor')
                potencial = extrair_valor(props, 'Potencial')
                st.write(f"Registro {i+1}: Realizado={realizado}, Valor={valor}, Potencial={potencial}")
    
    # Calcular valor fechado e potencial da Meta Financeira
    fechado_valor = 0
    potencial_valor = 0
    fechados = 0
    
    for m in meta_financeira:
        props = m.get('properties', {})
        status = extrair_status(props)
        
        # Tenta diferentes nomes de campos de valor
        realizado = extrair_valor(props, 'Realizado')
        valor = extrair_valor(props, 'Valor')
        potencial = extrair_valor(props, 'Potencial')
        
        # Se está Contratado e tem Realizado > 0 → é Fechado
        if status == 'Contratado' and realizado > 0:
            fechado_valor += realizado
            fechados += 1
        # Se tem Potencial preenchido → adiciona ao potencial
        elif potencial > 0:
            potencial_valor += potencial
    
    # Contar projetos da esteira
    for p in projetos:
        props = p.get('properties', {})
        status = props.get('Status', {}).get('status', {}).get('name', 'Sem status')
        cidade = props.get('Cidade', {}).get('select', {}).get('name', 'Não informada')
        valor = props.get('Valor', {}).get('number', 0)
        
        por_status[status] = por_status.get(status, 0) + 1
        por_cidade[cidade] = por_cidade.get(cidade, 0) + 1
        
        # Não soma valor aqui, pois vem da Meta Financeira
        if status != 'Contratado':
            valor_total += valor
    
    # Calcular meta
    ano_atual = datetime.now().year
    anos_restantes = 2030 - ano_atual
    
    return {
        'total': total,
        'por_status': por_status,
        'por_cidade': por_cidade,
        'valor_total': valor_total,
        'fechados': fechados,
        'fechado_valor': fechado_valor,
        'potencial_valor': potencial_valor,
        'restante': META_FINANCEIRA - fechado_valor,
        'anos_restantes': anos_restantes,
        'necessario_por_ano': (META_FINANCEIRA - fechado_valor) / max(anos_restantes, 1)
    }


def main():
    """Página principal"""
    
    # Título com logo
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("https://i.imgur.com/3YKn2xW.png", width=120)
    with col_title:
        st.title("🏢 Engesud Smart - Dashboard 2030")
    st.markdown("---")
    
    # Buscar dados
    with st.spinner('Carregando dados do Notion...'):
        projetos = buscar_projetos()
        meta_financeira = buscar_meta_financeira()
        metricas = calcular_metricas(projetos, meta_financeira)
    
    # Linha 1: Métricas principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Meta 2030",
            f"R$ {META_FINANCEIRA:,.0f}",
            delta="Objetivo"
        )
    
    with col2:
        st.metric(
            "Fechado",
            f"R$ {metricas['fechado_valor']:,.0f}",
            delta=f"{metricas['fechados']} projetos"
        )
    
    with col3:
        st.metric(
            "Potencial Estimado",
            f"R$ {metricas['potencial_valor']:,.0f}",
            delta="Projetos avançados"
        )
    
    st.markdown("---")
    
    # Linha 2: Restante
    col4, col5 = st.columns(2)
    
    with col4:
        st.metric(
            "Restante",
            f"R$ {metricas['restante']:,.0f}",
            delta=f"Meta 2030 - {metricas['anos_restantes']} anos"
        )
    
    st.markdown("---")
    
    # Linha 2: Status e Projetos
    col5, col6 = st.columns([1, 2])
    
    with col5:
        st.subheader("📊 Status da Esteira")
        
        # Gráfico de status
        status_data = pd.DataFrame([
            {'Status': k, 'Quantidade': v} 
            for k, v in metricas['por_status'].items()
        ])
        
        if not status_data.empty:
            st.bar_chart(status_data.set_index('Status'))
        
        # Legenda
        st.markdown("""
        **Legenda:**
        - 🟢 **Entrada**: Primeiro contato
        - 🔵 **Em progresso**: Follow-up ativo
        - 🟣 **Avançado**: Negociação
        - 🟡 **Standby**: Parado
        - 🟢 **Contratado**: Fechado! 🎉
        """)
    
    with col6:
        st.subheader("📋 Projetos Recentes")
        
        # Lista de projetos
        projetos_lista = []
        for p in projetos[:15]:  # Mostrar 15
            props = p.get('properties', {})
            nome = props.get('Negocio', {}).get('title', [{}])[0].get('plain_text', 'Sem nome')
            status = props.get('Status', {}).get('status', {}).get('name', 'Sem status')
            cidade = props.get('Cidade', {}).get('select', {}).get('name', 'Não informada')
            
            if nome != 'Sem nome':
                projetos_lista.append({
                    'Nome': nome[:30] + '...' if len(nome) > 30 else nome,
                    'Status': status,
                    'Cidade': cidade
                })
        
        if projetos_lista:
            df = pd.DataFrame(projetos_lista)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum projeto com nome preenchido ainda.")
    
    st.markdown("---")
    
    # Linha 3: Ações Rápidas
    st.subheader("⚡ Ações Rápidas")
    
    col7, col8, col9, col10 = st.columns(4)
    
    with col7:
        if st.button("📊 Relatório Semanal", use_container_width=True):
            st.success("Gerando relatório...")
    
    with col8:
        if st.button("📈 Análise Kimi K2", use_container_width=True):
            st.info("Use: python -m skills.kimi_ai 'Analise...'")
    
    with col9:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col10:
        if st.button("📱 Ver no Notion", use_container_width=True):
            st.markdown("[Abrir Notion](https://www.notion.so/d342aea509974410b9f90ad4524fd596)")
    
    st.markdown("---")
    
    # Rodapé
    st.markdown(f"""
    ---
    **Dashboard Robson Imóveis** | Meta: R$ 20.000.000 até 2030
    
    Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    
    Desenvolvido com ❤️ e Streamlit
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

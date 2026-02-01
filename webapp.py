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
def calcular_metricas(projetos):
    """Calcula métricas da esteira"""
    total = len(projetos)
    
    por_status = {}
    por_cidade = {}
    valor_total = 0
    fechado_valor = 0
    fechados = 0
    
    for p in projetos:
        props = p.get('properties', {})
        status = props.get('Status', {}).get('status', {}).get('name', 'Sem status')
        cidade = props.get('Cidade', {}).get('select', {}).get('name', 'Não informada')
        valor = props.get('Valor', {}).get('number', 0)
        realizado = props.get('Realizado', {}).get('number', 0)
        
        por_status[status] = por_status.get(status, 0) + 1
        por_cidade[cidade] = por_cidade.get(cidade, 0) + 1
        
        # Se é projeto fechado (Contratado), usa o valor realizado
        if status == 'Contratado':
            fechado_valor += realizado
            fechado_valor += valor  # mantém valor do campo Valor também
            fechados += 1
        else:
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
        metricas = calcular_metricas(projetos)
    
    # Linha 1: Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Meta 2030",
            f"R$ {META_FINANCEIRA:,.0f}",
            delta="Objetivo"
        )
    
    with col2:
        st.metric(
            "Fechado Estimado",
            f"R$ {metricas['fechado_valor']:,.0f}",
            delta=f"{metricas['fechados']} projetos"
        )
    
    with col3:
        st.metric(
            "Restante",
            f"R$ {metricas['restante']:,.0f}",
            delta=f"{metricas['anos_restantes']} anos"
        )
    
    with col4:
        st.metric(
            "Necessário/Ano",
            f"R$ {metricas['necessario_por_ano']:,.0f}",
            delta="~35 fechamentos"
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

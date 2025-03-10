import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
import random  # Para dados de demonstração

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Notícias BABI",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar dados
def load_data():
    """
    Carrega dados de notícias.
    
    Na versão completa, isso se conectaria ao Google Sheets.
    Nesta versão simplificada, usamos dados de demonstração ou um arquivo CSV/JSON local.
    """
    try:
        # Tentar carregar de um arquivo local (CSV ou JSON)
        if os.path.exists("noticias_babi.csv"):
            return pd.read_csv("noticias_babi.csv")
        elif os.path.exists("noticias_babi.json"):
            with open("noticias_babi.json", "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        else:
            # Dados de demonstração se nenhum arquivo for encontrado
            return get_demo_data()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return get_demo_data()

def get_demo_data():
    """Gera dados de demonstração para o dashboard"""
    categorias = ["B1", "B2", "B3", "A1", "A2", "A3", "I1", "I2", "I3"]
    fontes = ["Jornal Nacional", "G1", "CNN", "BBC", "Reuters", "The Guardian", "Folha", "Estadão", "El País"]
    
    dados = []
    for i in range(1, 31):  # 30 dias do mês anterior
        # Gerar entre 1-3 notícias por dia
        for _ in range(random.randint(1, 3)):
            data = f"2024-02-{i:02d}"
            categoria = random.choice(categorias)
            fonte = random.choice(fontes)
            dados.append({
                "data": data,
                "titulo": f"Notícia exemplo sobre {categoria} em {data}",
                "categoria_babi": categoria,
                "fonte": fonte,
                "resumo": f"Este é um resumo de exemplo para demonstrar o dashboard. Categoria: {categoria}, Fonte: {fonte}."
            })
    
    return pd.DataFrame(dados)

# Analisar dados
def analyze_data(df):
    """Extrai análises básicas dos dados"""
    
    # Adicionar categoria principal (primeira letra)
    if 'categoria_babi' in df.columns:
        df['categoria_principal'] = df['categoria_babi'].str[0]
    
    return df

# Interface principal
def main():
    # Título principal
    st.title("📰 Dashboard de Notícias - Método BABI")
    st.write("Análise de notícias categorizadas pelo método BABI (Background, Authoritativeness, Bias, Impact)")
    
    # Barra lateral
    with st.sidebar:
        st.header("Opções")
        
        # Upload de arquivo (alternativa ao Google Sheets)
        uploaded_file = st.file_uploader("Carregar arquivo de dados", type=["csv", "json"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith('.json'):
                    df = pd.DataFrame(json.loads(uploaded_file.getvalue().decode('utf-8')))
                st.session_state['data'] = df
                st.success("Dados carregados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao carregar arquivo: {e}")
        
        # Filtros básicos
        st.subheader("Filtros")
        if 'data' in st.session_state and 'data' in st.session_state['data'].columns:
            min_date = pd.to_datetime(st.session_state['data']['data']).min()
            max_date = pd.to_datetime(st.session_state['data']['data']).max()
            date_range = st.date_input(
                "Intervalo de datas",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
    
    # Carregar ou recarregar dados
    if 'data' not in st.session_state:
        with st.spinner('Carregando dados...'):
            df = load_data()
            df = analyze_data(df)
            st.session_state['data'] = df
    
    # Dados atuais
    df = st.session_state['data']
    
    # Aplicar filtros (se existirem)
    # Implementação de filtros específicos iria aqui
    
    # Layout em abas
    tab1, tab2 = st.tabs(["📊 Visualizações", "📋 Dados Brutos"])
    
    # Aba de visualizações
    with tab1:
        # Linha 1: Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Notícias", len(df))
        
        if 'categoria_principal' in df.columns:
            with col2:
                b_count = df[df['categoria_principal'] == 'B'].shape[0]
                st.metric("Background (B)", b_count)
            
            with col3:
                a_count = df[df['categoria_principal'] == 'A'].shape[0]
                st.metric("Authoritativeness (A)", a_count)
            
            with col4:
                i_count = df[df['categoria_principal'] == 'I'].shape[0]
                st.metric("Impact (I)", i_count)
        
        # Linha 2: Gráficos de categorias
        st.subheader("Distribuição por Categorias")
        col1, col2 = st.columns(2)
        
        with col1:
            if 'categoria_principal' in df.columns:
                categoria_counts = df['categoria_principal'].value_counts()
                fig, ax = plt.subplots()
                ax.pie(
                    categoria_counts, 
                    labels=categoria_counts.index, 
                    autopct='%1.1f%%',
                    colors=['#3B82F6', '#10B981', '#F59E0B']
                )
                ax.set_title('Distribuição por Categoria Principal')
                st.pyplot(fig)
        
        with col2:
            if 'categoria_babi' in df.columns:
                subcategoria_counts = df['categoria_babi'].value_counts().head(10)
                fig, ax = plt.subplots()
                bars = ax.bar(
                    subcategoria_counts.index, 
                    subcategoria_counts.values,
                    color='skyblue'
                )
                ax.set_title('Top 10 Subcategorias')
                ax.set_ylabel('Contagem')
                ax.set_xlabel('Subcategoria')
                plt.xticks(rotation=45)
                st.pyplot(fig)
        
        # Linha 3: Tendências temporais e fontes
        st.subheader("Tendências Temporais e Fontes")
        col1, col2 = st.columns(2)
        
        with col1:
            if 'data' in df.columns and 'categoria_principal' in df.columns:
                try:
                    # Converter para datetime se não for
                    if not pd.api.types.is_datetime64_any_dtype(df['data']):
                        df['data'] = pd.to_datetime(df['data'])
                    
                    # Agrupar por data e contar
                    time_data = df.groupby([pd.Grouper(key='data', freq='D'), 'categoria_principal']).size().unstack().fillna(0)
                    
                    fig, ax = plt.subplots()
                    time_data.plot(ax=ax)
                    ax.set_title('Tendência Temporal por Categoria')
                    ax.set_ylabel('Contagem')
                    ax.set_xlabel('Data')
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
                except Exception as e:
                    st.warning(f"Não foi possível criar gráfico temporal: {e}")
        
        with col2:
            if 'fonte' in df.columns:
                source_counts = df['fonte'].value_counts().head(10)
                fig, ax = plt.subplots()
                bars = ax.barh(
                    source_counts.index, 
                    source_counts.values,
                    color='lightgreen'
                )
                ax.set_title('Top 10 Fontes')
                ax.set_xlabel('Contagem')
                st.pyplot(fig)
        
        # Linha 4: Notícias recentes
        st.subheader("Notícias Recentes")
        try:
            if 'data' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['data']):
                    df['data'] = pd.to_datetime(df['data'])
                
                recent_news = df.sort_values(by='data', ascending=False).head(5)
                for _, row in recent_news.iterrows():
                    st.markdown(f"""
                    **{row.get('titulo', 'Sem título')}** - *{row.get('fonte', 'Sem fonte')}*  
                    Categoria: {row.get('categoria_babi', 'N/A')}  
                    {row.get('resumo', 'Sem resumo')}
                    """)
                    st.divider()
        except Exception as e:
            st.warning(f"Não foi possível mostrar notícias recentes: {e}")
    
    # Aba de dados brutos
    with tab2:
        st.subheader("Dados Completos")
        st.dataframe(df, use_container_width=True)
        
        # Opção para download dos dados
        csv = df.to_csv(index=False)
        st.download_button(
            "Download dos Dados (CSV)",
            csv,
            "noticias_babi.csv",
            "text/csv",
            key='download-csv'
        )

# Executar o aplicativo
if __name__ == "__main__":
    main()

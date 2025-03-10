import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import nltk
from nltk.corpus import stopwords
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import openai
from datetime import datetime, timedelta
import re

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Notícias BABI",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de autenticação e API
@st.cache_resource
def load_credentials():
    """Carrega credenciais para Google Sheets e OpenAI"""
    # Google Sheets API
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # Configure seu arquivo de credenciais aqui
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)
    
    # OpenAI API (opcional, configure sua chave)
    if 'OPENAI_API_KEY' not in st.session_state:
        st.session_state['OPENAI_API_KEY'] = ''
    
    return client

# Função para carregar dados do Google Sheets
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_news_data(spreadsheet_id, sheet_name):
    """Carrega dados de notícias da planilha Google Sheets"""
    try:
        client = load_credentials()
        sheet = client.open_by_key(spreadsheet_id)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        # Dados de exemplo em caso de falha
        return pd.DataFrame({
            'data': [datetime.now().strftime("%Y-%m-%d")] * 10,
            'titulo': [f"Título de notícia exemplo {i}" for i in range(1, 11)],
            'fonte': ['Fonte A', 'Fonte B', 'Fonte C', 'Fonte A', 'Fonte B', 
                      'Fonte C', 'Fonte A', 'Fonte B', 'Fonte C', 'Fonte A'],
            'categoria_babi': ['B1', 'A2', 'B3', 'I2', 'A1', 'B2', 'I1', 'A3', 'B1', 'I3'],
            'resumo': [f"Resumo da notícia exemplo {i}" for i in range(1, 11)],
            'link': [f"https://example.com/news/{i}" for i in range(1, 11)],
        })

# Funções para analisar dados de notícias
def analyze_categories(df):
    """Analisa categorias BABI nas notícias"""
    # Extrai as categorias principais (B, A, B, I)
    if 'categoria_babi' in df.columns:
        df['categoria_principal'] = df['categoria_babi'].str[0]
        
        # Contagem por categoria principal
        categoria_counts = df['categoria_principal'].value_counts().reset_index()
        categoria_counts.columns = ['Categoria', 'Contagem']
        
        # Contagem de subcategorias
        subcategoria_counts = df['categoria_babi'].value_counts().reset_index()
        subcategoria_counts.columns = ['Subcategoria', 'Contagem']
        
        return categoria_counts, subcategoria_counts
    return None, None

def analyze_sources(df):
    """Analisa fontes de notícias"""
    if 'fonte' in df.columns:
        source_counts = df['fonte'].value_counts().reset_index()
        source_counts.columns = ['Fonte', 'Contagem']
        return source_counts
    return None

def analyze_time_trends(df):
    """Analisa tendências temporais nas notícias"""
    if 'data' in df.columns:
        try:
            # Converter para datetime se não for
            if not pd.api.types.is_datetime64_any_dtype(df['data']):
                df['data'] = pd.to_datetime(df['data'])
            
            # Agrupar por data e categoria
            time_trend = df.groupby([pd.Grouper(key='data', freq='D'), 'categoria_principal']).size().reset_index()
            time_trend.columns = ['Data', 'Categoria', 'Contagem']
            return time_trend
        except:
            st.warning("Não foi possível analisar tendências temporais. Verifique o formato de data.")
    return None

def create_wordcloud(df, column='titulo'):
    """Cria uma nuvem de palavras a partir do texto"""
    if column in df.columns:
        try:
            # Baixa stopwords se necessário
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords')
            
            # Combina todos os textos
            all_text = ' '.join(df[column].astype(str))
            
            # Remove stopwords
            stop_words = set(stopwords.words('portuguese'))
            words = [word.lower() for word in re.findall(r'\b\w+\b', all_text) 
                     if word.lower() not in stop_words]
            
            # Cria wordcloud
            wordcloud = WordCloud(width=800, height=400, 
                                  background_color='white', 
                                  max_words=100).generate(' '.join(words))
            return wordcloud
        except Exception as e:
            st.warning(f"Não foi possível criar a nuvem de palavras: {e}")
    return None

# Função para o chat de IA
def get_ai_response(prompt, context, api_key):
    """Obtém resposta da IA baseada no contexto dos dados"""
    try:
        if not api_key:
            return "Por favor, configure sua chave de API nas configurações."
        
        openai.api_key = api_key
        
        system_prompt = """
        Você é um assistente especializado em analisar dados de notícias categorizadas pelo método BABI.
        O método BABI categoriza notícias em:
        - B (Background): Contexto e antecedentes
        - A (Authoritativeness): Credibilidade da fonte
        - B (Bias): Viés e inclinação
        - I (Impact): Impacto e relevância

        Cada categoria tem subcategorias numeradas (ex: B1, A2, etc.).
        Analise os dados e responda às perguntas do usuário de forma objetiva.
        """
        
        full_prompt = f"Contexto dos dados:\n{context}\n\nPergunta: {prompt}"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro ao comunicar com a API: {e}"

# Interface principal
def main():
    # Carregando CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .user-message {
        background-color: #E5E7EB;
    }
    .ai-message {
        background-color: #DBEAFE;
    }
    </style>
    """, unsafe_allow_html=True)

    # Título principal
    st.markdown('<div class="main-header">📰 Dashboard de Notícias - Método BABI</div>', unsafe_allow_html=True)

    # Barra lateral para configurações
    with st.sidebar:
        st.header("Configurações")
        
        # ID da planilha e nome da aba
        spreadsheet_id = st.text_input("ID da Planilha do Google", "1ABCDEFGhijklmno123456789")
        sheet_name = st.text_input("Nome da Aba", "Noticias")
        
        # Botão para atualizar dados
        if st.button("Carregar Dados"):
            st.session_state['refresh_data'] = True
        
        st.divider()
        
        # Filtros (datas, categorias, fontes)
        st.subheader("Filtros")
        
        # Configurações da OpenAI API
        st.divider()
        st.subheader("Configurações de IA")
        api_key = st.text_input("OpenAI API Key", st.session_state.get('OPENAI_API_KEY', ''), type="password")
        if api_key:
            st.session_state['OPENAI_API_KEY'] = api_key
    
    # Verifica se precisa atualizar os dados
    if 'data' not in st.session_state or st.session_state.get('refresh_data', False):
        with st.spinner('Carregando dados...'):
            st.session_state['data'] = load_news_data(spreadsheet_id, sheet_name)
            if 'refresh_data' in st.session_state:
                st.session_state['refresh_data'] = False
    
    # Dataframe principal
    df = st.session_state['data']
    
    # Análises dos dados
    categoria_counts, subcategoria_counts = analyze_categories(df)
    source_counts = analyze_sources(df)
    time_trend = analyze_time_trends(df)
    wordcloud = create_wordcloud(df)
    
    # Layout em abas
    tab1, tab2 = st.tabs(["📊 Visualizações", "💬 Chat com IA"])
    
    # Aba de visualizações
    with tab1:
        # Primeira linha - Métricas principais
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
        
        # Segunda linha - Gráficos de categorias e subcategorias
        st.markdown('<div class="subheader">Distribuição por Categorias</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if categoria_counts is not None:
                fig = px.pie(
                    categoria_counts, 
                    values='Contagem', 
                    names='Categoria', 
                    title='Distribuição por Categoria Principal',
                    color='Categoria',
                    color_discrete_map={'B': '#3B82F6', 'A': '#10B981', 'I': '#F59E0B'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if subcategoria_counts is not None:
                fig = px.bar(
                    subcategoria_counts, 
                    y='Contagem', 
                    x='Subcategoria', 
                    title='Distribuição por Subcategoria',
                    color='Subcategoria'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Terceira linha - Tendências temporais e fontes
        st.markdown('<div class="subheader">Tendências Temporais e Fontes</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if time_trend is not None:
                fig = px.line(
                    time_trend, 
                    x='Data', 
                    y='Contagem', 
                    color='Categoria',
                    title='Tendências Temporais por Categoria'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if source_counts is not None:
                fig = px.bar(
                    source_counts, 
                    y='Contagem', 
                    x='Fonte', 
                    title='Distribuição por Fonte',
                    color='Fonte'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Quarta linha - Nuvem de palavras e dados recentes
        st.markdown('<div class="subheader">Análise de Conteúdo</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Nuvem de Palavras dos Títulos")
            if wordcloud is not None:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
        
        with col2:
            st.subheader("Notícias Recentes")
            try:
                recent_news = df.sort_values(by='data', ascending=False).head(5)
                for _, row in recent_news.iterrows():
                    st.markdown(f"""
                    **{row.get('titulo', 'Sem título')}** - *{row.get('fonte', 'Sem fonte')}*  
                    Categoria: {row.get('categoria_babi', 'N/A')}  
                    {row.get('resumo', 'Sem resumo')}
                    """)
                    st.divider()
            except:
                st.write("Não foi possível mostrar notícias recentes.")
        
        # Quinta linha - Tabela completa de dados
        st.markdown('<div class="subheader">Tabela Completa de Dados</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
    
    # Aba de chat com IA
    with tab2:
        # Inicializa histórico de chat se não existir
        if 'chat_history' not in st.session_state:
            st.session_state['chat_history'] = []
        
        # Exibe histórico de chat
        for message in st.session_state['chat_history']:
            if message['role'] == 'user':
                st.markdown(f'<div class="chat-message user-message">👤 Você: {message["content"]}</div>', 
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message ai-message">🤖 Assistente: {message["content"]}</div>', 
                            unsafe_allow_html=True)
        
        # Preparar resumo de contexto para o modelo
        context = f"""
        Total de notícias: {len(df)}
        Distribuição por categorias principais: {df['categoria_principal'].value_counts().to_dict() if 'categoria_principal' in df.columns else 'N/A'}
        Fontes principais: {df['fonte'].value_counts().head(5).to_dict() if 'fonte' in df.columns else 'N/A'}
        """
        
        # Input para mensagem do usuário
        user_input = st.text_input("Faça uma pergunta sobre os dados de notícias:")
        
        if user_input:
            # Adiciona mensagem do usuário ao histórico
            st.session_state['chat_history'].append({"role": "user", "content": user_input})
            
            # Obtém resposta da IA
            with st.spinner('O assistente está pensando...'):
                ai_response = get_ai_response(user_input, context, st.session_state.get('OPENAI_API_KEY', ''))
            
            # Adiciona resposta da IA ao histórico
            st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})
            
            # Recarrega a página para mostrar a nova mensagem
            st.experimental_rerun()

if __name__ == "__main__":
    main()

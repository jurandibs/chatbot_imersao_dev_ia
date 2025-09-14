# app.py
import streamlit as st
import requests
import json
import os
import time  

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="ERP Assist - Assistente de Suporte",
    page_icon="🤖",
    layout="wide"
)

# --- ESTILO CSS CUSTOMIZADO---
st.markdown("""
<style>
    /* Suporte ao modo dark/light do sistema */
    :root {
        color-scheme: light dark;
    }
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #1a202c; /* Fundo escuro */
        }
        .st-emotion-cache-ch5dnh {
            background-color: #2d3748; /* Bolha do usuário em dark */
            border: 1px solid #4a5568;
            color: #e2e8f0; /* Texto claro */
        }
        .st-emotion-cache-4oy321 {
            background-color: #2d3748; /* Bolha do assistente em dark */
            border: 1px solid #4a5568;
            color: #e2e8f0; /* Texto claro */
        }
        section[data-testid="stSidebar"] {
            background-color: #1a202c; /* Sidebar em dark */
            border-right: 1px solid #4a5568;
        }
        .stTextInput > div > div > input {
            background-color: #2d3748;
            color: #e2e8f0;
            border: 1px solid #4a5568;
        }
        .stButton > button {
            background-color: #4a5568;
            color: #e2e8f0;
        }
        /* Ajuste para imagens */
        img {
            filter: brightness(1.2); /* Aumenta o brilho das imagens no modo dark para melhor visibilidade */
        }
    }
    @media (prefers-color-scheme: light) {
        .stApp {
            background-color: #f9fafb; /* Fundo claro */
        }
        .st-emotion-cache-ch5dnh {
            background-color: #e0f2fe; /* Bolha do usuário em light */
            border: 1px solid #bae6fd;
            color: #1f2937; /* Texto escuro */
        }
        .st-emotion-cache-4oy321 {
            background-color: #f3f4f6; /* Bolha do assistente em light */
            border: 1px solid #d1d5db;
            color: #1f2937; /* Texto escuro */
        }
        section[data-testid="stSidebar"] {
            background-color: #ffffff; /* Sidebar em light */
            border-right: 1px solid #e5e7eb;
        }
        .stTextInput > div > div > input {
            background-color: #ffffff;
            color: #1f2937;
            border: 1px solid #d1d5db;
        }
        .stButton > button {
            background-color: #e2e8f0;
            color: #1f2937;
        }
    }
    /* Estilos gerais */
    .st-emotion-cache-1v0mbdj > img {
        border-radius: 50%;
    }
    /* Expander para citações */
    .st-expander {
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
    /* Botões e inputs */
    .stButton > button {
        border-radius: 8px;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #4a5568;
    }
    .st-emotion-cache-ch5dnh, .st-emotion-cache-4oy321 {
        max-width: 80%;
    }
    .st-emotion-cache-ch5dnh {
        margin-left: auto;
    }
    .st-emotion-cache-4oy321 {
        margin-right: auto;
    }
    /* Ajuste para placeholders de imagem */
    .stImage > img {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ENDPOINTS DA API ---
API_BASE_URL = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/analyze_image"

# --- SIDEBAR PARA UPLOADER E CONTROLES ---
with st.sidebar:
    st.subheader("Analisar um Print de Tela")
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    
    uploaded_file = st.file_uploader(
        "Envie uma imagem (PNG, JPG)",
        type=['png', 'jpg', 'jpeg'],
        key=str(st.session_state.uploader_key),
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="Pré-visualização da imagem a ser analisada.")
    
    st.divider()
    if st.button("Limpar Conversa", key="clear_chat"):
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()

# --- INTERFACE DO CHAT ( em largura total para melhor usabilidade) ---
st.title("🤖 Assistente de Suporte ")
st.caption("Olá! Sou uma IA de assistência virtual para o seu ERP. Como posso ajudar hoje? Envie uma mensagem ou anexe uma imagem para análise.")

# Container para o histórico de mensagens com scroll
chat_container = st.container(height=500)

# Inicializa o histórico do chat na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with chat_container.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        # Exibe o prompt/imagem que o usuário enviou
        if "prompt" in message:
            st.markdown(message["prompt"])
        if "image" in message:
            st.image(message["image"], caption="Você enviou:", use_container_width=False, width=400)
        
        # Exibe a resposta do assistente
        if "content" in message:
            st.markdown(message["content"])
        if "imagens_resposta" in message and message["imagens_resposta"]:
            st.markdown("**Imagens relevantes da documentação:**")
            # Garante que o número de colunas seja ajustado dinamicamente e seguro
            num_images = len(message["imagens_resposta"])
            num_cols = min(num_images, 3)  # Limita a 3 colunas por linha
            cols = st.columns(num_cols)
            for i, img_url in enumerate(message["imagens_resposta"]):
                if img_url:  # Verifica se a URL não está vazia
                    cols[i % num_cols].image(img_url, use_container_width=True, output_format="PNG")
                else:
                    st.warning("URL de imagem inválida ou ausente.")
        
        # Mostra as citações de texto
        if "citacoes" in message and message["citacoes"]:
            with st.expander("Ver referências de texto"):
                for c in message["citacoes"]:
                    st.info(f"**📄 Documento:** `{c['documento']}` (Página: {c['pagina']})\n\n> _{c['trecho']}_")

# Captura a entrada do usuário (caixa de texto no final da página)
prompt = st.chat_input("Digite sua dúvida ou descreva a imagem...")

if prompt:
    image_bytes = None
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
    
    # Se uma imagem foi enviada, o prompt é para análise de imagem
    if image_bytes:
        # Adiciona a mensagem do usuário (com imagem) ao histórico
        user_message = {"role": "user", "prompt": prompt, "image": image_bytes}
        st.session_state.messages.append(user_message)
        
        with chat_container.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)
            st.image(image_bytes, caption="Você enviou:", use_container_width=False, width=400)
            
        with chat_container.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando a imagem..."):
                files = {'image_file': (uploaded_file.name, image_bytes, uploaded_file.type)}
                response = requests.post(ANALYZE_ENDPOINT, data={'pergunta': prompt}, files=files)
                
                if response.status_code == 200:
                    analise = response.json().get("analise", "Não foi possível analisar a imagem.")
                    st.markdown(analise)
                    assistant_message = {"role": "assistant", "content": analise}
                    st.session_state.messages.append(assistant_message)
                else:
                    st.error(f"Erro na análise: {response.text}")

    # Se não houver imagem, é um chat normal (RAG)
    else:
        # Adiciona a mensagem do usuário ao histórico
        user_message = {"role": "user", "prompt": prompt}
        st.session_state.messages.append(user_message)
        with chat_container.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        with chat_container.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando sua dúvida..."):
                response = requests.post(CHAT_ENDPOINT, json={"pergunta": prompt})

                if response.status_code == 200:
                    data = response.json()
                    resposta = data.get("resposta", "Desculpe, ocorreu um erro.")
                    citacoes = data.get("citacoes", [])
                    imagens_rag = [f"{API_BASE_URL}{p}" for p in data.get("imagens", [])]
                    
                    st.markdown(resposta)
                    if imagens_rag:
                        st.markdown("**Imagens relevantes da documentação:**")
                        num_cols = min(len(imagens_rag), 3)
                        cols = st.columns(num_cols)
                        for i, img_url in enumerate(imagens_rag):
                            if img_url:  # Verifica se a URL não está vazia
                                cols[i % num_cols].image(img_url, use_container_width=True, output_format="PNG")
                            else:
                                st.warning("URL de imagem inválida ou ausente.")
                    
                    if citacoes:
                        with st.expander("Ver referências de texto"):
                            for c in citacoes:
                                st.info(f"**📄 Documento:** `{c['documento']}` (Página: {c['pagina']})\n\n> _{c['trecho']}_")

                    assistant_message = {"role": "assistant", "content": resposta, "citacoes": citacoes, "imagens_resposta": imagens_rag}
                    st.session_state.messages.append(assistant_message)
                else:
                    st.error(f"Erro no chat: {response.text}")
    
    # Reseta o uploader e força reload para atualizar a interface
    st.session_state.uploader_key += 1
    st.rerun()
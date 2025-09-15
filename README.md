
# Chatbot de Suporte com Gemini API
#Criei este projeto com base na participação da Imersão Dev Agentes de IA Google da Alura.

## 📖 Descrição

Este projeto é uma plataforma de chatbot personalizada desenvolvida com a API do Gemini. 

Este chatbot foi desenvolvido para a 2ª Edição da Imersão de Inteligência Artificial da Alura em parceria com o Google.

## ✨ Funcionalidades

  * **Chatbot personalizado para utilização atendimentos de suporte em ERPs de diversos seguimentos.
  * **Aprendizagem Estruturada:** O conteúdo é apresentado de forma organizada para facilitar a compreensão e a retenção do conhecimento.
  * **Analise tanto textual quanto por imagem.
  * Feedback textual, por prints e refência dos documentos utilizados da base de conhecimento.

## 🚀 Tecnologias Utilizadas

  * **Google Gemini API:** Utilizada para a geração dos conteúdos de estudo.
  * **Python:** Linguagem de programação principal do projeto.
  * Streamlit: Biblioteca frontend
  * 

## ⚙️ Instalação e Uso

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/jurandibs/chatbot_imersao_dev_ia.git
    ```

2.  **Instale as dependências:**

pip install "fastapi[all]" streamlit requests python-dotenv
pip install langchain langchain-google-genai google-generativeai faiss-cpu langchain-text-splitters pymupdf langgraph

3.  **Configure sua API Key:**

      * Renomeie o arquivo `.env.example` para `.env`.
      * Abra o arquivo `.env` e adicione a sua API Key do Google Gemini:
        ```
        GEMINI_API_KEY="SUA_API_KEY_AQUI"
        ```

4.  **Execute o chatbot:**

    ```bash #Este script lerá os PDFs da pasta data/, os processará e salvará o índice FAISS na pasta vector_store/
    python create_vector_store.py    
    ```
    ```bash   # na pasta /chatbot_imersao_dev_ia execute este comando para rodar o backend no http://127.0.0.1:8000
    uvicorn main:app --reload   
    ```
    ```bash  # Comando para executar o frontend
    streamlit run app.py   
    ```            
  

## 🤝 Como Contribuir

Contribuições são bem-vindas\! Se você tiver ideias para novas funcionalidades, melhorias ou correções de bugs, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.

1.  Faça um *fork* deste repositório.
2.  Crie uma nova *branch* (`git checkout -b feature/sua-feature`).
3.  Faça o *commit* das suas alterações (`git commit -m 'Adiciona nova feature'`).
4.  Envie para a sua *branch* (`git push origin feature/sua-feature`).
5.  Abra um *Pull Request*.

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](https://www.google.com/search?q=LICENSE) para mais detalhes.

## Prints do Chatbot em Execução

<img src="https://raw.githubusercontent.com/jurandibs/chatbot_imersao_dev_ia/refs/heads/main/chatbot1.png">

<img src="https://raw.githubusercontent.com/jurandibs/chatbot_imersao_dev_ia/refs/heads/main/chatbot2.png">

-----

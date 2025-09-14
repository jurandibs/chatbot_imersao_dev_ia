# main.py
import os
import re
import base64
import pathlib
import tempfile
from typing import List, Dict, Optional, Literal
from dotenv import load_dotenv
from pathlib import Path 

# FastAPI e Pydantic
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# LangChain e Google GenAI
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_KEY')


# Validação da chave de API
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_KEY não encontrada. Por favor, configure no arquivo .env")

# Definir caminhos usando Path para consistência
VECTOR_STORE_PATH = Path("./vector_store/")
IMAGE_SAVE_DIR = Path("imagens_documentos") # Definido corretamente como objeto Path

#CRIAR a instância do FastAPI 
app = FastAPI(
    title="Help Desk Chatbot API - Multimodal",
    description="API para interação com o chatbot de suporte, com capacidade de análise e resposta visual.",
    version="2.0.0"
)


# Isso cria um endpoint /static/images/... que o frontend pode acessar
app.mount("/static/images", StaticFiles(directory=str(IMAGE_SAVE_DIR)), name="static_images")

# --- LÓGICA DO CHATBOT ---

# 1. Modelos LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    api_key=GOOGLE_API_KEY
)

# 2. Carregar Vector Store e Retriever
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GOOGLE_API_KEY
)
vectorstore = FAISS.load_local(str(VECTOR_STORE_PATH), embeddings, allow_dangerous_deserialization=True)
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.4, "k": 4}
)


# 3. Definição de Prompts e Chains
TRIAGEM_PROMPT = (
    "Você é um triador de Help Desk para suporte de software da empresa Hope. "
    "Dada a mensagem do usuário, retorne SOMENTE um JSON com:\n"
    "{\n"
    '  "decisao": "AUTO_RESOLVER" | "PEDIR_INFO" | "ABRIR_CHAMADO",\n'
    '  "urgencia": "BAIXA" | "MEDIA" | "ALTA",\n'
    '  "campos_faltantes": ["..."]\n'
    "}\n"
    "Regras:\n"
    '- **AUTO_RESOLVER**: Perguntas claras sobre regras ou procedimentos descritos nos manuais (Ex: "Como faço para importar uma nota fiscal?", "Como faço para cadastrar uma empresa?").\n'
    '- **PEDIR_INFO**: Mensagens vagas ou que faltam informações para identificar o tema ou contexto (Ex: "Preciso de ajuda no fiscal", "Tenho uma dúvida geral").\n'
    '- **ABRIR_CHAMADO**: Pedidos de acesso remoto, reincidencia de erro ou solicitações não identificadas, ou quando o usuário explicitamente pede para abrir um chamado (Ex: "Meu erro continua.", "Solicito acesso.", "Por favor, abra um chamado.").'
    "Analise a mensagem e decida a ação mais apropriada."
)

prompt_rag = ChatPromptTemplate.from_messages([
    ("system",
     "Você é um Analista de Suporte da ERP Contábil de uma empresa. "
     "Responda SOMENTE com base no contexto fornecido. "
     "Se não houver base suficiente, responda apenas 'Não sei, melhor abrir um chamado'."),
    ("human", "Pergunta: {input}\n\nContexto:\n{context}")
])

document_chain = create_stuff_documents_chain(llm, prompt_rag)

# 4. Funções e Classes de Suporte (Pydantic, Formatadores)
class TriagemOut(BaseModel):
    decisao: Literal["AUTO_RESOLVER", "PEDIR_INFO", "ABRIR_CHAMADO"]
    urgencia: Literal["BAIXA", "MEDIA", "ALTA"]
    campos_faltantes: List[str] = Field(default_factory=list)

triagem_chain = llm.with_structured_output(TriagemOut)

def triagem(mensagem: str) -> Dict:
    saida: TriagemOut = triagem_chain.invoke([
        SystemMessage(content=TRIAGEM_PROMPT),
        HumanMessage(content=mensagem)
    ])
    return saida.model_dump()

def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def extrair_trecho(texto: str, query: str, janela: int = 240) -> str:
    txt = _clean_text(texto)
    termos = [t.lower() for t in re.findall(r"\w+", query or "") if len(t) >= 4]
    pos = -1
    for t in termos:
        pos = txt.lower().find(t)
        if pos != -1: break
    if pos == -1: pos = 0
    ini, fim = max(0, pos - janela//2), min(len(txt), pos + janela//2)
    return "..." + txt[ini:fim] + "..."

def encode_image(image_path):
    """Converte um arquivo de imagem para string base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analisar_mensagem_com_imagem(mensagem: str, image_path: str):
    if not Path(image_path).exists():
        return "Erro: O caminho da imagem não foi encontrado."

    base64_image = encode_image(image_path)
    image_mime_type = f"image/{pathlib.Path(image_path).suffix[1:]}"

    human_message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": f"""
                    Analise a seguinte imagem e a mensagem do usuário.
                    A imagem é um print de tela do nosso sistema ERP.
                    Descreva o que você vê na imagem, identifique possíveis erros ou campos importantes, e explique qual pode ser o problema do usuário com base na mensagem dele.

                    Mensagem do usuário: '{mensagem}'
                """
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime_type};base64,{base64_image}"
                }
            }
        ]
    )
    response = llm.invoke([human_message])
    return response.content

def formatar_citacoes_e_imagens(docs_rel: List, query: str) -> Dict:
    cites, seen, imagens_relacionadas = [], set(), []
    for d in docs_rel:
        src = pathlib.Path(d.metadata.get("source","")).stem
        page = int(d.metadata.get("page", 0)) + 1
        key = (src, page)

        # Adiciona a citação de texto se ainda não foi vista
        if key not in seen:
            seen.add(key)
            cites.append({
                "documento": f"{src}.pdf",
                "pagina": page,
                "trecho": extrair_trecho(d.page_content, query)
            })

            # Procura por imagens correspondentes a este documento e página
            for img_path in IMAGE_SAVE_DIR.glob(f"{src}_page{page}_*.png"):
                imagens_relacionadas.append(str(img_path))

    return {
        "citacoes": cites[:3],
        "imagens": list(set(imagens_relacionadas)) # Remove duplicatas
    }

def perguntar_politica_RAG(pergunta: str) -> Dict:
    docs_relacionados = retriever.invoke(pergunta)

    if not docs_relacionados:
        return {"answer": "Não sei, melhor abrir um chamado.",
                "citacoes": [],
                "imagens": [],
                "contexto_encontrado": False}

    answer = document_chain.invoke({
        "input": pergunta,
        "context": docs_relacionados
    })

    txt = (answer or "").strip()

    if txt.rstrip(".!?") == "Não sei, melhor abrir um chamado":
        return {"answer": "Não sei, melhor abrir um chamado.",
                "citacoes": [],
                "imagens": [],
                "contexto_encontrado": False}

    # Formata as citações e busca as imagens relacionadas
    info_adicional = formatar_citacoes_e_imagens(docs_relacionados, pergunta)

    return {"answer": txt,
            "citacoes": info_adicional["citacoes"],
            "imagens": info_adicional["imagens"],
            "contexto_encontrado": True}


# 5. Lógica do Grafo (LangGraph)

# --- MODELO DE ESTADO ---
# Renomeei 'triagem_result' para 'triagem' para ficar mais limpo e consistente
class AgenteState(BaseModel):
    pergunta: str
    triagem: Optional[Dict] = None
    resposta: Optional[str] = None
    citacoes: Optional[List[Dict]] = []
    imagens: Optional[List[str]] = [] # NOVO: para guardar as URLs das imagens
    rag_sucesso: bool = False
    acao_final: Optional[str] = None

# --- NÓS DO GRAFO ---

def node_triagem(state: AgenteState) -> dict: # ALTERADO: type hint para AgenteState
    # ALTERADO: state["pergunta"] para state.pergunta
    return {"triagem": triagem(state.pergunta)} 

# MODIFICADO: Nó de auto_resolver para capturar e formatar os caminhos das imagens
def node_auto_resolver(state: AgenteState) -> dict:
    resposta_rag = perguntar_politica_RAG(state.pergunta)
    
    # NOVO: Converte os caminhos locais em URLs acessíveis pelo frontend
    imagens_urls = [f"/static/images/{pathlib.Path(p).name}" for p in resposta_rag.get("imagens", [])]
    
    update = {
        "resposta": resposta_rag["answer"],
        "citacoes": resposta_rag.get("citacoes", []),
        "imagens": imagens_urls, # Adiciona as URLs ao estado
        "rag_sucesso": resposta_rag["contexto_encontrado"],
    }
    if resposta_rag["contexto_encontrado"]:
        update["acao_final"] = "AUTO_RESOLVER"
    return update

def node_pedir_info(state: AgenteState) -> dict: # ALTERADO: type hint para AgenteState
    # ALTERADO: state["triagem"] para state.triagem
    faltantes = state.triagem.get("campos_faltantes", [])
    detalhe = ", ".join(faltantes) if faltantes else "mais detalhes sobre sua dúvida"
    return {"resposta": f'Para que eu possa ajudar melhor, por favor, forneça {detalhe}.', "citacoes": [], "acao_final": "PEDIR_INFO"}

def node_abrir_chamado(state: AgenteState) -> dict: # ALTERADO: type hint para AgenteState
    # ALTERADO: state["triagem"] para state.triagem e state['pergunta'] para state.pergunta
    triagem_data = state.triagem
    return {
        "resposta": f"Entendido. Estou abrindo um chamado para você com urgência '{triagem_data['urgencia']}'. Em breve um analista entrará em contato. Descrição: {state.pergunta[:140]}",
        "citacoes": [],
        "acao_final": "ABRIR_CHAMADO"
    }

# --- ARESTAS CONDICIONAIS ---

def decidir_pos_triagem(state: AgenteState) -> str: # ALTERADO: type hint para AgenteState
    # ALTERADO: state["triagem"]["decisao"] para state.triagem["decisao"]
    return state.triagem["decisao"].lower()

def decidir_pos_auto_resolver(state: AgenteState) -> str: # ALTERADO: type hint para AgenteState
    # ALTERADO: state.get("rag_sucesso") para state.rag_sucesso
    return 'end' if state.rag_sucesso else 'abrir_chamado'

workflow = StateGraph(AgenteState)
workflow.add_node('triagem', node_triagem)
workflow.add_node('auto_resolver', node_auto_resolver)
workflow.add_node('pedir_info', node_pedir_info)
workflow.add_node('abrir_chamado', node_abrir_chamado)

workflow.add_edge(START, 'triagem')
workflow.add_conditional_edges('triagem', decidir_pos_triagem, {
    'auto_resolver': 'auto_resolver',
    'pedir_info': 'pedir_info',
    'abrir_chamado': 'abrir_chamado'
})
workflow.add_conditional_edges('auto_resolver', decidir_pos_auto_resolver, {
    'end': END,
    'abrir_chamado': 'abrir_chamado'
})
workflow.add_edge('pedir_info', END)
workflow.add_edge('abrir_chamado', END)

grafo = workflow.compile()


# --- API Endpoints ---
class ChatRequest(BaseModel):
    pergunta: str

@app.post("/chat", response_model=AgenteState)
def chat_endpoint(request: ChatRequest):
    inputs = {"pergunta": request.pergunta}
    resposta_final = grafo.invoke(inputs)
    return resposta_final

class AnaliseResponse(BaseModel):
    analise: str

@app.post("/analyze_image", response_model=AnaliseResponse)
async def analyze_image_endpoint(pergunta: str = Form(...), image_file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=pathlib.Path(image_file.filename).suffix) as tmp:
        tmp.write(await image_file.read())
        tmp_path = tmp.name
    
    try:
        analise_texto = analisar_mensagem_com_imagem(pergunta, tmp_path)
        return {"analise": analise_texto}
    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
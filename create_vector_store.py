# create_vector_store.py
import os
import fitz  # PyMuPDF
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Carrega a chave de API do arquivo .env
load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_KEY não encontrada. Por favor, configure no arquivo .env")

# --- CAMINHOS ---
DATA_PATH = Path("./data/")
VECTOR_STORE_PATH = Path("./vector_store/")
IMAGE_SAVE_DIR = Path("./imagens_documentos/") # Pasta para salvar imagens extraídas

# Cria os diretórios se não existirem
VECTOR_STORE_PATH.mkdir(exist_ok=True)
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

def create_store_and_extract_images():
    print("Iniciando processo de preparação...")
    docs = []

    for pdf_path in DATA_PATH.glob("*.pdf"):
        try:
            # 1. Carrega o texto usando LangChain
            loader = PyMuPDFLoader(str(pdf_path))
            docs.extend(loader.load())

            # 2. Extrai e salva as imagens usando PyMuPDF (fitz)
            doc_fitz = fitz.open(pdf_path)
            for page_num, page in enumerate(doc_fitz):
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc_fitz.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Nome de arquivo único para cada imagem
                    image_filename = f"{pdf_path.stem}_page{page_num+1}_img{img_index}.png"
                    image_save_path = IMAGE_SAVE_DIR / image_filename

                    with open(image_save_path, "wb") as image_file:
                        image_file.write(image_bytes)

            print(f"✔️ Arquivo '{pdf_path.name}' processado (texto e imagens).")
        except Exception as e:
            print(f"❌ Erro ao processar o arquivo {pdf_path.name}: {e}")

    if not docs:
        print("⚠️ Nenhum documento foi carregado. Verifique a pasta 'data'.")
        return

    print(f"\nTotal de páginas de texto carregadas: {len(docs)}")

    # 3. Cria e salva o Vector Store (mesma lógica de antes)
    print("Dividindo documentos em chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    chunks = splitter.split_documents(docs)
    
    print("Gerando embeddings e criando o vector store FAISS...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(VECTOR_STORE_PATH))
    print(f"✅ Vector store criado e salvo com sucesso em '{VECTOR_STORE_PATH}'!")

if __name__ == "__main__":
    create_store_and_extract_images()
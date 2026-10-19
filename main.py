import sys
import os
import glob
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from DrissionPage import ChromiumPage, ChromiumOptions
import uvicorn
import time

# Variável global do navegador
page = None

# Define a pasta atual como o local padrão para transferências (downloads)
PASTA_DOWNLOADS = os.path.dirname(os.path.abspath(__file__))

class BuscarRequest(BaseModel):
    texto: str
    tipo: str = "texto"  # Adicionado para diferenciar: "texto" ou "imagem"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global page
    
    print("A iniciar o Chrome no modo Indetetável (DrissionPage)...")
    co = ChromiumOptions().auto_port()
    # Adicione estas 3 linhas cruciais para o Docker:
    co.set_argument('--headless=new') 
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    
    co.set_argument('--start-maximized')
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    page = ChromiumPage(co)
    
    print("A aceder ao site alvo...")
    page.get("https://detetiveforense.com")
    
    try:
        # 1. PREENCHE LOGIN
        page.ele('@name=username', timeout=10).input('Davidrochaadv')
        page.ele('@name=password').input('102030')
        page.ele('@type=submit').click()
        
        print("Botão Entrar clicado! A aguardar o ecrã do PIN...")
        time.sleep(3) 
        
        # 2. PREENCHE PIN
        seu_pin = "223731" 
        print(f"A digitar o PIN no teclado virtual...")
        for numero in seu_pin:
            botao_numero = page.ele(f'text={numero}')
            if botao_numero:
                botao_numero.click()
                time.sleep(0.2)
        
        # Clica em entrar no PIN
        botoes_entrar = page.eles('text=Entrar')
        if botoes_entrar:
            botao_pin = botoes_entrar[-1]
            botao_pin.wait.clickable(timeout=10)
            botao_pin.click()
            print("PIN confirmado! A aguardar o painel principal...")
        
        time.sleep(8) 
        print("Painel principal carregado e a aguardar requisições na API.")
        
    except Exception as e:
        print(f"Aviso no login ou PIN: {e}")

    yield
    
    if page:
        page.quit()

app = FastAPI(lifespan=lifespan)

@app.post("/buscar")
def fazer_busca(req: BuscarRequest):
    global page
    if not page:
        raise HTTPException(status_code=503, detail="O navegador ainda não iniciou.")
    
    try:
        print(f"Recebida requisição (Tipo: {req.tipo})! A preparar o módulo Investigador OSINT...")
        
        # PASSO 1: Clicar em "Módulos"
        menu_modulos = page.ele('text=Módulos', timeout=5)
        if menu_modulos:
            menu_modulos.click()
            time.sleep(3)
        else:
            page.get("https://detetiveforense.com/app/modulos")
            time.sleep(3)
        
        # PASSO 2: Clicar no cartão do Investigador OSINT
        card_investigador = page.ele('text=Investigador OSINT', timeout=5)
        if not card_investigador:
            card_investigador = page.ele('css:a[href*="investigador-osint"]', timeout=3)

        if card_investigador:
            card_investigador.click()
            print("Entrou no painel Investigador OSINT. A aguardar o ecrã...")
        else:
            return JSONResponse(status_code=400, content={"status": "erro", "mensagem": "Cartão do Investigador não encontrado."})
        
        time.sleep(5)
        
        # ====================================================================
        # PASSO 3: BIFURCAÇÃO DE FLUXO (TEXTO OU IMAGEM)
        # ====================================================================
        if req.tipo.lower() == "imagem":
            print("Fluxo de IMAGEM detetado. A procurar o separador 'Foto'...")
            
            separador_foto = page.ele('xpath://button[@role="tab" and contains(., "Foto")]', timeout=5)
            if separador_foto:
                separador_foto.click()
                time.sleep(2) 
                
                campo_upload = page.ele('xpath://input[@type="file"]', timeout=5)
                if campo_upload:
                    campo_upload.input(req.texto)
                    print(f"Ficheiro de imagem '{req.texto}' anexado com sucesso!")
                else:
                    return JSONResponse(status_code=400, content={"status": "erro", "mensagem": "Campo de upload não encontrado."})
            else:
                return JSONResponse(status_code=400, content={"status": "erro", "mensagem": "Separador 'Foto' não encontrado no ecrã."})

        else:
            print("Fluxo de TEXTO detetado. A procurar o campo CPF/Placa...")
            campo_cpf = page.ele('xpath://span[text()="CPF"]/ancestor::div[1]/input', timeout=5)
            if campo_cpf:
                campo_cpf.clear()
                campo_cpf.input(req.texto)
                print(f"Dado '{req.texto}' preenchido!")
            else:
                return JSONResponse(status_code=400, content={"status": "erro", "mensagem": "Campo de texto não encontrado no ecrã."})
            
        # ====================================================================
        # PASSO 4: PESQUISAR E EXPORTAR 
        # ====================================================================
        botao_pesquisar = page.ele('xpath://button[contains(., "Pesquisar")]', timeout=3)
        if botao_pesquisar:
            botao_pesquisar.click()
            print("Botão Pesquisar clicado! A aguardar os resultados (12 segundos)...")
            time.sleep(12)
            
            print("A procurar botão 'Exportar PDF'...")
            botao_exportar = page.ele('xpath://button[contains(text(), "Exportar PDF")]', timeout=5)
            
            if botao_exportar:
                botao_exportar.click()
                print("A aguardar 5 segundos para a transferência (download) concluir...")
                time.sleep(5)
            else:
                print("AVISO: Botão 'Exportar PDF' não encontrado.")
                return JSONResponse(status_code=404, content={"status": "erro", "mensagem": "Botão Exportar PDF não encontrado."})
            
            botao_fechar = page.ele('xpath://button[contains(., "Fechar") or contains(., "Voltar")]', timeout=3)
            if botao_fechar:
                botao_fechar.click()
                time.sleep(1)
            
            # ====================================================================
            # PASSO 5: ENCONTRAR O PDF E DEVOLVER COMO RESPOSTA BINÁRIA
            # ====================================================================
            arquivos_pdf = glob.glob(os.path.join(PASTA_DOWNLOADS, '*.pdf'))
            
            if not arquivos_pdf:
                return JSONResponse(status_code=404, content={"status": "erro", "mensagem": "Nenhum ficheiro PDF foi encontrado após a transferência."})
            
            # Pega o ficheiro PDF mais recente criado na pasta
            pdf_mais_recente = max(arquivos_pdf, key=os.path.getctime)
            print(f"Sucesso! A devolver o ficheiro: {pdf_mais_recente}")
            
            # Retorna o ficheiro fisicamente para o n8n
            return FileResponse(
                path=pdf_mais_recente,
                media_type="application/pdf",
                filename="resultado_osint.pdf"
            )
            
        else:
            return JSONResponse(status_code=400, content={"status": "erro", "mensagem": "Botão Pesquisar não encontrado."})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("A iniciar o servidor API na porta 8000...")
    # O host 0.0.0.0 é obrigatório para que a API seja acessível fora do contentor Docker no EasyPanel
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Usa uma imagem oficial do Python, versão leve
FROM python:3.11-slim

# Instalar dependências do sistema e o Google Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho dentro do contentor
WORKDIR /app

# Copia e instala as bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os restantes ficheiros do projeto (incluindo o main_4.py)
COPY . .

# Expõe a porta onde o FastAPI vai rodar
EXPOSE 8000

# Comando para iniciar a API
CMD ["uvicorn", "main_4:app", "--host", "0.0.0.0", "--port", "8000"]
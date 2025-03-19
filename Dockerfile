# 1️⃣ Usar uma imagem mínima do Python
FROM python:3.10-slim

# 2️⃣ Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3️⃣ Copiar arquivos do projeto para o contêiner
COPY . /app

# 4️⃣ Instalar as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# 5️⃣ Excluir cache do Streamlit (opcional, para evitar arquivos desnecessários)
RUN rm -rf ~/.streamlit/

# 6️⃣ Expor a porta padrão do Streamlit
EXPOSE 8501

# 7️⃣ Definir o comando para rodar o aplicativo dentro do contêiner
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

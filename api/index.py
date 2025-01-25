import os
from flask import Flask, render_template, request, redirect, url_for, session
import bcrypt
from werkzeug.utils import secure_filename
import psycopg2
from flask import jsonify
from supabase import create_client
import logging
from datetime import datetime


# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL_FILE", "https://riqzhrzpoxhubexqeqkz.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpcXpocnpwb3hodWJleHFlcWt6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY0MzEyNjMsImV4cCI6MjA1MjAwNzI2M30.fkxfzhLRZyMtACZaHBfCuVG-Sp_wxd8cos9JytUcd64")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Exemplo de conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "defaultsecretkey")  # Define um valor padrão para evitar erros

def get_db_connection():
    """Retorna uma conexão ao banco de dados Supabase."""
    return psycopg2.connect(DATABASE_URL)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY  # Garante que o SECRET_KEY seja configurado corretamente

# Configurações do upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Verifica se o arquivo possui uma extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    # Conexão com o banco
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtém os parâmetros do filtro
    preco = request.args.get('preco', '')
    localizacao = request.args.get('localizacao', '')
    tipo = request.args.get('tipo', '')

    # Criação da query SQL com as condições dinâmicas
    query = "SELECT id, nome, descricao, latitude, longitude, fotos, preco, tipo_imovel FROM apartamentos WHERE 1=1"
    params = []

    # Filtro de preço
    if preco == 'baixo':
        query += " AND preco < 500"
    elif preco == 'medio':
        query += " AND preco BETWEEN 500 AND 1000"
    elif preco == 'alto':
        query += " AND preco > 1000"

    # Filtro de localização
    if localizacao:
        query += " AND (bairro LIKE %s OR cidade LIKE %s)"
        params.extend([f"%{localizacao}%", f"%{localizacao}%"])

    # Filtro de tipo de imóvel
    if tipo:
        query += " AND tipo_imovel = %s"
        params.append(tipo)

    # Executa a consulta
    cursor.execute(query, params)
    apartamentos = cursor.fetchall()
    conn.close()

    # Formata os apartamentos
    apartamentos_formatados = [
        {
            "id": ap[0],
            "nome": ap[1],
            "descricao": ap[2],
            "latitude": ap[3],
            "longitude": ap[4],
            "fotos": ap[5].split(',') if ap[5] else [],
            "preco": ap[6],
            "tipo": ap[7]
        }
        for ap in apartamentos
    ]

    return render_template('index.html', apartamentos=apartamentos_formatados)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        if not email or not senha:
            return "Por favor, preencha todos os campos.", 400
        # Conexão com o banco
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Consulta o usuário pelo email
            cursor.execute("SELECT id, senha, tipo FROM usuarios WHERE email = %s", (email,))
            user = cursor.fetchone()  # Retorna um dicionário ou None

        # Verifica se o usuário foi encontrado
        if user is None:
            return "Usuário não encontrado", 404

        # Verifica a senha
        hashed_password = user[1]
        if bcrypt.checkpw(senha.encode('utf-8'), hashed_password.encode('utf-8')):
            session['user_id'] = user[0]  # Armazena o user_id na sessão
            session['user_type'] = user[2]  # Armazena o tipo de usuário
            return redirect(url_for('index'))
        else:
            return "Senha inválida", 401

        conn.close()
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if 'user_id' not in session or session['user_type'] != 'dono':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            nome = request.form['nome']
            preco = request.form['preco']
            tipo_imovel = request.form['tipo']
            descricao = request.form['descricao']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            file_paths = request.form.get('filePaths', '')  # Pega os caminhos das fotos ou vazio
            user_id = session['user_id']

            # Validações
            if not nome or not descricao or not latitude or not longitude:
                return "Todos os campos são obrigatórios.", 400
            
            # Converte valores numéricos
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except ValueError:
                return "Latitude e longitude devem ser números.", 400

            # Conexão com o banco
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO apartamentos(nome, descricao, latitude, longitude, user_id, fotos, preco, tipo_imovel) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, descricao, latitude, longitude, user_id, file_paths, preco, tipo_imovel))
            conn.commit()
            cursor.close()

            return redirect(url_for('index'))
        except Exception as e:
            return f"Erro ao processar o formulário: {e}", 400

    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    # Remove o user_id da sessão para deslogar o usuário
    session.pop('user_id', None)
    session.pop('user_type', None)
    return redirect(url_for('index'))

@app.route('/meus_apartamentos', methods=['GET'])
def meus_apartamentos():
    if 'user_id' not in session or session['user_type'] != 'dono':
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Conexão com o banco
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome, descricao, latitude, longitude, fotos, preco, tipo_imovel FROM apartamentos WHERE user_id = %s", [user_id])
    apartamentos = cursor.fetchall()
    conn.close()

    apartamentos_formatados = [
        {
            "id": ap[0],
            "nome": ap[1],
            "descricao": ap[2],
            "latitude": ap[3],
            "longitude": ap[4],
            "fotos": ap[5].split(',') if ap[5] else [],
            "preco": ap[6],
            "tipo": ap[7]
        } 
        for ap in apartamentos
    ]

    return render_template('meus_apartamentos.html', apartamentos=apartamentos_formatados)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']

        # Hash da senha (convertido para string)
        hashed_password = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Conexão com o banco
        conn = get_db_connection()
        cursor = conn.cursor()  

        cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (%s, %s, %s, %s)", 
                       (nome, email, hashed_password, tipo))
        conn.commit()
        cursor.close()

        return redirect(url_for('login'))
    return render_template('registro.html')


@app.route('/apartamento/<int:id>', methods=['GET'])
def apartamento(id):
    # Conexão com o banco
    conn = get_db_connection()
    cursor = conn.cursor() 

    # Consulta o banco de dados
    cursor.execute("SELECT nome, descricao, latitude, longitude, fotos, preco, tipo_imovel FROM apartamentos WHERE id = %s", [id])
    apartamento = cursor.fetchone()
    conn.close()

    if apartamento:
        apartamento_formatado = {
            "nome": apartamento[0],
            "descricao": apartamento[1],
            "latitude": apartamento[2],
            "longitude": apartamento[3],
            "fotos": apartamento[4].split(',') if apartamento[4] else [],
            "preco": apartamento[5],
            "tipo": apartamento[6],
            "id": id
        }
        return render_template('apartamento.html', apartamento=apartamento_formatado)
    else:
        return "Apartamento não encontrado", 404


@app.route('/apartamento/editar/<int:id>', methods=['GET', 'POST'])
def editar_apartamento(id):
    if 'user_id' not in session or session['user_type'] != 'dono':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Busca os dados do apartamento
    cursor.execute("""
        SELECT nome, descricao, latitude, longitude, fotos, preco, tipo_imovel
        FROM apartamentos 
        WHERE id = %s
    """, [id])
    apartamento = cursor.fetchone()

    if not apartamento:
        conn.close()
        return "Apartamento não encontrado", 404

    # Mapeia os dados do apartamento para um dicionário
    imovel = {
        'nome': apartamento[0],
        'descricao': apartamento[1],
        'latitude': apartamento[2],
        'longitude': apartamento[3],
        'fotos': apartamento[4],
        'preco': apartamento[5],
        'tipo': apartamento[6]
    }

    if request.method == 'POST':
        try:
            # Recebe os dados do formulário
            nome = request.form.get('nome', '').strip()
            descricao = request.form.get('descricao', '').strip()
            latitude = request.form.get('latitude', '').strip()
            longitude = request.form.get('longitude', '').strip()
            preco = request.form.get('preco', '').strip()
            tipo_imovel = request.form.get('tipo', '').strip()
            file_paths = request.form.get('filePaths', '').strip()

            # Valida os campos obrigatórios
            if not nome or not descricao or not latitude or not longitude:
                return "Todos os campos obrigatórios devem ser preenchidos.", 400

            # Converte valores numéricos
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                preco = float(preco)
            except ValueError:
                return "Latitude, longitude, preço devem ser valores válidos.", 400

            # Atualiza os dados do apartamento no banco
            cursor.execute("""
                UPDATE apartamentos 
                SET nome = %s, descricao = %s, latitude = %s, longitude = %s, preco = %s, tipo_imovel = %s, fotos = %s
                WHERE id = %s
            """, (nome, descricao, latitude, longitude, preco, tipo_imovel, file_paths, id))
            conn.commit()

            return redirect(url_for('apartamento', id=id))
        except Exception as e:
            return f"Erro ao atualizar o imóvel: {e}", 500
        finally:
            conn.close()

    conn.close()
    return render_template('editar_apartamento.html', imovel=imovel)

def upload_to_supabase(bucket_name, file_path, file_data):
    """
    Faz upload de um arquivo para o Supabase Storage.
    
    :param bucket_name: Nome do bucket no Supabase
    :param file_path: Caminho onde o arquivo será salvo (ex: 'imagens/meuarquivo.jpg')
    :param file_data: Dados do arquivo (em bytes)
    :return: URL pública do arquivo ou erro
    """
    try:
        # Faz o upload do arquivo
        response = supabase.storage.from_(bucket_name).upload(file_path, file_data)
        
        # Adiciona um log para ver o conteúdo de 'response'
        print(f"Response do upload: {response}")  # Imprime no terminal
        logging.info(f"Response do upload: {response}")  # Loga a resposta
        return {"success": True, "url": response}
       
    except Exception as e:
        print(f"Erro na função de upload: {str(e)}")  # Imprime qualquer exceção
        return {"success": False, "error": str(e)}


@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['user_type'] != 'dono':
        return jsonify({"error": "Usuário não autorizado"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if file and allowed_file(file.filename):
        try:
            # Nome único com data e hora
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{timestamp}_{secure_filename(file.filename)}"

            # Define o caminho do arquivo no bucket
            filename = secure_filename(unique_filename)
            file_path = f"uploads/{filename}"

            # Faz o upload diretamente para o Supabase
            result = upload_to_supabase("apartamentos", file_path, file.read())

            if result["success"]:
                return jsonify({"file_url": result["url"]}), 200
            else:
                return jsonify({"error": result["error"]}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Arquivo não permitido"}), 400


if __name__ == '__main__':
    app.run(debug=True)
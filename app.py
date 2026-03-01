from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key"

# =============================
# CONEXÃO POSTGRESQL
# =============================
DATABASE_URL = os.environ.get("DATABASE_URL")
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

cursor = conn.cursor()

# =============================
# CRIAR TABELAS
# =============================
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario TEXT UNIQUE,
    senha TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS servicos (
    id SERIAL PRIMARY KEY,
    cliente TEXT,
    veiculo TEXT,
    servico TEXT,
    data TEXT,
    valor REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS agendamentos (
    id SERIAL PRIMARY KEY,
    cliente TEXT,
    veiculo TEXT,
    servico TEXT,
    data DATE,
    hora TIME,
    valor REAL,
    status TEXT DEFAULT 'Agendado'
)
""")

conn.commit()

# =============================
# REGISTRAR USUÁRIO
# =============================
@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        senha_hash = generate_password_hash(senha)

        cursor.execute("""
            INSERT INTO usuarios (usuario, senha)
            VALUES (%s, %s)
            ON CONFLICT (usuario) DO NOTHING
        """, (usuario, senha_hash))

        conn.commit()

        return """
        Usuário criado com sucesso! <br><br>
        <a href="/login">Ir para Login</a>
        """

    return """
    <h2>Criar Usuário</h2>
    <form method="POST">
        Usuário: <input name="usuario" required><br><br>
        Senha: <input type="password" name="senha" required><br><br>
        <button type="submit">Criar</button>
    </form>
    """
# =============================
# login
# =============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        cursor.execute("""
            SELECT id, usuario, senha
            FROM usuarios
            WHERE usuario = %s
        """, (usuario,))

        user = cursor.fetchone()

        if user and check_password_hash(user[2], senha):
            session["logado"] = True
            session["usuario"] = usuario
            return redirect("/")
        else:
            return """
            Login inválido! <br><br>
            <a href="/login">Tentar novamente</a>
            """

    return """
    <h2>Login</h2>
    <form method="POST">
        Usuário: <input name="usuario" required><br><br>
        Senha: <input type="password" name="senha" required><br><br>
        <button type="submit">Entrar</button>
    </form>
    """
# =============================
# client
# =============================
@app.route("/")
def index():
    if "logado" not in session:
        return redirect("/login")

    cursor.execute("SELECT * FROM servicos ORDER BY id DESC")
    servicos = cursor.fetchall()

    cursor.execute("SELECT SUM(valor) FROM servicos")
    faturamento = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT cliente, COUNT(*) 
        FROM servicos
        GROUP BY cliente
        ORDER BY COUNT(*) DESC
    """)
    ranking = cursor.fetchall()

    return render_template("index.html",
                           servicos=servicos,
                           faturamento=faturamento,
                           ranking=ranking)

# =============================
# AGENDAR
# =============================
@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if "logado" not in session:
        return redirect("/login")

    if request.method == "POST":
        cliente = request.form["cliente"]
        veiculo = request.form["veiculo"]
        servico = request.form["servico"]
        data = request.form["data"]
        hora = request.form["hora"]
        valor = float(request.form["valor"])

        cursor.execute("""
            INSERT INTO agendamentos
            (cliente, veiculo, servico, data, hora, valor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (cliente, veiculo, servico, data, hora, valor))

        conn.commit()
        return redirect("/agenda")

    return render_template("agendar.html")

# =============================
# AGENDA VISUAL
# =============================
@app.route("/agenda")
def agenda():
    if "logado" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT * FROM agendamentos
        ORDER BY data, hora
    """)
    agendamentos = cursor.fetchall()

    return render_template("agenda.html",
                           agendamentos=agendamentos)

# =============================
# CONCLUIR SERVIÇO
# =============================
@app.route("/concluir/<int:id>")
def concluir(id):
    if "logado" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT cliente, veiculo, servico, valor
        FROM agendamentos
        WHERE id = %s
    """, (id,))
    dados = cursor.fetchone()

    if dados:
        cliente, veiculo, servico, valor = dados

        data = datetime.now().strftime("%d/%m/%Y")

        # vira faturamento automático
        cursor.execute("""
            INSERT INTO servicos
            (cliente, veiculo, servico, data, valor)
            VALUES (%s, %s, %s, %s, %s)
        """, (cliente, veiculo, servico, data, valor))

        cursor.execute("""
            UPDATE agendamentos
            SET status = 'Concluído'
            WHERE id = %s
        """, (id,))

        conn.commit()

    return redirect("/agenda")

if __name__ == "__main__":
    app.run(debug=True)
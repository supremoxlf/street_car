from flask import Flask, render_template, request, redirect
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)

# =============================
# CONEXÃO POSTGRESQL (RENDER)
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
# HOME
# =============================
@app.route("/")
def index():
    cursor.execute("SELECT * FROM servicos ORDER BY id DESC")
    servicos = cursor.fetchall()

    cursor.execute("SELECT SUM(valor) FROM servicos")
    faturamento = cursor.fetchone()[0] or 0

    return render_template("index.html",
                           servicos=servicos,
                           faturamento=faturamento)

# =============================
# AGENDAR
# =============================
@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if request.method == "POST":
        cliente = request.form["cliente"]
        veiculo = request.form["veiculo"]
        servico = request.form["servico"]
        valor = float(request.form["valor"])
        data = request.form["data"]
        hora = request.form["hora"]

        cursor.execute("""
            INSERT INTO agendamentos
            (cliente, veiculo, servico, data, hora, valor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (cliente, veiculo, servico, data, hora, valor))

        conn.commit()
        return redirect("/agenda")

    return render_template("agendar.html")

# =============================
# AGENDA (FULLCALENDAR)
# =============================
@app.route("/agenda")
def agenda():
    cursor.execute("""
        SELECT id, cliente, servico, data, hora, status
        FROM agendamentos
    """)
    dados = cursor.fetchall()

    eventos = []

    for d in dados:
        eventos.append({
            "id": d[0],
            "title": f"{d[1]} - {d[2]}",
            "start": f"{d[3]}T{d[4]}",
            "color": "green" if d[5] == "Concluído" else "orange"
        })

    return render_template("agenda.html", eventos=eventos)

# =============================
# CONCLUIR SERVIÇO
# =============================
@app.route("/concluir/<int:id>")
def concluir(id):
    cursor.execute("""
        SELECT cliente, veiculo, servico, valor
        FROM agendamentos
        WHERE id = %s
    """, (id,))
    dados = cursor.fetchone()

    if dados:
        cliente, veiculo, servico, valor = dados
        data = datetime.now().strftime("%d/%m/%Y")

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
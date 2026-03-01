from flask import Flask, render_template, request, redirect
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)

# =============================
# FUNÇÃO DE CONEXÃO (ESTÁVEL)
# =============================
def get_connection():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    url = urlparse(DATABASE_URL)

    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

# =============================
# CRIAR TABELAS (1 VEZ)
# =============================
conn = get_connection()
cursor = conn.cursor()

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
cursor.close()
conn.close()

# =============================
# HOME
# =============================
@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        cliente = request.form.get("cliente")
        veiculo = request.form.get("veiculo")
        servico = request.form.get("servico")
        valor = request.form.get("valor")

        if not valor:
            valor = 0

        data = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
            INSERT INTO servicos
            (cliente, veiculo, servico, data, valor)
            VALUES (%s, %s, %s, %s, %s)
        """, (cliente, veiculo, servico, data, float(valor)))

        conn.commit()

    # 🔥 CONSULTA CORRETA COM TOTAL DO CLIENTE
    cursor.execute("""
        SELECT s.id, s.cliente, s.veiculo, s.servico, s.data, s.valor,
        (SELECT COUNT(*) FROM servicos WHERE cliente = s.cliente)
        FROM servicos s
        ORDER BY s.id DESC
    """)

    servicos = cursor.fetchall()

    cursor.execute("SELECT COALESCE(SUM(valor),0) FROM servicos")
    faturamento = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template("index.html",
                           servicos=servicos,
                           faturamento=faturamento)

    # BUSCAR SERVIÇOS
    cursor.execute("""
                   SELECT s.*,
                          (SELECT COUNT(*) FROM servicos WHERE cliente = s.cliente) as total_cliente
                   FROM servicos s
                   ORDER BY id DESC
                   """)
    servicos = cursor.fetchall()
@app.route("/faturamento")
def faturamento():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM servicos ORDER BY id DESC")
    servicos = cursor.fetchall()

    cursor.execute("SELECT COALESCE(SUM(valor),0) FROM servicos")
    total = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template("faturamento.html",
                           servicos=servicos,
                           total=total)
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

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agendamentos
            (cliente, veiculo, servico, data, hora, valor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (cliente, veiculo, servico, data, hora, valor))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/agenda")

    return render_template("agendar.html")

# =============================
# AGENDA
# =============================
@app.route("/agenda")
def agenda():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, cliente, servico, data, hora, status
        FROM agendamentos
    """)
    dados = cursor.fetchall()

    cursor.close()
    conn.close()

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
# CONCLUIR
# =============================
@app.route("/concluir/<int:id>")
def concluir(id):
    conn = get_connection()
    cursor = conn.cursor()

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

    cursor.close()
    conn.close()

    return redirect("/agenda")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
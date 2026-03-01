from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import requests

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

app = Flask(__name__)

# =============================
# CRIAR BANCO AUTOMATICAMENTE
# =============================
def criar_banco():
    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            veiculo TEXT,
            servico TEXT,
            data TEXT,
            valor REAL
        )
    """)
    conn.commit()
    conn.close()

criar_banco()

# =============================
# PAGINA PRINCIPAL
# =============================
@app.route("/")
def index():
    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM servicos")
    servicos = cursor.fetchall()

    cursor.execute("SELECT SUM(valor) FROM servicos")
    faturamento = cursor.fetchone()[0]
    faturamento = faturamento if faturamento else 0

    conn.close()

    return render_template("index.html",
                           servicos=servicos,
                           faturamento=faturamento)

# =============================
# ADICIONAR SERVIÇO
# =============================
@app.route("/adicionar", methods=["POST"])
def adicionar():
    cliente = request.form["cliente"]
    veiculo = request.form["veiculo"]
    servico = request.form["servico"]
    valor = float(request.form["valor"])
    numero = request.form["numero"]
    data = datetime.now().strftime("%d/%m/%Y")

    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO servicos (cliente, veiculo, servico, data, valor)
        VALUES (?, ?, ?, ?, ?)
    """, (cliente, veiculo, servico, data, valor))

    conn.commit()
    conn.close()

    # =============================
    # WHATSAPP BUSINESS API
    # =============================
    TOKEN = "SEU_TOKEN_AQUI"
    PHONE_ID = "SEU_PHONE_ID_AQUI"

    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    mensagem = f"""
Olá {cliente}!
Seu serviço ({servico}) foi registrado.
Valor: R$ {valor:.2f}
Street Car 🚗
"""

    data_api = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensagem}
    }

    try:
        requests.post(url, headers=headers, json=data_api)
    except:
        pass

    return redirect("/")

# =============================
# EXCLUIR
# =============================
@app.route("/excluir/<int:id>")
def excluir(id):
    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servicos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# =============================
# DASHBOARD
# =============================
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT data, SUM(valor)
        FROM servicos
        GROUP BY data
    """)

    dados = cursor.fetchall()
    conn.close()

    datas = [d[0] for d in dados]
    valores = [d[1] for d in dados]

    return render_template("dashboard.html",
                           datas=datas,
                           valores=valores)

# =============================
# RELATÓRIO PDF
# =============================
@app.route("/relatorio_pdf")
def relatorio_pdf():
    conn = sqlite3.connect("streetcar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servicos")
    dados = cursor.fetchall()
    conn.close()

    pdf = SimpleDocTemplate("static/relatorio.pdf")
    elementos = []
    estilos = getSampleStyleSheet()

    elementos.append(Paragraph("Relatório Street Car", estilos["Title"]))
    elementos.append(Spacer(1, 0.5 * inch))

    tabela_dados = [["ID", "Cliente", "Veículo", "Serviço", "Data", "Valor"]]

    for s in dados:
        tabela_dados.append([
            s[0], s[1], s[2], s[3], s[4], f"R$ {s[5]:.2f}"
        ])

    tabela = Table(tabela_dados)
    elementos.append(tabela)

    pdf.build(elementos)

    return redirect("/static/relatorio.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
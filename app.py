from flask import Flask, render_template, request, redirect, url_for, session, send_file
import mysql.connector
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from urllib.parse import quote
import os

app = Flask(__name__)
app.secret_key = "alexmo_secret"

# ==========================
# CONEXIÓN BASE DE DATOS
# ==========================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="alexmo_cY2001",
        database="mi_gas"
    )

# ==========================
# GENERAR FACTURA PDF
# ==========================
def generar_factura_pdf(nombre, telefono, producto, cantidad, total):

    if not os.path.exists("facturas"):
        os.makedirs("facturas")

    pdf_path = f"facturas/factura_{telefono}.pdf"

    doc = SimpleDocTemplate(pdf_path)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("FACTURA - MI GAS", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Cliente: {nombre}", styles["Normal"]))
    elements.append(Paragraph(f"Teléfono: {telefono}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Producto: {producto}", styles["Normal"]))
    elements.append(Paragraph(f"Cantidad: {cantidad}", styles["Normal"]))
    elements.append(Paragraph(f"Total: Q{total}", styles["Normal"]))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Gracias por confiar en Mi Gas 🔥", styles["Normal"]))

    doc.build(elements)

    return pdf_path

# ==========================
# LOGIN
# ==========================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        correo = request.form['correo']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE correo = %s AND password = %s",
            (correo, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session['usuario'] = user[1]
            session['id_usuario'] = user[0]
            return redirect(url_for('index'))
        else:
            return "❌ Credenciales inválidas"

    return render_template('login.html')

# ==========================
# REGISTRO
# ==========================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':

        nombre = request.form['nombre']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        correo = request.form['correo']
        password = request.form['password']
        fecha_registro = request.form['fecha_registro']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO usuarios 
            (nombre, telefono, direccion, correo, password, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nombre, telefono, direccion, correo, password, fecha_registro))

        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Usuario registrado exitosamente"

    return render_template('registro.html')

# ==========================
# INDEX
# ==========================
@app.route('/index')
def index():
    if 'usuario' in session:
        return render_template('index.html', usuario=session['usuario'])
    return redirect(url_for('login'))

# ==========================
# LOGOUT
# ==========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================
# COMPRAR GAS
# ==========================
@app.route('/comprar_gas', methods=['GET', 'POST'])
def comprar_gas():

    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cilindros WHERE stock > 0")
    cilindros = cursor.fetchall()

    if request.method == 'POST':

        id_cilindro = request.form['id_cilindro']
        cantidad = int(request.form['cantidad'])
        direccion = request.form['direccion']

        cursor.execute("SELECT * FROM cilindros WHERE id_cilindro = %s", (id_cilindro,))
        cilindro = cursor.fetchone()

        total = cilindro['precio'] * cantidad

        cursor.close()
        conn.close()

        return render_template(
            'confirmar_pago.html',
            cilindro=cilindro,
            cantidad=cantidad,
            direccion=direccion,
            total=total
        )

    cursor.close()
    conn.close()

    return render_template('comprar_gas.html', cilindros=cilindros)

# ==========================
# SERVIR FACTURA
# ==========================
@app.route('/facturas/<filename>')
def servir_factura(filename):
    return send_file(f"facturas/{filename}", as_attachment=False)

# ==========================
# PROCESAR PAGO
# ==========================
@app.route('/procesar_pago', methods=['POST'])
def procesar_pago():

    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    id_usuario = session['id_usuario']
    id_cilindro = request.form['id_cilindro']
    cantidad = int(request.form['cantidad'])
    total = float(request.form['total'])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Guardar venta
    cursor.execute("""
        INSERT INTO ventas_gas
        (id_usuario, id_cilindro, cantidad, total, fecha, estado)
        VALUES (%s, %s, %s, %s, NOW(), 'Pendiente')
    """, (id_usuario, id_cilindro, cantidad, total))

    # Actualizar stock
    cursor.execute("""
        UPDATE cilindros
        SET stock = stock - %s
        WHERE id_cilindro = %s
    """, (cantidad, id_cilindro))

    conn.commit()

    # Obtener datos usuario
    cursor.execute("SELECT nombre, telefono FROM usuarios WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()

    nombre = usuario['nombre']
    telefono = usuario['telefono']

    # Obtener nombre producto
    cursor.execute("SELECT tipo,peso FROM cilindros WHERE id_cilindro = %s", (id_cilindro,))
    cilindro = cursor.fetchone()
    producto = f"{cilindro['tipo']} - {cilindro['peso']} lb"

    cursor.close()
    conn.close()

    # Generar factura
    pdf_path = generar_factura_pdf(nombre, telefono, producto, cantidad, total)
    nombre_archivo = os.path.basename(pdf_path)

    # Mensaje WhatsApp
    mensaje = f"""
Hola {nombre} 👋

Gracias por tu compra en Mi Gas 🔥

Producto: {producto}
Cantidad: {cantidad}
Total: Q{total}

Aquí está tu factura:
http://localhost:5000/facturas/{nombre_archivo}
"""

    mensaje_codificado = quote(mensaje)

    return redirect(f"https://wa.me/502{telefono}?text={mensaje_codificado}")

# ==========================
# EJECUTAR
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
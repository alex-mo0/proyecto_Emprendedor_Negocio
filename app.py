from asyncio import events

from flask import Flask, render_template, request, redirect, url_for, session, send_file
import mysql.connector
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime
import os
import random   
import smtplib


app = Flask(__name__)
app.secret_key = "alexmo_secret"

# ==========================
# CONEXIÓN BD
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime
import os
import random

def generar_factura_pdf(nombre, telefono, producto, cantidad, total, direccion):

    if not os.path.exists("facturas"):
        os.makedirs("facturas")

    numero_factura = "FAC-" + str(random.randint(10000,99999))
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf_path = f"facturas/factura_{numero_factura}.pdf"

    doc = SimpleDocTemplate(pdf_path)
    elements = []
    styles = getSampleStyleSheet()

    # 🔥 LOGO (opcional)
    if os.path.exists("static/45.png"):
        logo = Image("static/45.png", width=120, height=90 )
        logo.hAlign = 'LEFT'
        elements.append(logo)
    # 🧾 TÍTULO
    elements.append(Paragraph("<b>FACTURA</b>", styles["Title"]))

    # 📌 INFO EMPRESA
    elements.append(Paragraph("RapiGas", styles["Normal"]))
    elements.append(Paragraph("Tel: 1234-5678", styles["Normal"]))
    elements.append(Paragraph("Dirección: Mixqueño", styles["Normal"]))

    elements.append(Spacer(1, 0.2 * inch))

    # 🔢 INFO FACTURA
    elements.append(Paragraph(f"No. Factura: {numero_factura}", styles["Normal"]))
    elements.append(Paragraph(f"Fecha: {fecha}", styles["Normal"]))

    elements.append(Spacer(1, 0.3 * inch))

    # 👤 CLIENTE
    elements.append(Paragraph("<b>Datos del Cliente</b>", styles["Heading3"]))
    elements.append(Paragraph(f"Nombre: {nombre}", styles["Normal"]))
    elements.append(Paragraph(f"Teléfono: {telefono}", styles["Normal"]))
    elements.append(Paragraph(f"Dirección: {direccion}", styles["Normal"]))

    elements.append(Spacer(1, 0.3 * inch))

    # 📦 TABLA DE PRODUCTOS
    data = [
        ["Producto", "Cantidad", "Precio Unitario", "Total"],
        [producto, str(cantidad), f"Q{round(total/cantidad,2)}", f"Q{total}"]
    ]

    table = Table(data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(1,1),(-1,-1),'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 0.3 * inch))

    # 💰 TOTAL GRANDE
    elements.append(Paragraph(f"<b>Total a pagar: Q{total}</b>", styles["Heading2"]))

    elements.append(Spacer(1, 0.5 * inch))

    # 🙌 MENSAJE FINAL
    elements.append(Paragraph("Gracias por su compra ", styles["Normal"]))

    doc.build(elements)

    return pdf_path

# ==========================
# LOGIN (USUARIO + ADMIN)
# ==========================
@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        correo = request.form['correo']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # USUARIO
        cursor.execute("SELECT * FROM usuarios WHERE correo=%s AND password=%s", (correo, password))
        user = cursor.fetchone()

        if user:
            session['usuario'] = user['nombre']
            session['id_usuario'] = user['id_usuario']
            session['rol'] = 'usuario'
            cursor.close()
            conn.close()
            return redirect(url_for('index'))

        # ADMIN
        cursor.execute("SELECT * FROM administradores WHERE correo=%s AND password=%s", (correo, password))
        admin = cursor.fetchone()

        if admin:
            session['usuario'] = admin['nombre']
            session['id_admin'] = admin['id_admin']
            session['rol'] = 'admin'
            cursor.close()
            conn.close()
            return redirect(url_for('admin'))
        #repartidor
        cursor.execute("SELECT * FROM repartidores WHERE correo=%s AND password=%s", (correo, password))    
        repartidor = cursor.fetchone()
        if repartidor:
            session['usuario'] = repartidor['nombre']
            session['id_repartidor'] = repartidor['id_repartidor']
            session['rol'] = 'repartidor'
            cursor.close()
            conn.close()
            return redirect(url_for('repartidor'))

        cursor.close()
        conn.close()

        return "❌ Credenciales incorrectas"

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
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (nombre, telefono, direccion, correo, password, fecha_registro))

        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Usuario registrado"

    return render_template('registro.html')

# ==========================
# INDEX
# ==========================
@app.route('/index')
def index():
    if session.get('rol') != 'usuario':
        return redirect(url_for('login'))
    return render_template('index.html', usuario=session['usuario'])

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
        observacion = request.form.get('observacion', '')
        fecha_entrega = request.form.get('fecha_entrega')
        hora_entrega = request.form.get('hora_entrega')

        cursor.execute("SELECT * FROM cilindros WHERE id_cilindro=%s", (id_cilindro,))
        cilindro = cursor.fetchone()

        total = cilindro['precio'] * cantidad

        cursor.close()
        conn.close()

        return render_template('confirmar_pago.html',
            cilindro=cilindro,
            cantidad=cantidad,
            direccion=direccion,
            observacion=observacion,
            total=total,
            fecha_entrega=fecha_entrega,
            hora_entrega=hora_entrega
        )

    cursor.close()
    conn.close()

    return render_template('comprar_gas.html', cilindros=cilindros)

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
    direccion = request.form['direccion']
    observacion = request.form.get('observacion', '')
    metodo_pago = request.form['metodo_pago']

    fecha_entrega = request.form.get('fecha_entrega')
    hora_entrega = request.form.get('hora_entrega')

    if not fecha_entrega or not hora_entrega:
        ahora = datetime.now()
        fecha_entrega = ahora.strftime("%Y-%m-%d")
        hora_entrega = ahora.strftime("%H:%M:%S")

    numero_factura = "FAC-" + str(random.randint(10000, 99999))
    estado = "Pagado" if metodo_pago == "tarjeta" else "Pendiente"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO ventas_gas_nueva
        (id_usuario,id_cilindro,cantidad,total,direccion,observacion,estado,fecha_entrega,hora_entrega,numero_factura)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (id_usuario, id_cilindro, cantidad, total, direccion, observacion, estado, fecha_entrega, hora_entrega,numero_factura))

    cursor.execute("UPDATE cilindros SET stock = stock - %s WHERE id_cilindro = %s",
                   (cantidad, id_cilindro))

    conn.commit()

    cursor.close()
    conn.close()

    return render_template('mensaje.html', mensaje="✅ Pedido realizado", factura=numero_factura)

# ==========================
# MIS PEDIDOS
# ==========================
@app.route('/mis_pedidos')
def mis_pedidos():

    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT v.*, c.tipo, c.peso
        FROM ventas_gas_nueva v
        JOIN cilindros c ON v.id_cilindro = c.id_cilindro
        WHERE v.id_usuario = %s
    """, (session['id_usuario'],))

    pedidos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('mis_pedidos.html', pedidos=pedidos)

# ==========================
# ADMIN DASHBOARD
# ==========================
@app.route('/admin')
def admin():

    if session.get('rol') != 'admin':
        return "❌ Acceso no autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # TOTAL PEDIDOS
    cursor.execute("SELECT COUNT(*) as total FROM ventas_gas_nueva")
    total_pedidos = cursor.fetchone()['total']

    # TOTAL VENTAS
    cursor.execute("SELECT SUM(total) as total FROM ventas_gas_nueva")
    total_ventas = cursor.fetchone()['total'] or 0

    # TOTAL USUARIOS
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    total_usuarios = cursor.fetchone()['total']

    # PEDIDOS RECIENTES ✅
    cursor.execute("""
        SELECT v.id_ventas, u.nombre, v.total, v.estado
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        ORDER BY v.id_ventas DESC
        LIMIT 5
    """)
    pedidos = cursor.fetchall()

    # VENTAS PARA GRAFICA ✅ (ESTO TE FALTABA)
    cursor.execute("""
        SELECT DATE(fecha) as dia, SUM(total) as total
        FROM ventas_gas_nueva
        GROUP BY DATE(fecha)
        ORDER BY dia ASC
    """)
    ventas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin.html',
        total_pedidos=total_pedidos,
        total_ventas=total_ventas,
        total_usuarios=total_usuarios,
        pedidos=pedidos,
        ventas=ventas,  # 🔥 YA EXISTE
        admin_nombre=session['usuario']
    )
# ==========================
# ADMIN PEDIDOS
# ==========================
@app.route('/admin_pedidos')
def admin_pedidos():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 📦 PEDIDOS
    cursor.execute("""
        SELECT 
            v.id_ventas,
            u.nombre,
            c.tipo,
            c.peso,
            v.total,
            v.estado,
            v.estado_ruta,
            v.id_repartidor,
            DATE_FORMAT(v.fecha_entrega, '%d/%m/%Y') as fecha_entrega,
            v.direccion,
            r.nombre AS repartidor_nombre
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        JOIN cilindros c ON v.id_cilindro = c.id_cilindro
        LEFT JOIN repartidores r ON v.id_repartidor = r.id_repartidor
        WHERE v.estado_ruta != 'entregado' OR v.estado_ruta IS NULL
        ORDER BY v.id_ventas DESC
    """)
    pedidos = cursor.fetchall()

    # 👷 REPARTIDORES (FALTABA ESTO 🔥)
    cursor.execute("SELECT * FROM repartidores")
    repartidores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin_pedidos.html',
        pedidos=pedidos,
        repartidores=repartidores   # 👈 CLAVE
    )
# ==========================
# ADMIN INVENTARIO
# ==========================
@app.route('/admin_inventario')
def admin_inventario():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cilindros")
    productos = cursor.fetchall()
    cursor.execute("SELECT * FROM cilindros_vacios")
    vacios = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_inventario.html', productos=productos, vacios=vacios)

# ==========================
# ADMIN USUARIOS
# ==========================
@app.route('/admin_usuarios')
def admin_usuarios():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_usuarios.html', usuarios=usuarios)
#despacho
@app.route('/admin_historial')
def admin_historial():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            v.id_ventas,
            u.nombre,
            v.total,
            v.factura_enviada,
            DATE_FORMAT(v.fecha_entrega,'%d/%m/%Y') as fecha_entrega,
            r.nombre AS repartidor_nombre
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        LEFT JOIN repartidores r ON v.id_repartidor = r.id_repartidor
        WHERE v.estado_ruta = 'entregado'
        ORDER BY v.id_ventas DESC
    """)

    pedidos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_historial.html",
        pedidos=pedidos,
        admin_nombre=session.get('usuario')
    )
#asignar repartidor
@app.route('/asignar_repartidor', methods=['POST'])
def asignar_repartidor():

    id_venta = request.form['id_venta']
    id_repartidor = request.form['repartidor']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET id_repartidor = %s,
            estado_ruta = 'asignado'
        WHERE id_ventas = %s
    """, (id_repartidor, id_venta))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/admin_pedidos')

#estado de ruta 
@app.route('/estado/<int:id>/<estado>')
def cambiar_estado(id, estado):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET estado = %s
        WHERE id_ventas = %s
    """, (estado, id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/admin_despacho')
#finalizar ruta
@app.route('/finalizar/<int:id>')
def finalizar_pedido(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET estado_ruta = 'entregado'
        WHERE id_ventas = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/admin_pedidos')

#historial de ventas
@app.route('/historial')
def historial():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            v.id_ventas,
            u.nombre,
            c.tipo,
            c.peso,
            v.total,
            DATE_FORMAT(v.fecha_entrega, '%d/%m/%Y') as fecha_entrega,
            r.nombre AS repartidor_nombre
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        JOIN cilindros c ON v.id_cilindro = c.id_cilindro
        LEFT JOIN repartidores r ON v.id_repartidor = r.id_repartidor
        WHERE v.estado_ruta = 'entregado'
        ORDER BY v.id_ventas DESC
    """)

    pedidos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('historial.html', pedidos=pedidos)

#enviar factura
@app.route('/enviar_factura/<int:id>')
def enviar_factura(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET factura_enviada = 1
        WHERE id_ventas = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/admin_historial')
#mis facturas
@app.route('/mis_facturas')
def mis_facturas():

    if session.get('rol') != 'usuario':   # 🔥 MEJOR VALIDACIÓN
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            id_ventas,
            total,
            fecha_entrega
        FROM ventas_gas_nueva
        WHERE id_usuario = %s
        AND estado_ruta = 'entregado'
        AND factura_enviada = 1
    """, (session['id_usuario'],))

    facturas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("mis_facturas.html", facturas=facturas)
#descargar factura
@app.route('/descargar_factura/<int:id>')
def descargar_factura(id):

    if session.get('rol') != 'usuario':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT v.*, u.nombre, u.telefono, c.tipo
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        JOIN cilindros c ON v.id_cilindro = c.id_cilindro
        WHERE v.id_ventas = %s
    """, (id,))

    venta = cursor.fetchone()

    cursor.close()
    conn.close()

    # 🔥 generar PDF
    pdf_path = generar_factura_pdf(
        venta['nombre'],
        venta['telefono'],
        venta['tipo'],
        venta['cantidad'],
        venta['total'],
        venta['direccion']
    )

    return send_file(pdf_path, as_attachment=True)

#repartidor 
@app.route('/repartidor')
def repartidor():

    if session.get('rol') != 'repartidor':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT v.*, u.nombre,v.observacion as pedido_observacion, v.direccion, u.telefono, c.tipo
        FROM ventas_gas_nueva v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        JOIN cilindros c ON v.id_cilindro = c.id_cilindro
        WHERE v.id_repartidor = %s
        AND v.estado_ruta != 'entregado'
    """, (session['id_repartidor'],))

    pedidos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('repartidor.html', pedidos=pedidos)
# ==========================
#inicio de ruta
@app.route('/iniciar_ruta/<int:id>')
def iniciar_ruta(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET estado_ruta = 'en_camino'
        WHERE id_ventas = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/repartidor')
#entregar parte de repartidor
@app.route('/entregar/<int:id>')
def entregar(id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ver estado actual
    cursor.execute("SELECT estado FROM ventas_gas_nueva WHERE id_ventas = %s", (id,))
    venta = cursor.fetchone()

    if venta['estado'] == 'Pendiente':
        # pago en efectivo
        cursor.execute("""
            UPDATE ventas_gas_nueva
            SET estado = 'Pagado',
                estado_ruta = 'entregado'
            WHERE id_ventas = %s
        """, (id,))
    else:
        # ya estaba pagado (tarjeta)
        cursor.execute("""
            UPDATE ventas_gas_nueva
            SET estado_ruta = 'entregado'
            WHERE id_ventas = %s
        """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/repartidor')
#enviar a ruta
@app.route('/enviar_ruta/<int:id>')
def enviar_ruta(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ventas_gas_nueva
        SET estado_ruta = 'en_camino'
        WHERE id_ventas = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/admin_pedidos')

#ventas por fecha 
@app.route('/admin_ventas')
def admin_ventas():

    if session.get('rol') != 'admin':
        return "❌ No autorizado"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # filtros
    fecha = request.args.get('fecha')
    factura = request.args.get('factura')

    query = """
    SELECT v.*, u.nombre
    FROM ventas_gas_nueva v
    JOIN usuarios u ON v.id_usuario = u.id_usuario
    WHERE 1=1
    """

    valores = []

    if fecha:
        query += " AND DATE(v.fecha_entrega) = %s"
        valores.append(fecha)

    if factura:
        query += " AND v.numero_factura = %s"
        valores.append(factura)

    query += " ORDER BY v.fecha_entrega DESC"

    cursor.execute(query, valores)
    ventas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_ventas.html', ventas=ventas)

# RUN
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
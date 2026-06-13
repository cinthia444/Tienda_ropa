from flask import Flask, render_template, request, redirect, session
import sqlite3
from mongo import (
    productos_collection,
    usuarios_collection,
    ventas_collection,
    carrito_collection
)

app = Flask(__name__)
app.secret_key = "inventario_ropa"


# ==========================
# CREAR BASE DE DATOS
# ==========================
def crear_db():
    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        talla TEXT NOT NULL,
        color TEXT NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL,
        imagen TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        cantidad INTEGER,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO usuarios
    (usuario,password)
    VALUES ('admin','1234')
    """)

    conexion.commit()
    conexion.close()

    usuarios_collection.update_one(
        {"usuario": "admin"},
        {"$set": {"usuario": "admin", "password": "1234"}},
        upsert=True
    )


crear_db()


# ==========================
# LOGIN
# ==========================
@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        conexion = sqlite3.connect("inventario.db")
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND password=?",
            (usuario, password)
        )

        usuario_encontrado = cursor.fetchone()
        conexion.close()

        if usuario_encontrado:
            return redirect('/dashboard')

        return render_template(
            'login.html',
            error='Usuario o contraseña incorrectos'
        )

    return render_template('login.html')


# ==========================
# DASHBOARD
# ==========================
@app.route('/dashboard')
def dashboard():

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM productos")
    total_productos = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(stock) FROM productos")
    total_stock = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(precio * stock) FROM productos")
    valor_inventario = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM productos WHERE stock <= 5")
    stock_bajo = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "dashboard.html",
        total_productos=total_productos,
        total_stock=total_stock,
        valor_inventario=round(valor_inventario, 2),
        stock_bajo=stock_bajo
    )


# ==========================
# PRODUCTOS
# ==========================
@app.route('/productos')
def productos():

    buscar = request.args.get('buscar', '')
    categoria = request.args.get('categoria', '')

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    if buscar:
        cursor.execute(
            "SELECT * FROM productos WHERE nombre LIKE ?",
            ('%' + buscar + '%',)
        )

    elif categoria:
        cursor.execute(
            "SELECT * FROM productos WHERE categoria=?",
            (categoria,)
        )

    else:
        cursor.execute("SELECT * FROM productos")

    productos = cursor.fetchall()
    conexion.close()

    return render_template(
        "productos.html",
        productos=productos
    )


# ==========================
# AGREGAR PRODUCTO
# ==========================
@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        talla = request.form['talla']
        color = request.form['color']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        imagen = request.form['imagen']

        conexion = sqlite3.connect("inventario.db")
        cursor = conexion.cursor()

        cursor.execute("""
        INSERT INTO productos
        (nombre, categoria, talla, color, precio, stock, imagen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            nombre,
            categoria,
            talla,
            color,
            precio,
            stock,
            imagen
        ))

        conexion.commit()

        producto_id = cursor.lastrowid

        productos_collection.insert_one({
            "sqlite_id": producto_id,
            "nombre": nombre,
            "categoria": categoria,
            "talla": talla,
            "color": color,
            "precio": precio,
            "stock": stock,
            "imagen": imagen
        })

        conexion.close()

        return redirect('/productos')

    return render_template('agregar_producto.html')


# ==========================
# EDITAR PRODUCTO
# ==========================
@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        talla = request.form['talla']
        color = request.form['color']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        imagen = request.form['imagen']

        cursor.execute("""
        UPDATE productos
        SET nombre=?,
            categoria=?,
            talla=?,
            color=?,
            precio=?,
            stock=?,
            imagen=?
        WHERE id=?
        """, (
            nombre,
            categoria,
            talla,
            color,
            precio,
            stock,
            imagen,
            id
        ))

        conexion.commit()

        productos_collection.update_one(
            {"sqlite_id": id},
            {
                "$set": {
                    "sqlite_id": id,
                    "nombre": nombre,
                    "categoria": categoria,
                    "talla": talla,
                    "color": color,
                    "precio": precio,
                    "stock": stock,
                    "imagen": imagen
                }
            },
            upsert=True
        )

        conexion.close()

        return redirect('/productos')

    cursor.execute(
        "SELECT * FROM productos WHERE id=?",
        (id,)
    )

    producto = cursor.fetchone()
    conexion.close()

    return render_template(
        'editar_producto.html',
        producto=producto
    )


# ==========================
# ELIMINAR PRODUCTO
# ==========================
@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute(
        "DELETE FROM productos WHERE id=?",
        (id,)
    )

    conexion.commit()
    conexion.close()

    productos_collection.delete_one({"sqlite_id": id})
    carrito_collection.delete_many({"producto_id": id})

    return redirect('/productos')


# ==========================
# VENTAS
# ==========================
@app.route('/ventas', methods=['GET', 'POST'])
def ventas():

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad = int(request.form['cantidad'])

        cursor.execute(
            "SELECT stock FROM productos WHERE id=?",
            (producto_id,)
        )

        resultado = cursor.fetchone()

        if resultado:
            stock_actual = resultado[0]

            if stock_actual >= cantidad:
                nuevo_stock = stock_actual - cantidad

                cursor.execute(
                    "UPDATE productos SET stock=? WHERE id=?",
                    (nuevo_stock, producto_id)
                )

                cursor.execute("""
                INSERT INTO ventas
                (producto_id, cantidad)
                VALUES (?, ?)
                """, (
                    producto_id,
                    cantidad
                ))

                conexion.commit()

                venta_id = cursor.lastrowid

                ventas_collection.insert_one({
                    "sqlite_id": venta_id,
                    "producto_id": producto_id,
                    "cantidad": cantidad
                })

                productos_collection.update_one(
                    {"sqlite_id": producto_id},
                    {"$set": {"stock": nuevo_stock}}
                )

        conexion.close()

        return redirect('/ventas')

    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    conexion.close()

    return render_template(
        'ventas.html',
        productos=productos
    )


# ==========================
# REPORTES
# ==========================
@app.route('/reportes')
def reportes():

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM productos")
    total_productos = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(stock) FROM productos")
    total_stock = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(precio * stock) FROM productos")
    valor_inventario = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM ventas")
    total_ventas = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "reportes.html",
        total_productos=total_productos,
        total_stock=total_stock,
        valor_inventario=round(valor_inventario, 2),
        total_ventas=total_ventas
    )


# ==========================
# HISTORIAL VENTAS
# ==========================
@app.route('/historial_ventas')
def historial_ventas():

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT ventas.id,
           productos.nombre,
           ventas.cantidad,
           ventas.fecha
    FROM ventas
    INNER JOIN productos
    ON ventas.producto_id = productos.id
    ORDER BY ventas.id DESC
    """)

    ventas = cursor.fetchall()
    conexion.close()

    return render_template(
        'historial_ventas.html',
        ventas=ventas
    )


# ==========================
# DETALLE PRODUCTO
# ==========================
@app.route('/producto/<int:id>')
def detalle_producto(id):

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT * FROM productos WHERE id=?",
        (id,)
    )

    producto = cursor.fetchone()
    conexion.close()

    return render_template(
        "detalle_producto.html",
        producto=producto
    )


# ==========================
# AGREGAR AL CARRITO
# ==========================
@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):

    if 'carrito' not in session:
        session['carrito'] = []

    session['carrito'].append(id)
    session.modified = True

    carrito_collection.insert_one({
        "producto_id": id
    })

    return redirect('/carrito')


# ==========================
# VER CARRITO
# ==========================
@app.route('/carrito')
def carrito():

    ids = session.get('carrito', [])
    productos = []

    if ids:
        conexion = sqlite3.connect("inventario.db")
        cursor = conexion.cursor()

        for producto_id in ids:
            cursor.execute(
                "SELECT * FROM productos WHERE id=?",
                (producto_id,)
            )

            producto = cursor.fetchone()

            if producto:
                productos.append(producto)

        conexion.close()

    total = sum(producto[5] for producto in productos)

    return render_template(
        "carrito.html",
        productos=productos,
        total=total
    )


# ==========================
# ELIMINAR DEL CARRITO
# ==========================
@app.route('/eliminar_carrito/<int:id>')
def eliminar_carrito(id):

    carrito = session.get('carrito', [])

    if id in carrito:
        carrito.remove(id)

    session['carrito'] = carrito
    session.modified = True

    carrito_collection.delete_one({"producto_id": id})

    return redirect('/carrito')


# ==========================
# FINALIZAR COMPRA
# ==========================
@app.route('/finalizar_compra')
def finalizar_compra():

    carrito = session.get('carrito', [])

    if not carrito:
        return redirect('/carrito')

    conexion = sqlite3.connect("inventario.db")
    cursor = conexion.cursor()

    for producto_id in carrito:

        cursor.execute(
            "SELECT stock FROM productos WHERE id=?",
            (producto_id,)
        )

        producto = cursor.fetchone()

        if producto and producto[0] > 0:
            nuevo_stock = producto[0] - 1

            cursor.execute(
                "UPDATE productos SET stock=? WHERE id=?",
                (nuevo_stock, producto_id)
            )

            cursor.execute("""
            INSERT INTO ventas
            (producto_id, cantidad)
            VALUES (?, ?)
            """, (
                producto_id,
                1
            ))

            conexion.commit()

            venta_id = cursor.lastrowid

            ventas_collection.insert_one({
                "sqlite_id": venta_id,
                "producto_id": producto_id,
                "cantidad": 1
            })

            productos_collection.update_one(
                {"sqlite_id": producto_id},
                {"$set": {"stock": nuevo_stock}}
            )

    conexion.close()

    session['carrito'] = []
    carrito_collection.delete_many({})

    return redirect('/productos')


# ==========================
# EJECUTAR APP
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
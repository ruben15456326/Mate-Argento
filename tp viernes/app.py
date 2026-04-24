from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'mi_llave_secreta_super_segura'
# Configuración mínima para que funcione la base de datos
db_path = os.path.join(os.path.dirname(__file__), 'mate_argento.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)

# TABLA DE USUARIOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    # NUEVA COLUMNA:
    rol = db.Column(db.String(20), default='cliente')
# NUEVA TABLA PARA STOCK
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    precio = db.Column(db.Float, nullable=False) # Float para números con decimales
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(100)) # Aquí guardamos el nombre del archivo (ej: "mate.jpg")

with app.app_context():
    db.create_all()

# --- TUS RUTAS DE SIEMPRE (pero guardando en DB) ---

@app.route('/')
def inicio():
    # Buscamos todos los productos en la base de datos
    productos_db = Producto.query.all()
    # Se los pasamos al HTML con el nombre 'productos'
    return render_template('inicio.html', productos=productos_db)


@app.route('/login', methods=['GET', 'POST'])
def vista_login():
    
    if request.method == 'POST':
        email_f = request.form.get('email')
        pass_f = request.form.get('password')
        # Buscamos en la DB:
        user = Usuario.query.filter_by(email=email_f, password=pass_f).first()
        if user:
            # GUARDAMOS EN LA SESIÓN
            session['usuario_id'] = user.id
            session['usuario_nombre'] = user.nombre
            session['usuario_rol'] = user.rol
            session['carrito'] = [] # Inicializamos el carrito vacío
            return f"<h1>Bienvenido {user.nombre}</h1><a href='/'>Inicio</a>"
        return "<h1>Error de datos</h1><a href='/login'>Volver</a>"
    return render_template('login.html')

# RUTA PARA AGREGAR AL CARRITO (SOLO PARA USUARIOS LOGUEADOS)
@app.route('/agregar_al_carrito/<int:id>')
def agregar_al_carrito(id):
    if 'usuario_nombre' not in session:
        return redirect('/login') # Si no está logueado, al login

    # Obtenemos el carrito actual de la sesión

    carrito = list(session.get('carrito', []))
    
    # Agregamos el ID del producto
    carrito.append(id)
    
    # Guardamos el carrito actualizado en la sesión
    session['carrito'] = carrito
    
    # Marcamos la sesión como "modificada" para que Flask guarde los cambios
    session.modified = True
    producto = Producto.query.get(id)
    # ENVIAMOS EL MENSAJE: (Texto, Categoría)
    flash(f"¡{producto.nombre} se agregó al carrito!", "success")
    # En vez de volver al inicio, volvemos al detalle de ese mismo producto
    return redirect(f'/detalle/{id}') 
# RUTA PARA CERRAR SESIÓN
@app.route('/logout')
def logout():
    session.clear() # Borra todo lo guardado
    return redirect('/')

@app.route('/registro')
def vista_registro():
    return render_template('registro.html')

@app.route('/registrar_usuario', methods=['POST'])
def registrar_usuario():
    # Creamos el usuario con lo que viene del formulario
    nuevo = Usuario(
        nombre=request.form.get('nombre'),
        email=request.form.get('email'),
        password=request.form.get('password')
    )
    db.session.add(nuevo) # Lo agregamos
    db.session.commit()   # Guardamos de verdad
    return f"<h1>Registrado con éxito</h1><a href='/login'>Ir al Login</a>"

# NUEVA RUTA PARA CARGAR PRODUCTOS (SOLO PARA ADMIN)

@app.route('/admin/nuevo_producto', methods=['GET', 'POST'])
def nuevo_producto():
    # VERIFICACIÓN DE SEGURIDAD
    if session.get('usuario_rol') != 'admin':
        return "<h1>Acceso denegado. Solo administradores.</h1>", 403
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = float(request.form.get('precio'))
        categoria = request.form.get('categoria')
        imagen = request.form.get('imagen') # Por ahora el nombre del archivo
        descripcion = request.form.get('descripcion')

        nuevo = Producto(nombre=nombre, precio=precio, categoria=categoria, imagen=imagen, descripcion=descripcion)
        db.session.add(nuevo)
        db.session.commit()
        return "Producto cargado con éxito. <a href='/'>Volver</a>"
    
    # Si es GET, mostramos el formulario
    return render_template('cargar_producto.html')


#Ruta para eliminar productos (SOLO ADMIN)


@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    # SEGURIDAD: Solo el admin puede eliminar
    if session.get('usuario_rol') != 'admin':
        return "Acceso denegado", 403

    # Buscamos el producto por su ID
    producto = Producto.query.get(id)
    
    if producto:
        db.session.delete(producto) # Lo marcamos para borrar
        db.session.commit()         # Confirmamos el cambio en la DB
    
    return redirect('/') # Volvemos al inicio para ver los cambios

#Ruta para ver el detalle de un producto (con su descripción, imagen, etc)
@app.route('/detalle/<int:id>')
def detalle_producto(id):
    # Buscamos el producto específico por su ID único
    p = Producto.query.get(id)
    
    if p:
        return render_template('detalle.html', producto=p)
    else:
        return "Producto no encontrado", 404
    
    
#SE CREA UN ADMIN INICIAL PARA PODER PROBAR EL PANEL DE ADMINISTRACIÓN (LUEGO SE PODRÁ CREAR DESDE EL PANEL)
@app.route('/crear_admin_inicial')
def crear_admin():
    # Verificamos si ya existe para no duplicar
    existe = Usuario.query.filter_by(email="admin@mateargento.com").first()
    if not existe:
        admin = Usuario(
            nombre="Admin", 
            email="admin@mateargento.com", 
            password="123", 
            rol="admin" # IMPORTANTE
        )
        db.session.add(admin)
        db.session.commit()
        return "Administrador creado. Email: admin@mateargento.com, Pass: admin123"
    
    return "El admin ya existe."

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request,url_for, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from functools import wraps
#comentario inicial para probar el git
#hola
app = Flask(__name__)
app.secret_key = 'mi_llave_secreta_super_segura'

# --- CONFIGURACIÓN DE ROLES Y NIVELES ---
# Definimos el "poder" de cada rol. Cuanto más alto el número, más permisos.
NIVELES_ACCESO = {
    'cliente': 1,
    'gestor': 5,
    'admin': 10
}

def requiere_nivel(nivel_minimo):
    """
    Decorador para proteger rutas según el nivel de acceso.
    Uso: @requiere_nivel(5) protegerá la ruta para gestores y admins.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            rol_usuario = session.get('usuario_rol', 'cliente')
            nivel_usuario = NIVELES_ACCESO.get(rol_usuario, 1)

            if nivel_usuario < nivel_minimo:
                flash("No tenés permisos suficientes para realizar esta acción.", "danger")
                return redirect(url_for('inicio'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

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
    #Para el control de stock, agregamos esta columna nueva. Por ahora no se muestra en ningún lado, pero ya queda guardada para usarla después.
    stock = db.Column(db.Integer, default=0)

             #Clase Opinion para armar el modelo en el que se van a guardar los datos en el .db

class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True) #Esto hace que el cerebro los vuelva unicos y los va colocando 1,2,3.
    nombre_cliente = db.Column(db.String(100)) #Espacio para el nombre del cliente de maximo 100 letras.
    comentario = db.Column(db.Text, nullable=False) # El texto que escriben, nullable para que no se guarde vacio.

with app.app_context():
    db.create_all()

# CLASE PARA MANEJAR EL CARRITO DE COMPRAS (GUARDADO EN SESIÓN)

class Carrito:
    def __init__(self, session_flask):
        self.session = session_flask
        # Ahora inicializamos como un diccionario vacío si no existe
        if 'carrito' not in self.session:
            self.session['carrito'] = {} 

    def agregar(self, producto_id):
        # Convertimos el ID a string porque las claves de sesión en Flask deben ser texto
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        
        # Si ya está, sumamos 1. Si no, empezamos en 1.
        if p_id in carrito:
            carrito[p_id] += 1
        else:
            carrito[p_id] = 1
            
        self.session['carrito'] = carrito
        self.session.modified = True

    def quitar(self, producto_id):
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        if p_id in carrito:
            del carrito[p_id] # Borra toda la fila del producto
            self.session['carrito'] = carrito
            self.session.modified = True

    def obtener_datos(self, modelo_producto):
        carrito_dict = self.session.get('carrito', {})
        productos_reales = []
        total_general = 0
        total_unidades = 0  # <--- Nueva variable
        
        for p_id, cantidad in carrito_dict.items():
            p = modelo_producto.query.get(int(p_id))
            if p:
                subtotal = p.precio * cantidad
                total_general += subtotal
                total_unidades += cantidad  # <--- Sumamos las cantidades reales
                # Creamos un objeto temporal para el HTML con la cantidad y subtotal
                productos_reales.append({
                    'id': p.id,
                    'nombre': p.nombre,
                    'precio': p.precio,
                    'cantidad': cantidad,
                    'subtotal': subtotal
                })
        return productos_reales, total_general, total_unidades

    def restar(self, producto_id):
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        if p_id in carrito:
            carrito[p_id] -= 1
            if carrito[p_id] <= 0:
                del carrito[p_id] # Si llega a 0, eliminamos la fila
            self.session['carrito'] = carrito
            self.session.modified = True
# --- TUS RUTAS ---

#Aca se guarda el nombre y la opinion que se sacaron de la sesion y de la opinion en el archivo.db
@app.route('/enviar_opinion', methods=['POST'])
def enviar_opinion():
    # A. CAPTURA: Agarramos lo que el usuario escribió en el HTML
    comentario_del_usuario = request.form.get('opinion_texto')
    
    # B. IDENTIDAD: Sacamos el nombre de la mochila (sesión) que vimos antes
    nombre_del_usuario = session.get('usuario_nombre', 'Anónimo')

    # C. CREACIÓN: Creamos "la ficha" con el modelo que diseñamos en el Paso 1
    nueva_op = Opinion(nombre_cliente=nombre_del_usuario, comentario=comentario_del_usuario)

    # D. GUARDADO: Metemos la ficha en la base de datos
    db.session.add(nueva_op)  # Esto la deja en "espera"
    db.session.commit()       # Esto es como darle a "Guardar" en el Word

    return redirect(url_for('inicio'))

@app.route('/opiniones')
def ver_opiniones():
    opiniones_db = Opinion.query.all() 
    return render_template('opiniones.html', opiniones=opiniones_db)

                                   #ELIMINAR OPINIONES
                                   
@app.route('/eliminar_opinion/<int:id>')
@requiere_nivel(5)
def eliminar_opinion(id):
    # SEGURIDAD: Solo el admin puede eliminar
    if session.get('usuario_rol') != 'admin':
        return "Acceso denegado", 403

    # Buscamos el producto por su ID
    opinion = Opinion.query.get(id)
    
    if opinion:
        db.session.delete(opinion) # Lo marcamos para borrar
        db.session.commit()         # Confirmamos el cambio en la DB
    
    return redirect('/') # Volvemos al inicio para ver los cambios


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
            flash(f"¡Hola de nuevo, {user.nombre}!") 
            return redirect(url_for('inicio'))
        flash("Email o contraseña incorrectos")
        return redirect(url_for('vista_login'))
    return render_template('login.html')

# Carga los datos del carrito en todas las páginas para mostrarlos en el menú
@app.context_processor
def procesar_carrito():
    # Creamos el objeto carrito pasando la sesión actual
    mi_carrito = Carrito(session)
    
    # Obtenemos los items procesados (con cantidad y subtotal) y el total general
    items, total, unidades = mi_carrito.obtener_datos(Producto)
    
    # Retornamos las variables que usará base.html
    return dict(carrito_html=items, total_carrito=total, total_unidades=unidades)
@app.route('/agregar_al_carrito/<int:id>')
def agregar_al_carrito(id):
    # Verificamos si el usuario está logueado (opcional, según tu lógica)
    if 'usuario_nombre' not in session:
        flash("Debes iniciar sesión para comprar", "warning")
        return redirect('/login')

    # Instanciamos la clase y agregamos
    mi_carrito = Carrito(session)
    mi_carrito.agregar(id)
    
    # Buscamos el nombre para el mensaje flash
    producto = Producto.query.get(id)
    if producto:
        flash(f"¡{producto.nombre} agregado!", "success")
    
    # Redirigimos a la página anterior o al inicio
    return redirect(request.referrer or '/')

@app.route('/eliminar_del_carrito/<int:id>')
def eliminar_del_carrito(id):
    mi_carrito = Carrito(session)
    mi_carrito.quitar(id)
    
    flash("Producto quitado del carrito", "info")
    return redirect(request.referrer or '/')

@app.route('/restar_del_carrito/<int:id>')
def restar_del_carrito(id):
    mi_carrito = Carrito(session)
    mi_carrito.restar(id)
    return redirect(request.referrer or '/')

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
    email = request.form.get('email')
    #BUSCAMOS si ya existe alguien con ese email
    usuario_existente = Usuario.query.filter_by(email = email ).first()

    #COMPARAMOS
    if usuario_existente: # Si existe, frenamos todo acá
        flash("Ese mail ya está en uso") # <--- El mensaje push
        return redirect(url_for('vista_registro'))
    
    #SI NO EXISTE, recién ahí creamos el nuevo
    db.session.add(nuevo) # Lo agregamos
    db.session.commit()   # Guardamos de verdad
    flash(f"¡Bienvenido {nuevo.nombre}! Usuario creado con exito.") # <--- El mensaje push
    return redirect(url_for('vista_login')) # <--- TE MANDA DIRECTO AL INICIO

# NUEVA RUTA PARA CARGAR PRODUCTOS (SOLO PARA ADMIN)
# Configuramos dónde se guardan las fotos
FOLDER_FOTOS = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = FOLDER_FOTOS

@app.route('/admin/nuevo_producto', methods=['GET', 'POST'])
@requiere_nivel(5) # Entra el Gestor (5) y el Admin (10)
def nuevo_producto():
    # VERIFICACIÓN DE SEGURIDAD
    if session.get('usuario_rol') != 'admin':
        return "<h1>Acceso denegado. Solo administradores.</h1>", 403
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = float(request.form.get('precio'))
        categoria = request.form.get('categoria')
        stock = int(request.form.get('stock', 0)) # Si no viene, asumimos 0
        descripcion = request.form.get('descripcion')        
        # --- LÓGICA PARA LA IMAGEN ---
        file = request.files.get('imagen') # Cambiamos .form por .files
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ruta_destino = os.path.join(app.root_path, 'static', 'img', filename)
            file.save(ruta_destino)
            nombre_imagen_db = filename
        else:
            nombre_imagen_db = "default.jpg" # Por si no suben nada
        
        
        
        nuevo = Producto(nombre=nombre, precio=precio, categoria=categoria, imagen=nombre_imagen_db, descripcion=descripcion, stock=stock)
        db.session.add(nuevo)
        db.session.commit()
        flash(f"¡Producto {nuevo.nombre}! agregado con exito.") # <--- El mensaje push
        return redirect(url_for('inicio')) # <--- TE MANDA DIRECTO AL INICIO
    # Si es GET, mostramos el formulario
    return render_template('cargar_producto.html')

#Ruta para eliminar productos (SOLO ADMIN)

@app.route('/eliminar_producto/<int:id>')
@requiere_nivel(5)
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
    
@app.route('/seccion/<categoria_nom>')
def ver_seccion(categoria_nom):
    # Buscamos los productos. 
    # IMPORTANTE: Asegúrate que en la base de datos sea 'Yerbas' y no 'yerbas'
    productos_filtrados = Producto.query.filter_by(categoria=categoria_nom).all()
    
    # Aquí le mandamos los productos a tu archivo productos.html
    return render_template('productos.html', productos=productos_filtrados, titulo=categoria_nom)
    
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
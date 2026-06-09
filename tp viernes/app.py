from flask import Flask, render_template, request, url_for, session, redirect, flash
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


# ==============================================================================
# 👤 CLASE USUARIO (Modelo de BD + Lógica de Negocio POO)
# ==============================================================================
class Usuario(db.Model):
    """
    Representa a los usuarios del sistema. Centraliza los procesos de 
    autenticación, registro y gestión de permisos (Roles).
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    # NUEVA COLUMNA:
    rol = db.Column(db.String(20), default='cliente')

    @classmethod
    def registrar(cls, nombre, email, password, rol='cliente'):
        """
        Método de clase (POO) para dar de alta usuarios.
        Valida que el email no esté repetido antes de persistir en la BD.
        Retorna la instancia del usuario si tiene éxito, o None si el mail ya existe.
        """
        # BUSCAMOS si ya existe alguien con ese email
        if cls.query.filter_by(email=email).first():
            return None  # Si existe, frena la operación devolviendo None
        
        # SI NO EXISTE, recién ahí creamos el nuevo objeto
        nuevo_usuario = cls(nombre=nombre, email=email, password=password, rol=rol)
        db.session.add(nuevo_usuario) # Lo agregamos
        db.session.commit()           # Guardamos de verdad
        return nuevo_usuario

    @classmethod
    def autenticar(cls, email, password):
        """
        Método de clase (POO) para el Login.
        Busca en la DB la coincidencia exacta de email y contraseña.
        """
        return cls.query.filter_by(email=email, password=password).first()

    def actualizar_rol(self, nuevo_rol):
        """
        Método de instancia. Modifica el rol del usuario actual 
        y confirma el cambio en la base de datos.
        """
        self.rol = nuevo_rol
        db.session.commit()

    def eliminar(self):
        """
        Método de instancia. Borra al usuario actual de la base de datos 
        de forma definitiva.
        """
        db.session.delete(self)
        db.session.commit()


# ==============================================================================
# 🧉 CLASE PRODUCTO (Modelo de BD + Lógica de Catálogo POO)
# ==============================================================================
# NUEVA TABLA PARA STOCK
class Producto(db.Model):
    """
    Representa los artículos a la venta. Contiene la lógica de búsquedas 
    y el procesamiento técnico de carga de nuevos productos e imágenes.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    precio = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)

    @classmethod
    def buscar(cls, consulta):
        """
        Este método busca productos que coincidan con la consulta
        en el nombre o en la descripción.
        """
        # Convertimos la consulta a minúsculas para que no importe si escriben con Mayúsculas
        termino = f"%{consulta}%"
        
        # Usamos el operador 'or_' (representado por |) para buscar en varios campos a la vez
        return cls.query.filter(
            (cls.nombre.ilike(termino)) | 
            (cls.descripcion.ilike(termino))
        ).all()

    @classmethod
    def guardar_nuevo(cls, datos_form, archivo_imagen):
        """
        Método de clase (POO). Desacopla la lógica de guardado de la ruta.
        Procesa los campos de texto, evalúa la subida del archivo de imagen
        utilizando secure_filename y guarda el Producto.
        """
        # --- LÓGICA PARA LA IMAGEN ---
        if archivo_imagen and archivo_imagen.filename != '':
            filename = secure_filename(archivo_imagen.filename)
            ruta_destino = os.path.join(app.root_path, 'static', 'img', filename)
            archivo_imagen.save(ruta_destino)
            nombre_imagen_db = filename
        else:
            nombre_imagen_db = "default.jpg" # Por si no suben nada

        nuevo_prod = cls(
            nombre=datos_form.get('nombre'),
            precio=float(datos_form.get('precio')),
            categoria=datos_form.get('categoria'),
            stock=int(datos_form.get('stock', 0)), # Si no viene, asumimos 0
            descripcion=datos_form.get('descripcion'),
            imagen=nombre_imagen_db
        )
        db.session.add(nuevo_prod)
        db.session.commit()
        return nuevo_prod

    def eliminar(self):
        """
        Método de instancia. Remueve el artículo del catálogo 
        y impacta el cambio en la base de datos.
        """
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        """Muestra una representación legible del objeto en la consola."""
        return f"<Producto: {self.nombre}>"


<<<<<<< HEAD
    @app.route('/admin/editar/<int:id>', methods=['GET', 'POST'])
    def editar_producto(id):
        # Buscamos el producto por ID (no usa classmethod porque SQLAlchemy ya busca por la clave primaria)
        producto = Producto.query.get_or_404(id) 

        if request.method == 'POST':
            # Tomamos los datos del formulario y los asignamos directo al objeto
            producto.nombre = request.form['nombre']
            producto.categoria = request.form['categoria']
            producto.precio = float(request.form['precio'])
            producto.descripcion = request.form['descripcion']
            producto.stock = int(request.form['stock'])
        
            # Manejo de la foto por si sube una nueva
            foto = request.files.get('imagen')
            if foto and foto.filename != '':
                producto.imagen = foto.filename
                foto.save(f"static/img/{foto.filename}")

            # Guardamos los cambios de este producto en la base de datos
            db.session.commit()
        
            return redirect(url_for('inicio'))

        return render_template('editar.html', producto=producto)

=======
# ==============================================================================
# 💬 CLASE OPINION (Modelo de BD + Lógica de Feedback POO)
# ==============================================================================
# Clase Opinion para armar el modelo en el que se van a guardar los datos en el .db
>>>>>>> 2f99269f5eb19bf92f2f16961f6a9563deac4e60
class Opinion(db.Model):
    """
    Modela el buzón de comentarios de los clientes de la tienda.
    """
    id = db.Column(db.Integer, primary_key=True) # Esto hace que el cerebro los vuelva unicos y los va colocando 1,2,3.
    nombre_cliente = db.Column(db.String(100)) # Espacio para el nombre del cliente de maximo 100 letras.
    comentario = db.Column(db.Text, nullable=False) # El texto que escriben, nullable para que no se guarde vacio.

    @classmethod
    def publicar(cls, comentario, nombre_usuario):
        """
        Método de clase (POO). Recibe el texto ingresado en el HTML 
        y el nombre del usuario recuperado de la sesión para crear la opinión.
        """
        nueva_op = cls(nombre_cliente=nombre_usuario, comentario=comentario)
        db.session.add(nueva_op)  # Esto la deja en "espera"
        db.session.commit()       # Esto es como darle a "Guardar" en el Word
        return nueva_op

    def eliminar(self):
        """
        Método de instancia. Borra permanentemente el comentario de la BD.
        """
        db.session.delete(self)
        db.session.commit()


# Inicialización de las tablas dentro del contexto de Flask
with app.app_context():
    db.create_all()


# ==============================================================================
# 🛒 CLASE PARA MANEJAR EL CARRITO DE COMPRAS (GUARDADO EN SESIÓN)
# ==============================================================================
class Carrito:
    """
    Clase de lógica pura de negocio. No persiste en la base de datos;
    manipula un diccionario de datos serializado dentro de la sesión de Flask.
    """
    def __init__(self, session_flask):
        """
        Constructor. Vincula la sesión activa e inicializa el contenedor 
        del carrito si el cliente no posee uno.
        """
        self.session = session_flask
        # Ahora inicializamos como un diccionario vacío si no existe
        if 'carrito' not in self.session:
            self.session['carrito'] = {} 

    def agregar(self, producto_id):
        """Suma un elemento al carrito o incrementa sus unidades."""
        # Convertimos el ID a string porque las claves de sesión en Flask deben ser texto
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        
        # Si ya está, sumamos 1. Si no, empezamos en 1.
        if p_id in carrito:
            carrito[p_id] += 1
        else:
            carrito[p_id] = 1
            
        self.session['carrito'] = carrito
        self.session.modified = True # Le avisa a Flask que la cookie cambió

    def quitar(self, producto_id):
        """Borra la clave entera del diccionario, eliminando el producto."""
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        if p_id in carrito:
            del carrito[p_id] # Borra toda la fila del producto
            self.session['carrito'] = carrito
            self.session.modified = True

    def restar(self, producto_id):
        """Resta una unidad. Si el contador llega a cero, remueve el artículo."""
        p_id = str(producto_id)
        carrito = self.session.get('carrito', {})
        if p_id in carrito:
            carrito[p_id] -= 1
            if carrito[p_id] <= 0:
                del carrito[p_id] # Si llega a 0, eliminamos la fila
            self.session['carrito'] = carrito
            self.session.modified = True

    def obtener_datos(self, modelo_producto):
        """
        Cruza los IDs del carrito de sesión con la base de datos (modelo Producto).
        Calcula subtotales individuales, el total de dinero y unidades totales.
        Retorna la estructura procesada lista para las plantillas HTML.
        """
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


# ==============================================================================
# 🛣️ RUTAS DE FLASK (Controladores resumidos)
# ==============================================================================

# Carga los datos del carrito en todas las páginas para mostrarlos en el menú
@app.context_processor
def procesar_carrito():
    # Creamos el objeto carrito pasando la sesión actual
    mi_carrito = Carrito(session)
    # Obtenemos los items procesados (con cantidad y subtotal) y el total general
    items, total, unidades = mi_carrito.obtener_datos(Producto)
    # Retornamos las variables que usará base.html
    return dict(carrito_html=items, total_carrito=total, total_unidades=unidades)


@app.route('/')
def inicio():
    # Buscamos todos los productos en la base de datos y se los pasamos al HTML
    return render_template('inicio.html', productos=Producto.query.all())


# RUTA PARA BUSCAR PRODUCTOS DESDE EL FORMULARIO DE BÚSQUEDA
@app.route('/buscar')
def buscar():
    query = request.args.get('q', '').strip()
    
    if query:
        # Usamos el método de la Clase Producto (POO)
        resultados = Producto.buscar(query)
    else:
        resultados = Producto.query.all()

    # IMPORTANTE: Mandamos los resultados a 'productos.html' 
    # porque ya tiene el bucle FOR preparado para mostrar muchos items
    return render_template('productos.html', productos=resultados, busqueda=query)


@app.route('/seccion/<categoria_nom>')
def ver_seccion(categoria_nom):
    # Buscamos los productos. 
    # IMPORTANTE: Asegúrate que en la base de datos sea 'Yerbas' y no 'yerbas'
    productos_filtrados = Producto.query.filter_by(categoria=categoria_nom).all()
    # Aquí le mandamos los productos a tu archivo productos.html
    return render_template('productos.html', productos=productos_filtrados, titulo=categoria_nom)


# Ruta para ver el detalle de un producto (con su descripción, imagen, etc)
@app.route('/detalle/<int:id>')
def detalle_producto(id):
    # Buscamos el producto específico por su ID único. Si no existe lanza un 404 limpio.
    p = Producto.query.get_or_404(id)
    return render_template('detalle.html', producto=p)


# --- CONTROL DE ACCESO (LOGIN / LOGOUT / REGISTRO) ---

@app.route('/login', methods=['GET', 'POST'])
def vista_login():
    if request.method == 'POST':
        # Validamos credenciales usando el método estático de Usuario
        user = Usuario.autenticar(request.form.get('email'), request.form.get('password'))
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


# RUTA PARA CERRAR SESIÓN
@app.route('/logout')
def logout():
    session.clear() # Borra todo lo guardado en la mochila (sesión)
    return redirect('/')


@app.route('/registro')
def vista_registro():
    return render_template('registro.html')


@app.route('/registrar_usuario', methods=['POST'])
def registrar_usuario():
    # Delegamos la creación y validación de correo único a la propia clase Usuario
    nuevo = Usuario.registrar(request.form.get('nombre'), request.form.get('email'), request.form.get('password'))
    
    if not nuevo: # Si devolvió None significa que el correo ya estaba tomado
        flash("Ese mail ya está en uso") # <--- El mensaje push
        return redirect(url_for('vista_registro'))
    
    flash(f"¡Bienvenido {nuevo.nombre}! Usuario creado con exito.") # <--- El mensaje push
    return redirect(url_for('vista_login')) # <--- TE MANDA DIRECTO AL LOGIN


# --- FEEDBACK Y OPINIONES ---

# Aca se guarda el nombre y la opinion que se sacaron de la sesion y de la opinion en el archivo.db
@app.route('/enviar_opinion', methods=['POST'])
def enviar_opinion():
    # A. CAPTURA Y B. IDENTIDAD: Extraemos el texto y sacamos el nombre de la mochila (sesión)
    comentario_del_usuario = request.form.get('opinion_texto')
    nombre_del_usuario = session.get('usuario_nombre', 'Anónimo')

    # C, D y E. PROCESO POO: La clase gestiona la creación y guardado interno
    Opinion.publicar(comentario_del_usuario, nombre_del_usuario)
    return redirect(url_for('inicio'))


@app.route('/opiniones')
def ver_opiniones():
    return render_template('opiniones.html', opiniones=Opinion.query.all())


# ELIMINAR OPINIONES
@app.route('/eliminar_opinion/<int:id>')
@requiere_nivel(5)
def eliminar_opinion(id):
    # SEGURIDAD INTERNA: Doble chequeo estricto para el administrador
    if session.get('usuario_rol') != 'admin':
        return "Acceso denegado", 403

    opinion = Opinion.query.get_or_404(id)
    opinion.eliminar() # El objeto se elimina a sí mismo de la DB
    return redirect('/') # Volvemos al inicio para ver los cambios


# --- INTERACCIÓN INTERACTIVA CON EL CARRITO ---

@app.route('/agregar_al_carrito/<int:id>')
def agregar_al_carrito(id):
    # Verificamos si el usuario está logueado
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


# ==============================================================================
# 🛠️ PANEL DE CONTROL Y ADMINISTRACIÓN (SOLO ADMIN / ROL REQUERIDO)
# ==============================================================================

FOLDER_FOTOS = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = FOLDER_FOTOS

# NUEVA RUTA PARA CARGAR PRODUCTOS (SOLO PARA ADMIN)
@app.route('/admin/nuevo_producto', methods=['GET', 'POST'])
@requiere_nivel(5) # Entra el Gestor (5) y el Admin (10)
def nuevo_producto():
    # VERIFICACIÓN DE SEGURIDAD
    if session.get('usuario_rol') != 'admin':
        return "<h1>Acceso denegado. Solo administradores.</h1>", 403
    
    if request.method == 'POST':
        # La clase Producto procesa el request.form y request.files de forma interna
        nuevo = Producto.guardar_nuevo(request.form, request.files.get('imagen'))
        flash(f"¡Producto {nuevo.nombre}! agregado con exito.") # <--- El mensaje push
        return redirect(url_for('inicio')) # <--- TE MANDA DIRECTO AL INICIO
    
    # Si es GET, mostramos el formulario de carga
    return render_template('cargar_producto.html')


# Ruta para eliminar productos (SOLO ADMIN)
@app.route('/eliminar_producto/<int:id>')
@requiere_nivel(5)
def eliminar_producto(id):
    # SEGURIDAD: Solo el admin puede eliminar
    if session.get('usuario_rol') != 'admin':
        return "Acceso denegado", 403

    producto = Producto.query.get_or_404(id)
    producto.eliminar() # El objeto ejecuta su propio borrado de la base de datos
    return redirect('/') # Volvemos al inicio para ver los cambios


# RUTA PARA LISTAR USUARIOS (SOLO ADMIN)
@app.route('/admin/usuarios')
@requiere_nivel(10) # Solo el Administrador absoluto
def lista_usuarios():
    return render_template('admin_usuarios.html', usuarios=Usuario.query.all())


# RUTA PARA CAMBIAR EL ROL DE UN USUARIO (SOLO ADMIN)
@app.route('/admin/cambiar_rol/<int:id>/<nuevo_rol>')
@requiere_nivel(10)
def cambiar_rol(id, nuevo_rol):
    user = Usuario.query.get_or_404(id)
    user.actualizar_rol(nuevo_rol) # Llamamos al método POO del usuario
    flash(f"Rol de {user.nombre} actualizado a {nuevo_rol}")
    return redirect(url_for('lista_usuarios'))


# RUTA PARA CREAR USUARIOS DIRECTAMENTE DESDE EL PANEL (SOLO ADMIN)
@app.route('/admin/crear_usuario', methods=['GET', 'POST'])
@requiere_nivel(10) # Solo el Admin (Dueño) puede usar esta ruta
def admin_crear_usuario():
    if request.method == 'POST':
        # Reutilizamos de forma limpia el método .registrar() de la clase Usuario pasando el rol elegido
        nuevo = Usuario.registrar(
            nombre=request.form.get('nombre'),
            email=request.form.get('email'),
            password=request.form.get('password'),
            rol=request.form.get('rol') # El admin elige: admin, gestor o cliente
        )
        
        if not nuevo:
            flash(f"Error: El email ya está registrado.", "danger")
            return redirect(url_for('admin_crear_usuario'))

        flash(f"¡Usuario {nuevo.nombre} creado con éxito como {nuevo.rol}!", "success")
        return redirect(url_for('lista_usuarios'))

    # Si es GET, simplemente mostramos el formulario
    return render_template('admin_crear_usuario.html')


# RUTA PARA ELIMINAR USUARIOS (SOLO ADMIN)
@app.route('/admin/eliminar_usuario/<int:id>')
@requiere_nivel(10)
def eliminar_usuario(id):
    user = Usuario.query.get_or_404(id)
    user.eliminar() # El usuario se autoelimina de la base de datos
    flash(f"Usuario eliminado.")
    return redirect(url_for('lista_usuarios'))


# RUTA PARA VER EL PANEL DE CONTROL CON ESTADÍSTICAS (SOLO ADMIN)
@app.route('/admin/dashboard')
@requiere_nivel(10) # Solo el Administrador absoluto tiene acceso
def dashboard():
    # Renderizamos la plantilla pasando los conteos directos de las clases
    return render_template('admin/dashboard.html', 
                           u_total=Usuario.query.count(), 
                           p_total=Producto.query.count())


# SE CREA UN ADMIN INICIAL PARA PODER PROBAR EL PANEL DE ADMINISTRACIÓN
@app.route('/crear_admin_inicial')
def crear_admin():
    # Usamos la lógica integrada para generar el administrador inicial si la DB está vacía
    admin = Usuario.registrar("Admin", "admin@mateargento.com", "123", rol="admin")
    if admin:
        return "Administrador creado. Email: admin@mateargento.com, Pass: 123"
    
    return "El admin ya existe."


if __name__ == '__main__':
    app.run(debug=True)
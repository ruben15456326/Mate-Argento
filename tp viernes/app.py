from flask import Flask, render_template, request, url_for, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func 
import os
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

#comentario inicial para probar el git
#hola
app = Flask(__name__)
app.secret_key = 'mi_llave_secreta_super_segura'
ts = URLSafeTimedSerializer("CLAVE_SECRETA_PARA_EL_TOKEN")

# Configuración mínima para que funcione la base de datos
db_path = os.path.join(os.path.dirname(__file__), 'mate_argento.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)


# =====================================================================
# CONFIGURACIÓN DEL MOTOR DE MAIL
# =====================================================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'ruben650160@gmail.com'
app.config['MAIL_PASSWORD'] = 'gwwuxyrjezjiwodr'     
app.config['MAIL_DEFAULT_SENDER'] = 'ruben650160@gmail.com'

# Inicializamos el mail acá arriba para que todas las rutas lo vean
mail = Mail(app)

# --- CONFIGURACIÓN DE ROLES Y NIVELES ---
# Definimos el "poder" de cada rol. Cuanto más alto el número, más permisos.
NIVELES_ACCESO = {
    'cliente': 1,
    'gestor': 5,
    'admin': 10
}

#agregado para poder tener las categorias de los productos a mano y no en los html
CATEGORIAS_DATA = [
    {'nombre': 'Conservadoras', 'imagen': 'conservadora.jpg'},
    {'nombre': 'Juego de Pava', 'imagen': 'juego_pava.webp'},
    {'nombre': 'Chopera', 'imagen': 'chopera.jpg'},
    {'nombre': 'Cuchillos', 'imagen': 'Cuchillos.jpg'},
    {'nombre': 'Regalos Empresariales', 'imagen': 'regalo.jpg'},
    {'nombre': 'Autocebantes', 'imagen': 'autocebantes.webp'},
    {'nombre': 'Cafe x Mayor', 'imagen': 'Cafe.jpg'},
    {'nombre': 'Carteras', 'imagen': 'cartera.jpg'},
    {'nombre': 'Kits de Futbol', 'imagen': 'equipos.webp'},
    {'nombre': 'Kits Economicos', 'imagen': 'economicos.webp'},
    {'nombre': 'Kits con Mochila', 'imagen': 'set_mochila.webp'},
    {'nombre': 'Kits para Mujeres', 'imagen': 'kits_dama.webp'},
    {'nombre': 'Yerbas', 'imagen': 'yerbat.png.'}
    {'nombre': 'Mates', 'imagen': 'madera.webp'},
    {'nombre': 'Bombillas', 'imagen': 'pico_loro.jpg'},
    {'nombre': 'Termos', 'imagen': 'termo.jpg'}
]
@app.context_processor
def inject_categorias():
    # Esto hace que 'todas_las_categorias' esté disponible en todos los HTML
    return dict(todas_las_categorias=CATEGORIAS_DATA)

# DECORADOR PARA VALIDAR NIVELES DE ACCESO
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

def generar_token(email):
    return ts.dumps(email, salt='recuperar-password')

def verificar_token(token, expiration=3600):
    try:
        email = ts.loads(token, salt='recuperar-password', max_age=expiration)
        return email
    except:
        return None

#  CLASE USUARIO (Modelo de BD + Lógica de Negocio POO)

class Usuario(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(500), nullable=False)
    rol = db.Column(db.String(20), default='cliente')
    activo = db.Column(db.Boolean, default=False) 
    bloqueado = db.Column(db.Integer, default=0)

    @classmethod
    def registrar(cls, nombre, email, password, rol='cliente'):
       
        #Método de clase (POO) para dar de alta usuarios.
        #Valida que el email no esté repetido antes de persistir en la BD.
        #Retorna la instancia del usuario si tiene éxito, o None si el mail ya existe.
       
        # BUSCAMOS si ya existe alguien con ese email
        if cls.query.filter_by(email=email).first():
            return None  # Si existe, frena la operación devolviendo None
        new_password=generate_password_hash(password)
        
        # SI NO EXISTE, recién ahí creamos el nuevo objeto
        nuevo_usuario = cls(nombre=nombre, email=email, password=new_password, rol=rol, activo=True)
        db.session.add(nuevo_usuario) # Lo agregamos
        db.session.commit()           # Guardamos de verdad
        return nuevo_usuario
    
    @classmethod
    def autenticar(cls, email, password):
        user = cls.query.filter_by(email=email).first()
        
        if user:
            # Caso A: Si es un hash (lo nuevo)
            if user.password.startswith('scrypt:'): 
                if check_password_hash(user.password, password):
                    return user
            # Caso B: Si es texto plano (lo viejo/admin)
            elif user.password == password:
                return user
                
        return None

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
    # --- NUEVOS MÉTODOS DE OBJETO ---

    def alternar_estado_usuario(self):
        # Si está bloqueado (1), lo desbloqueamos (0). Si no, lo bloqueamos (1).
        if self.bloqueado == 1:
            self.bloqueado = 0
        else:
            self.bloqueado = 1
        
        db.session.commit()
        return self.bloqueado # Devuelve el estado final
    
    def actualizar_rol_usuario(self, nuevo_rol):
    #Valida y actualiza el rol del usuario
        roles_permitidos = ['cliente', 'gestor', 'admin']
        if nuevo_rol in roles_permitidos:
            self.rol = nuevo_rol
            db.session.commit()
            return True
        return False

# NUEVA TABLA PARA STOCK
class Producto(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    precio = db.Column(db.Float, nullable=False)
    precio_costo = db.Column(db.Float, nullable=False, default=0.0)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)

    @classmethod
    def buscar(cls, consulta):
        """
        Este método busca productos que coincidan con la consulta
        en el nombre o en la descripción.
        """
        termino = f"%{consulta}%"
        return cls.query.filter(
            (cls.nombre.ilike(termino)) | 
            (cls.descripcion.ilike(termino))
        ).all()

    @classmethod
    def guardar_nuevo(cls, datos_form, archivo_imagen):
        
        #Método de clase (POO). Desacopla la lógica de guardado de la ruta.
        #Procesa los campos de texto, evalúa la subida del archivo de imagen
        #utilizando secure_filename y guarda el Producto.
        
        if archivo_imagen and archivo_imagen.filename != '':
            filename = secure_filename(archivo_imagen.filename)
            ruta_destino = os.path.join(app.root_path, 'static', 'img', filename)
            archivo_imagen.save(ruta_destino)
            nombre_imagen_db = filename
        else:
            nombre_imagen_db = "default.jpg"

        # --- [NUEVO] FILTRO INTELIGENTE DE CATEGORÍA ---
        nueva_cat = datos_form.get('nueva_categoria')
        if nueva_cat and nueva_cat.strip() != "":
            # Si el admin inventó una categoría en el campo de texto, usamos esa
            categoria_final = nueva_cat.strip()
        else:
            # Si ese campo quedó vacío, agarramos la que seleccionó del select
            categoria_final = datos_form.get('categoria')

        # --- CREACIÓN DEL PRODUCTO ---
        nuevo_prod = cls(
            nombre=datos_form.get('nombre'),
            precio=float(datos_form.get('precio')),
            precio_costo=float(datos_form.get('precio_costo')),
            categoria=datos_form.get('categoria'),
            stock=int(datos_form.get('stock', 0)),
            descripcion=datos_form.get('descripcion'),
            imagen=nombre_imagen_db
        )
        db.session.add(nuevo_prod)
        db.session.commit()
        return nuevo_prod

    @classmethod
    def obtener_mas_vendido_por_categoria(cls, nombre_categoria):
        """
        Método de clase (POO). Consulta los detalles de ventas,
        suma las cantidades agrupadas por producto y devuelve el producto
        más vendido de la categoría especificada.
        Si nadie compró nada de esa categoría, devuelve el primero que encuentre.
        """
        # Hacemos un Join entre Producto y DetalleVenta para sumar las cantidades
        resultado = db.session.query(
            cls, 
            func.sum(DetalleVenta.cantidad).label('total_vendido')
        ).join(DetalleVenta, cls.id == DetalleVenta.producto_id)\
         .filter(cls.categoria == nombre_categoria)\
         .group_by(cls.id)\
         .order_by(func.sum(DetalleVenta.cantidad).desc())\
         .first()

        # Si la consulta trajo un resultado, devolvemos el objeto Producto (el primer elemento de la tupla)
        if resultado:
            return resultado[0]
        
        # Si la tienda es nueva o nadie compró de esa categoría todavía,
        # tiramos un fallback al primer producto de esa categoría para que la web no rompa
        return cls.query.filter_by(categoria=nombre_categoria).first()
    #  NUEVO MÉTODO AGREGADO (MÉTODO DE INSTANCIA) 
    def actualizar_datos(self, datos_form, archivo_imagen):
        """
        Método de instancia (POO). Permite al objeto modificarse a sí mismo
        procesando los datos del formulario de edición.
        Si se sube una nueva imagen, se guarda; si no, conserva la actual.
        """
        self.nombre = datos_form.get('nombre')
        self.precio = float(datos_form.get('precio'))
        self.precio_costo=float(datos_form.get('precio_costo'))
        self.categoria = datos_form.get('categoria')
        self.stock = int(datos_form.get('stock', 0))
        self.descripcion = datos_form.get('descripcion')
        

        # Controlamos si el usuario subió un archivo de imagen nuevo
        if archivo_imagen and archivo_imagen.filename != '':
            filename = secure_filename(archivo_imagen.filename)
            ruta_destino = os.path.join(app.root_path, 'static', 'img', filename)
            archivo_imagen.save(ruta_destino)
            self.imagen = filename  # Reemplazamos por la nueva foto

        # Guardamos todos los cambios en la Base de Datos
        db.session.commit()
        return self

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

class Venta(db.Model):
    __tablename__ = 'ventas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Relación con tu usuario
    fecha = db.Column(db.String(20), nullable=False, default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    total = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='Completado')

    # Relación inversa para sacar los renglones de la venta directo en Flask
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)

    @classmethod
    def registrar_desde_carrito(cls, usuario_id, items_compra):
        
        #LÓGICA POO: Valida stock, resta cantidades en los objetos de la DB,
        #y guarda la cabecera y el detalle de la venta.
        
        if not items_compra:
            raise ValueError("El carrito está vacío.")

        total_venta = 0
        renglones_a_guardar = []

        # 1. Validaciones previas de negocio
        for item in items_compra:
            producto = item['producto']
            cantidad = item['cantidad']

            if producto.stock < cantidad:
                raise ValueError(f"Stock insuficiente para: {producto.nombre} (Disponibles: {producto.stock})")

            subtotal = producto.precio * cantidad
            total_venta += subtotal

            # Armamos la instancia del detalle (renglón)
            nuevo_detalle = DetalleVenta(
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=producto.precio
            )
            renglones_a_guardar.append((producto, cantidad, nuevo_detalle))

        # 2. Si todo el stock es correcto, creamos la Venta
        nueva_venta = cls(usuario_id=usuario_id, total=total_venta)
        db.session.add(nueva_venta)
        db.session.flush()  # Obtiene el ID de la venta de forma intermedia

        # 3. Descontamos stock físico y asociamos los renglones
        for producto, cantidad, detalle in renglones_a_guardar:
            producto.stock -= cantidad  # Resta directa sobre el modelo Producto
            detalle.venta_id = nueva_venta.id
            db.session.add(detalle)

        # 4. Impactamos los cambios de forma transaccional y masiva
        db.session.commit()
        return nueva_venta


class DetalleVenta(db.Model):
    __tablename__ = 'detalles_ventas'
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)

    # Relación para acceder a los datos del producto comprado (ej: detalle.producto.nombre)
    producto = db.relationship('Producto')
    
    
    
#  CLASE OPINION (Modelo de BD + Lógica de Feedback POO)

# Clase Opinion para armar el modelo en el que se van a guardar los datos en el .db
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



# CLASE PARA MANEJAR EL CARRITO DE COMPRAS (GUARDADO EN SESIÓN)

class Carrito:
    
    # Clase de lógica pura de negocio. No persiste en la base de datos;
    # manipula un diccionario de datos serializado dentro de la sesión de Flask.
    
    def __init__(self, session_flask):
        
       # Constructor. Vincula la sesión activa e inicializa el contenedor 
       # del carrito si el cliente no posee uno.
        
        self.session = session_flask
        # Ahora inicializamos como un diccionario vacío si no existe
        if 'carrito' not in self.session:
            self.session['carrito'] = {} 

    def agregar(self, producto_id):
        #Suma un elemento al carrito o incrementa sus unidades."""
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
# RUTAS DE FLASK (Controladores resumidos)
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
    # Traemos el más vendido de cada una de las 4 categorías destacadas
    mas_vendidos = {
        'Yerbas': Producto.obtener_mas_vendido_por_categoria('Yerbas'),
        'Mates': Producto.obtener_mas_vendido_por_categoria('Mates'),
        'Bombillas': Producto.obtener_mas_vendido_por_categoria('Bombillas'),
        'Termos': Producto.obtener_mas_vendido_por_categoria('Termos')
    }
    
    # CORRECCIÓN AQUÍ: Consultamos las últimas 4 opiniones de la base de datos
    ultimas_opiniones = Opinion.query.order_by(Opinion.id.desc()).limit(4).all()
    
    # Pasamos todos los productos, los destacados y la nueva lista de opiniones
    return render_template('inicio.html', 
                           productos=Producto.query.all(), 
                           destacados=mas_vendidos, 
                           opiniones=ultimas_opiniones)


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

@app.route('/todos_productos')
def todos_los_productos():
    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

# --- CONTROL DE ACCESO (LOGIN / LOGOUT / REGISTRO) ---

@app.route('/login', methods=['GET', 'POST'])
def vista_login():
    if request.method == 'POST':
        # Validamos credenciales usando el método estático de Usuario
        user = Usuario.autenticar(request.form.get('email'), request.form.get('password'))
        
        if user:
            # Si el rol sigue siendo 'pendiente' (o el valor por defecto de tu BD), lo frenamos
            if not user.activo:
                flash("Tu cuenta aún no está verificada. Por favor, revisá tu correo para activarla.")
                return redirect(url_for('vista_login'))
            if user.bloqueado == 1:
                flash("Tu cuenta ha sido bloqueada por un administrador.")
                return redirect(url_for('vista_login'))
            
            # SI ESTÁ ACTIVO, PASA DERECHO Y SE GUARDA EN LA SESIÓN:
            session['usuario_id'] = user.id
            session['usuario_nombre'] = user.nombre
            session['usuario_rol'] = user.rol
            flash(f"¡Hola de nuevo, {user.nombre}!") 
            return redirect(url_for('inicio'))
        else:
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
    # 1. Tu modelo original de siempre
    nuevo = Usuario.registrar(request.form.get('nombre'), request.form.get('email'), request.form.get('password'))
    
    if not nuevo:
        flash("Ese mail ya está en uso") 
        return redirect(url_for('vista_registro'))
    
    def enviar_mail_verificacion_local(correo_usuario):
        # Usamos el serializador que está abajo de todo
        token = ts.dumps(correo_usuario, salt='activar-cuenta')
        link_verificacion = url_for('confirmar_email', token=token, _external=True)
        
        msg = Message(subject="Verificá tu cuenta de Mate Argento", recipients=[correo_usuario])
        msg.body = f"Para activar tu cuenta, hace click acá: {link_verificacion}"
        mail.send(msg)
        print("--- EL MAIL SALIÓ DE LA APP CON ÉXITO ---")

    # 2. LA EJECUTAMOS INMEDIATAMENTE
    try:
        enviar_mail_verificacion_local(nuevo.email)
    except Exception as e:
        print(f"--- ERROR CRÍTICO AL ENVIAR EL MAIL: {e} ---")

    # 3. Te manda al login con el cartel como siempre
    flash(f"¡Usuario creado! Te enviamos un mail a {nuevo.email} para verificar tu cuenta.") 
    return redirect(url_for('vista_login'))

@app.route('/confirmar/<token>')
def confirmar_email(token):
    try:
        email = ts.loads(token, salt='activar-cuenta', max_age=86400)
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.activo = True
            db.session.commit()
            return "<h1>¡Cuenta verificada con éxito!</h1><p>Ya podés cerrar esta pestaña y loguearte.</p>"
        return "Usuario no encontrado."
    except Exception as e:
        return "<h1>El enlace es inválido o ya venció.</h1>"

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



# RUTA PARA FNALIZAR LA COMPRA
@app.route('/carrito/finalizar', methods=['POST'])
def finalizar_compra():
    # 1. Seguridad: Verificamos si hay un usuario logueado en la sesión
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        flash("Debés iniciar sesión para finalizar la compra.", "danger")
        return redirect(url_for('inicio')) # O a tu ruta de login

    # 2. Recuperamos el carrito de la sesión
    # Ajustá 'carrito' por el nombre exacto que le diste en tu session
    carrito_sesion = session.get('carrito', {})

    if not carrito_sesion:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for('inicio'))

    # 3. Estructuramos los objetos trayéndolos desde la BD
    items_compra = []
    for prod_id, cantidad in carrito_sesion.items():
        producto = Producto.query.get(int(prod_id))
        if producto:
            items_compra.append({
                'producto': producto,
                'cantidad': int(cantidad)
            })

    # 4. Ejecutamos el motor de compras
    try:
        # Invocamos la lógica rica de POO
        nueva_venta = Venta.registrar_desde_carrito(
            usuario_id=usuario_id, 
            items_compra=items_compra
        )
        
        # 5. Éxito: Limpiamos el carrito de la sesión para que quede en 0
        session['carrito'] = {}
        session.modified = True # Le avisa a Flask que la sesión cambió
        
        flash(f"🛒 ¡Compra registrada con éxito! Pedido N° {nueva_venta.id}.", "success")
        return redirect(url_for('inicio'))

    except ValueError as e:
        # Si falló el stock, atrapamos el mensaje y lo mandamos a la pantalla
        flash(str(e), "danger")
        return redirect(url_for('inicio')) # O a la vista del carrito

# Asegurate de importar tu modelo, por ejemplo: from models import Usuario
# Si no tenés un archivo models.py, probablemente tengas la clase definida en app.py

@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        email = request.form['email']
        
        # BUSCAR USUARIO CON SQLALCHEMY
        # 'Usuario' debe ser el nombre de la clase que definiste para tu tabla
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            token = generar_token(email)
            link = url_for('resetear_password', token=token, _external=True)
            
            # Tu función de envío de mail (asegúrate de que esté definida)
            msg = Message("Recuperación de contraseña", recipients=[email])
            msg.body = f"Haz clic en el siguiente enlace para restablecer tu contraseña: {link}"
            mail.send(msg)
            
            flash("Si el correo existe, recibirás un mensaje en breve.")
        else:
            flash("Si el correo existe, recibirás un mensaje en breve.") # Por seguridad, no digas si existe o no
            
        return redirect(url_for('vista_login')) # O a donde prefieras
        
    return render_template('recuperar.html')

@app.route('/resetear-password/<token>', methods=['GET', 'POST'])
def resetear_password(token):
    email = verificar_token(token)
    if not email:
        flash("El token es inválido o expiró.")
        return redirect(url_for('vista_login'))
    
    if request.method == 'POST':
        nueva_password = request.form['password']
        
        # BUSCAR Y ACTUALIZAR CON SQLALCHEMY
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.password = generate_password_hash(nueva_password) # Hasheando la password
            db.session.add(usuario)
            db.session.commit()
            print(f"DEBUG: Contraseña guardada (hash): {usuario.password}")
            flash("Contraseña actualizada con éxito.")
            return redirect(url_for('vista_login'))
            
    return render_template('resetear.html', token=token)

# ==============================================================================
#  PANEL DE CONTROL Y ADMINISTRACIÓN (SOLO ADMIN / ROL REQUERIDO)
# ==============================================================================

FOLDER_FOTOS = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = FOLDER_FOTOS

# NUEVA RUTA PARA CARGAR PRODUCTOS (SOLO PARA ADMIN)
@app.route('/admin/nuevo_producto', methods=['GET', 'POST'])
@requiere_nivel(5) # Entra el Gestor (5) y el Admin (10)
def nuevo_producto():
    if request.method == 'POST':
        # Seguimos usando tu método de clase excelente que desacopla la creación
        Producto.guardar_nuevo(request.form, request.files.get('imagen'))
        
        flash("¡Nuevo producto agregado al catálogo con éxito!", "success")
        return redirect(url_for('lista_productos'))
    
    return render_template('cargar_producto.html')

# 3. RUTA EXCLUSIVA PARA EDITAR UN PRODUCTO EXISTENTE
@app.template_filter('dinero')
def formato_dinero(valor):
    if valor is None: return "0.00"
    # Esto convierte 159229000.0 en 159.229.000,00
    return "{:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")

@app.route('/admin/editar_producto/<int:id>', methods=['GET', 'POST'])
@requiere_nivel(5)
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        #Le pasamos el formulario y el archivo; el objeto hace el resto
        producto.actualizar_datos(request.form, request.files.get('imagen'))
        
        flash(f"¡Producto '{producto.nombre}' modificado con éxito!", "success")
        return redirect(url_for('lista_productos'))
        
    # Si es GET, abrimos el formulario de edición pasándole el objeto
    return render_template('editar_producto.html', producto=producto)

# RUTA LISTADO GENERAL DE PRODUCTOS
@app.route('/admin/productos')
@requiere_nivel(5)  # Permite que entren tanto gestores (5) como administradores (10)
def lista_productos():
    todos_los_productos = Producto.query.all()
    # Retornamos el HTML que creamos para listar los productos
    return render_template('admin_productos.html', productos=todos_los_productos)


# Ruta para Editar el Rol (SOLO PARA ADMIN)
@app.route('/admin/editar_rol/<int:id>', methods=['GET', 'POST'])
@requiere_nivel(10)
def editar_rol(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        nuevo_rol = request.form.get('rol')
        
        # Delegamos la validación y actualización al método del usuario
        if usuario.actualizar_rol_usuario(nuevo_rol):
            flash(f"Rol de {usuario.nombre} actualizado a {nuevo_rol} con éxito.", "success")
            return redirect(url_for('lista_usuarios'))
        else:
            flash("Error: Rol no válido seleccionado.", "danger")
            
    return render_template('editar_usuario.html', usuario=usuario)

# Ruta para Bloquear / Activar (SOLO PARA ADMIN)
@app.route('/admin/alternar_estado/<int:id>', methods=['POST'])
@requiere_nivel(10)
def alternar_estado(id):
    usuario = Usuario.query.get_or_404(id)
    
    # 1. Ejecutamos el cambio de estado (que ya hace el commit internamente)
    nuevo_estado = usuario.alternar_estado_usuario()
    
    # 2. Guardamos el nombre para el mensaje
    nombre_usuario = usuario.nombre
    
    # 3. Evaluamos el resultado: 
    # Si nuevo_estado es 1, significa que está ACTIVO (desbloqueado)
    # Si nuevo_estado es 0, significa que está BLOQUEADO
    if nuevo_estado == 1:
        flash(f"¡El usuario {nombre_usuario} ahora está BLOQUEADO!", "success")
    else:
        flash(f"¡El usuario {nombre_usuario} ha sido ACTIVADO con éxito!", "danger")
        
    return redirect(url_for('lista_usuarios'))
# Ruta para eliminar productos (SOLO ADMIN)
@app.route('/admin/eliminar_producto/<int:id>')
@requiere_nivel(5)
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    #  Invocamos el método de instancia que borra e impacta la BD
    producto.eliminar()
    
    flash(f"Producto '{producto.nombre}' eliminado con éxito.", "success")
    return redirect(url_for('lista_productos'))

# RUTA PARA AUDITAR Y VER LAS VENTAS DE LA TIENDA (SOLO ADMIN)
@app.route('/admin/ventas')
@requiere_nivel(10) # Al igual que el dashboard, solo entra el Admin absoluto
def lista_ventas():
    # 1. Traemos todas las ventas ordenadas desde la más nueva a la más vieja
    ventas_totales = Venta.query.order_by(Venta.id.desc()).all()

    # 2. Inicializamos los contadores para las métricas de negocio
    ingresos_brutos = 0.0
    costos_totales = 0.0
    ganancia_neta = 0.0

    # 3. Barremos las ventas y sus detalles calculando los márgenes reales
    for v in ventas_totales:
        ingresos_brutos += v.total
        
        # Recorremos cada renglón de cada venta
        for detalle in v.detalles:
            # Buscamos el precio al que compramos el producto al proveedor
            # Usamos un short-if por si algún producto viejo quedó en Null
            costo_unitario = detalle.producto.precio_costo if detalle.producto.precio_costo else 0.0
            
            # Costo total del renglón = costo de proveedor * cantidad que llevó el cliente
            costos_totales += (costo_unitario * detalle.cantidad)

    # La ganancia real es la facturación menos lo que nos costó la mercadería
    ganancia_neta = ingresos_brutos - costos_totales

    # 4. Renderizamos la plantilla pasándole los datos y las métricas formateadas
    return render_template(
        'admin_ventas.html',
        ventas=ventas_totales,
        ingresos=ingresos_brutos,
        ganancia=ganancia_neta,
        cantidad_pedidos=len(ventas_totales)
    )

# RUTA PARA LISTAR USUARIOS (SOLO ADMIN)
@app.route('/admin/usuarios')
@requiere_nivel(10) # Solo el Administrador absoluto
def lista_usuarios():
    db.session.expire_all()
    todos_los_usuarios = Usuario.query.all()    
    return render_template('admin_usuarios.html', usuarios=todos_los_usuarios)


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
    
    # CAMBIO: Usamos las herramientas directas de la base de datos
    db.session.delete(user) # Le decimos a la DB que borre este usuario
    db.session.commit()     # Guardamos el cambio definitivo
    
    flash(f"Usuario eliminado.")
    return redirect(url_for('lista_usuarios'))

# RUTA PARA VER EL PANEL DE CONTROL CON ESTADÍSTICAS (SOLO ADMIN)
@app.route('/admin/dashboard')
@requiere_nivel(5) 
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
    # Render asigna un puerto automáticamente en la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    # Escucha en 0.0.0.0 para ser accesible desde el exterior
    app.run(host="0.0.0.0", port=port, debug=False)
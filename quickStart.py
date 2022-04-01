import PySimpleGUI as sg
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import mysql.connector
from simplegmail import Gmail

# ----------------- Inicio de PySimpleGUI y configuracion inicial de la interfaz -------------------------------------------------------------------------
sg.theme('DefaultNoMoreNagging')
sg.theme_background_color('#ebebeb')
sg.theme_button_color(('black', '#fff159'))
sg.theme_input_text_color('black')
sg.theme_input_background_color('#ebebeb')
sg.theme_text_element_background_color('#ebebeb')

layout = [      
                [sg.pin(sg.Text('\n\nElegir opcion', key = 'stepone', visible = True))],
                [sg.Text()],
                [sg.Button('Chequear DB', key = 'checkdb', visible=True),
                sg.pin(sg.Button('Crear DB', key = 'createdb', visible=True)),
                sg.pin(sg.Button('Iniciar Programa', key = 'init', visible=True)),
                sg.pin(sg.Button('Volver', key = 'goback', visible=False))
            ]]

# ----------------- Declaracion de 2 booleans para que el programa pueda detectar la existencia o no de la DB --------------------------------------------
databaseExists = bool(False)
check = bool(False)
    
# ----------------- Inicio de la conexion con la DB ------------------------------------------------------------------------------------------------------
try:
    print("Ingresar datos de DataBase")
    database = mysql.connector.connect(
    host = input("DataBase Host: "),
    user = input("DataBase Usuario: "),
    password = input("DataBase Password: "))
# Mensaje de error en caso de que los datos sean incorrectos
except mysql.connector.errors.DatabaseError:
       print("ERROR: Los datos de login de la base de datos son incorrectos")
       exit()


# ----------------- Declaracion del Cursor para el uso de la DB (Buffered para que funcione con loops) ---------------------------------------------------
sqlcursor = database.cursor(buffered = True)

# ----------------- Inicio de autenticacion con Google Account y Gmail----------------------------------------------------------------------------------------
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)
gmail = Gmail()

# ----------------- Obtencion de lista de archivos de Drive con los datos obtenidos anteriormente ---------------------------------------
fileList = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
# Cabe destacar que usamos la carpeta "root" la cual contiene todos los archivos de nuestro drive, y no incluimos los archivos en trash

# ----------------- Definir funcion para chequear si la DB existe ----------------------------------------------------------------------
def checkdb():
    #Aca hay una reiteracion de variable pero es la unica forma en la cual funciona
    databaseExists = bool(False)
    #Ejecutamos funcion SHOW DATABASES
    sqlcursor.execute("SHOW DATABASES")
    #Traemos el dato a un For
    for x in sqlcursor:
        #Si alguno de los datos es gdrive_database, convertimos el bool a true
        if x[0] == "gdrive_database":
            databaseExists = bool(True)
    #Si el bool es true, informamos que la database existe, y la ponemos en uso
    if databaseExists is True:
        print("La base de datos ya existe")
        sqlcursor.execute("USE gdrive_database")
    #En caso de que sea falso, declaramos el valor como falso
    else:
        databaseExists = bool(False)
    #Retornamos el valor del bool para posterior utilizacion
    return(databaseExists)
    
# -------------------------------- Funcion para crear DataBase --------------------------------------------------------------------------
def createdb():
    #Try para crear la DB solamente en caso de que no este creada
    try:
        #Utilizacion de diferentes comandos para crear la DB
        sqlcursor.execute("CREATE DATABASE gdrive_database")
        sqlcursor.execute("USE gdrive_database")
        sqlcursor.execute("CREATE TABLE inventario (id VARCHAR(255) PRIMARY KEY, nombre VARCHAR(255), owner VARCHAR(255), extension VARCHAR(255), modificacion VARCHAR(255), publico VARCHAR(5))")
        print("Base y Tabla Creadas")
        #Si ya esta creada, lo informamos al usuario
    except mysql.connector.errors.DatabaseError:
        sg.Print("La base de datos ya se encuentra creada")

# -------------------------------- Funcion principal del programa ----------------------------------------------------------------------
def loop_file():
    #Inicio de loop con cada archivo de nuestro drive
    for file in fileList:
        
        # Fetchear todos los metadatos(caracteristicas) de los archivos para posterior carga
        file.FetchMetadata(fetch_all=True)
        
        # Extraer extension del archivo y categorizarlos si no tienen extension
        auxE = file['mimeType']
        if "/" in auxE:
            fileEx = bool(True)
        else: 
            fileEx = bool(False)
        #Cabe destacar que existe un metadato que contiene la extension, pero en caso de que este vacio, genera errores
            
        # Extraer solamente la fecha de modificacion, ya que tambien trae la hora
        auxT = file['modifiedDate']
        date = auxT.split("T")
        
        # Extraer los permisos del archivo (Publico o privado)
        permisos = file.GetPermissions()
        idPermiso = permisos[0]['id']
        # Categorizacion de archivo en caso de que sea publico o privado
        if idPermiso == 'anyoneWithLink':
            publico = bool(True)
            auxP = 'anyoneWithLink'
            #El ID "anyoneWithLink" refiere a permisos publicos (cualquier persona con el link puede acceder)
        else:
            publico = bool(False)
            auxP = ''
        
        # Convertimos metadata a string, ya que vienen en formato Lista, y SQL no los permite
        titulo = str(file['title'])
        fid = str(file['id'])
        owner = str(file['ownerNames'])
        dat = str(date[0])

        # Insert de los archivos con extension en la database
        if fileEx is True:
            ext = auxE.split("/")
            extension = str(ext[1])
            sql = "INSERT INTO inventario(nombre, id, owner, extension, modificacion, publico) VALUES (%s, %s, %s, %s, %s, %s)"
            val = (titulo, fid, owner, extension, dat, publico)
        # Insert de los archivos sin extension en la database
        elif fileEx is False:
            null = "null"
            sql = "INSERT INTO inventario(nombre, id, owner, extension, modificacion, publico) VALUES (%s, %s, %s, %s, %s, %s)"
            val = (titulo, fid, owner, null, dat, publico)
        # El insert esta dividido segun el tipo de archivo, debido a que genera errores la API de Drive al conseguir la extension como tal

        # Serie de instrucciones en caso de que el archivo sea publico
        if publico is True:
        # Eliminar permisos publicos
            file.DeletePermission(auxP)
            file.Upload()
        # Enviar mail de notificacion al owner
            # Extraer email del owner
            mail = permisos[1]['emailAddress']
            # Avisamos por un print que el archivo estaba publico
            sg.Print("Archivo %s : Visibilidad Publica --> Privada" % titulo)
            # Configuracion del email a enviar
            params = {
                "to": mail,
                "sender": "gmail@gmail.com",
                "subject": "Seguridad de Archivo Modificada",
                "msg_plain": "El archivo %s estaba configurado como Publico, el mismo fue cambiado a Privado" % titulo,
                }
            # Envio de mail
            message = gmail.send_message(**params)
            sg.Print("Email Enviado!")
        # Logueamos cambios en el archivo log.txt que esta en el directorio del archivo
            with open('log.txt', 'a') as f:
                f.write('El archivo "%s" estuvo publico a la fecha %s. Fue cambiado a privado automaticamente \n' % (titulo, dat))
                sg.Print("Datos logueados")
        
    # Commiteamos los cambios en la DB   
        try:
            sqlcursor.execute(sql, val)
            database.commit()
            sg.Print ("Archivo: %s insertado" % titulo)
        # En caso de que el archivo ya exista dentro de la DB, no se hace el commit
        except mysql.connector.errors.IntegrityError:
            sg.Print("El archivo %s ya existe en la database" % titulo)

# Inicio de la interfaz GUI
window = sg.Window("Challenge Drive Docks", layout)

# -------------------------------- Loop del menu ---------------------------------------------------------------------------------------
while True:
    # Leemos input de boton
    event, values = window.read()
    # Configuracion de pantalla inicial
    window['stepone'].Update("Elija una opcion")
    window['checkdb'].Update(visible = True)
    window['createdb'].Update(visible = True)
    window['init'].Update(visible = True)
    window['goback'].Update(visible = False)
    #Pasos al seleccionar chequear DB
    if event == 'checkdb':
        check = checkdb()
        if check is True:
            # Configuracion del menu en caso de base creada
            window['stepone'].Update("La base de datos se encuentra creada")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)
        elif check is False:
            # Configuracion del menu en caso de base no creada
            window['stepone'].Update("La base de datos no esta creada")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)
    #Pasos al seleccionar crear DB
    if event == 'createdb':
        createdb()
        # Configuracion del menu en caso de conseguir crear la base
        window['checkdb'].Update(visible = False)
        window['createdb'].Update(visible = False)
        window['init'].Update(visible = False)
        window['goback'].Update(visible = True)
        window['stepone'].Update("La base de datos se ha creado")
    #Pasos al seleccionar iniciar el programe
    if event == 'init':
        #Si ya chequeamos la DB, podemos iniciar
        if check is True:
            loop_file()
        #Si no se chequeo la DB, se avisa al usuario
        elif check is False:
            window['stepone'].Update("Se debe chequear la base de datos primero")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)
    #Si el usuario cierra la ventana por la X, frenamos el programa
    if event == sg.WIN_CLOSED:
            break
import PySimpleGUI as sg
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import mysql.connector
from simplegmail import Gmail

# definicion de layout GUI
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

# boolean para chequeo de DB
databaseExists = bool(False)
check = bool(False)
    
# conexion con DB
database = mysql.connector.connect(
host = "localhost",
user = "root",
password = "Webapi2022")

# declarar cursor DB (si o si buffered, sino genera problemas con los loops)
sqlcursor = database.cursor(buffered = True)

# autenticar con google
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)
gmail = Gmail()

# obtener lista de archivos de drive
fileList = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()

# funcion para chequeo DB
def checkdb():
    databaseExists = bool(False)
    sqlcursor.execute("SHOW DATABASES")
    for x in sqlcursor:
        if x[0] == "gdrive_database":
            databaseExists = bool(True)
    if databaseExists is True:
        print("La base de datos ya existe")
        sqlcursor.execute("USE gdrive_database")
    else:
        databaseExists = bool(False)
    return(databaseExists)
    
# funcion para crear DB
def createdb():
    try:
        sqlcursor.execute("CREATE DATABASE gdrive_database")
        sqlcursor.execute("USE gdrive_database")
        sqlcursor.execute("CREATE TABLE inventario (id VARCHAR(255) PRIMARY KEY, nombre VARCHAR(255), owner VARCHAR(255), extension VARCHAR(255), modificacion VARCHAR(255), publico VARCHAR(5))")
        print("Base y Tabla Creadas")
    except mysql.connector.errors.DatabaseError:
        sg.Print("La base de datos ya se encuentra creada")

# loop principal para la carga de datos en DB
def loop_file():
    for file in fileList:
        
        # fetchear todos los metadatos para posterior carga
        file.FetchMetadata(fetch_all=True)
        
        # extraer extension del archivo y categorizarlos si no tienen extension
        auxE = file['mimeType']
        if "/" in auxE:
            fileEx = bool(True)
        else: 
            fileEx = bool(False)
            
        # extraer fecha unicamente en dias
        auxT = file['modifiedDate']
        date = auxT.split("T")
        
        # extraer permisos (publico o privado)
        permisos = file.GetPermissions()
        idPermiso = permisos[0]['id']
        # categorizacion de archivo en caso de que sea publico o privado
        if idPermiso == 'anyoneWithLink':
            publico = bool(True)
            auxP = 'anyoneWithLink'
        else:
            publico = bool(False)
            auxP = ''
        
        # conversion a string para posterior carga
        titulo = str(file['title'])
        fid = str(file['id'])
        owner = str(file['ownerNames'])
        dat = str(date[0])

        # insert con extension
        if fileEx is True:
            ext = auxE.split("/")
            extension = str(ext[1])
            sql = "INSERT INTO inventario(nombre, id, owner, extension, modificacion, publico) VALUES (%s, %s, %s, %s, %s, %s)"
            val = (titulo, fid, owner, extension, dat, publico)
        # insert sin extension
        elif fileEx is False:
            null = "null"
            sql = "INSERT INTO inventario(nombre, id, owner, extension, modificacion, publico) VALUES (%s, %s, %s, %s, %s, %s)"
            val = (titulo, fid, owner, null, dat, publico)

# -------------- El insert esta dividido segun el tipo de archivo, debido a que genera errores la API de Drive al conseguir la extension como tal--------------------

        # serie de instrucciones en caso de que el archivo sea publico
        if publico is True:
        # eliminar permisos publicos
            file.DeletePermission(auxP)
            file.Upload()
        # enviar mail de notificacion al owner
            mail = permisos[1]['emailAddress']
            sg.Print("Archivo %s : Visibilidad Publica --> Privada" % titulo)
            params = {
                "to": mail,
                "sender": "gmail@gmail.com",
                "subject": "Seguridad de Archivo Modificada",
                "msg_plain": "El archivo %s estaba configurado como Publico, el mismo fue cambiado a Privado" % titulo,
                }
            message = gmail.send_message(**params)
            sg.Print("Email Enviado!")
        # loguear cambios
            with open('log.txt', 'a') as f:
                f.write('El archivo "%s" estuvo publico a la fecha %s. Fue cambiado a privado automaticamente \n' % (titulo, dat))
                sg.Print("Datos logueados")
        
    # commit en database    
        try:
            sqlcursor.execute(sql, val)
            database.commit()
            sg.Print ("Archivo: %s insertado" % titulo)
        #en caso de que el archivo exista, no se hace el commit
        except mysql.connector.errors.IntegrityError:
            sg.Print("El archivo %s ya existe en la database" % titulo)

# crear ventana GUI
window = sg.Window("Challenge Drive Docks", layout)

# menu en loop
while True:
    # se lee el input del boton
    event, values = window.read()
    # configuracion de pantalla inicial
    window['stepone'].Update("Elija una opcion")
    window['checkdb'].Update(visible = True)
    window['createdb'].Update(visible = True)
    window['init'].Update(visible = True)
    window['goback'].Update(visible = False)
    if event == 'checkdb':
        check = checkdb()
        if check is True:
            # configuracion base creada
            window['stepone'].Update("La base de datos se encuentra creada")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)
        elif check is False:
            # configuracion base no creada
            window['stepone'].Update("La base de datos no esta creada")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)
    if event == 'createdb':
        createdb()
        #configuracion base nueva
        window['checkdb'].Update(visible = False)
        window['createdb'].Update(visible = False)
        window['init'].Update(visible = False)
        window['goback'].Update(visible = True)
        window['stepone'].Update("La base de datos se ha creado")
    if event == 'init':
        if check is True:
            loop_file()
        elif check is False:
            #configuracion inicio sin base creada
            window['stepone'].Update("Se debe chequear la base de datos primero")
            window['checkdb'].Update(visible = False)
            window['createdb'].Update(visible = False)
            window['init'].Update(visible = False)
            window['goback'].Update(visible = True)

    if event == sg.WIN_CLOSED:
            break
# Sharing (Universal Continuity)

Una solución unificada, ligera e independiente para compartir portapapeles (de texto e imágenes) y archivos (estilo AirDrop) entre computadoras con **Ubuntu Linux (Wayland)** y **Windows**.

A diferencia de otros programas, **Sharing** es 100% independiente (no requiere Deskflow ni Mouse Without Borders), funciona de forma peer-to-peer y cuenta con **autodescubrimiento en red local** (cero configuración manual).

---

## Características
* **Autodescubrimiento Automático (mDNS/UDP):** Los equipos se detectan automáticamente en la red local. No es necesario escribir direcciones IP.
* **Portapapeles Bidireccional (Texto e Imágenes):** Sincroniza textos y capturas de pantalla de forma instantánea al copiar.
* **Transferencia de Archivos (AirDrop-like):** Envía archivos con un clic. Se guardan en la carpeta de descargas de Linux o en el Escritorio de Windows, mostrando notificaciones al recibirlos.
* **Compatible con Wayland:** Optimizado para funcionar bajo el servidor gráfico moderno de Ubuntu (GNOME Wayland) de forma 100% silenciosa y sin disparar alertas de seguridad.
* **Portable en Windows:** El lado de Windows funciona desde una terminal de usuario sin requerir instaladores ni permisos de administrador.

---

## Estructura del Proyecto
* **`linux/`**: Contiene la aplicación gráfica y el lanzador de Linux.
* **`win/`**: Contiene el script de PowerShell y el lanzador por lotes (.bat) para Windows.

---

## Configuración y Uso

### En Linux (Servidor)
El instalador creará un acceso directo en tu menú de aplicaciones llamado **"Sharing (Continuity)"**.

1. Abre el menú de aplicaciones de Ubuntu y ejecuta **"Sharing (Continuity)"**.
2. Verás una ventana gráfica que muestra tu nombre de equipo y estado de búsqueda.
3. El programa transmitirá su presencia y esperará conexiones entrantes.

---

### En Windows (Cliente)
1. Copia la carpeta `win` de este proyecto a tu computadora Windows (ej. en tu Escritorio).
2. Haz doble clic sobre **`run_sharing.bat`**.
3. Se abrirá una ventana de comandos que buscará automáticamente a tu equipo Linux en la red local.
4. Una vez detectado, se conectará de inmediato y comenzará a sincronizar el portapapeles y los archivos.

---

## Cómo transferir archivos
* **De Linux a Windows:** En la ventana gráfica de Linux, haz clic en **"Enviar Archivo"**, selecciona el archivo y se guardará automáticamente en el Escritorio del equipo Windows conectado.
* **De Windows a Linux:** (Futura extensión).
* Al recibir cualquier archivo, el sistema te mostrará un aviso en pantalla informándote de la descarga.

---

## Puertos Utilizados
Asegúrate de que tu red local y firewalls permitan la comunicación en los siguientes puertos:
* **Puerto 15200 (TCP):** Para la transferencia del portapapeles y archivos.
* **Puerto 15201 (UDP):** Para el autodescubrimiento de equipos en red local.

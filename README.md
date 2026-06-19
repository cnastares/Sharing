# Sharing (Deskflow + ClipSync)

Una solución unificada y ligera para compartir teclado, ratón y portapapeles (de texto e imágenes) entre computadoras con **Ubuntu Linux (Wayland)** y **Windows**. 

Esta suite combina la potencia de **Deskflow** (para compartir el hardware) con **ClipSync** (un demonio ligero escrito en Python y PowerShell para sincronizar el portapapeles superando las restricciones de seguridad de Wayland en GNOME de forma 100% silenciosa).

---

## Características
* **Compartición de Teclado y Ratón:** Transición fluida a través de los bordes de la pantalla mediante Deskflow.
* **Portapapeles Bidireccional (Texto e Imágenes):** Comparte textos y capturas de pantalla de forma instantánea.
* **Compatible con Wayland:** Diseñado específicamente para funcionar bajo el servidor gráfico moderno de Ubuntu (GNOME Wayland) sin disparar alertas de seguridad del sistema ni popups molestos.
* **Sin requerir privilegios en Windows:** El lado de Windows funciona de forma portable, sin instaladores ni permisos de administrador.

---

## Requisitos Previos

### En Linux (Servidor):
* **Deskflow** instalado en el sistema (disponible en los repositorios de tu distribución).
* Python 3 instalado con soporte para Tkinter (`python3-tk`).
* Utilidades de portapapeles de Wayland (`wl-clipboard` instalado).

### En Windows (Cliente):
* PowerShell 5.1 o superior (instalado por defecto en Windows 10/11).
* La carpeta portable de **Deskflow** descargada.

---

## Configuración e Instalación

### Lado de Linux (Ubuntu)
El instalador creará un acceso directo en tu menú de aplicaciones llamado **"Sharing (Deskflow + ClipSync)"**.

1. Abre el menú de aplicaciones de Ubuntu y ejecuta **"Sharing (Deskflow + ClipSync)"**.
2. En la interfaz de Deskflow, selecciona la opción **"Servidor"** (Server).
3. Haz clic en **Configure Server...** (Configurar Servidor).
4. Arrastra un monitor desde la esquina superior derecha y colócalo a la derecha de tu monitor central (representando la posición física de tu PC Windows).
5. Haz doble clic en el monitor recién colocado y cámbiale el nombre a `LSTKLM290621` (el nombre de tu equipo Windows).
6. Guarda los cambios haciendo clic en **OK** y haz clic en **Start** (Comenzar) en la pantalla principal.

---

### Lado de Windows
Para simplificar la ejecución, combinaremos el cliente de Deskflow y la sincronización de portapapeles en la misma carpeta:

1. Copia la carpeta `win` de este proyecto a tu computadora Windows (puedes ubicarla en tu Escritorio).
2. Descarga la versión **portable** (.zip) de Deskflow para Windows desde su repositorio oficial en GitHub.
3. Descomprime el contenido del zip de Deskflow y copia el archivo `deskflow.exe` **dentro de la carpeta `win`** (donde están `clipsync.ps1` y `run_clipsync.bat`).
4. Haz doble clic sobre **`run_clipsync.bat`**. 
   * Esto abrirá automáticamente el cliente de Deskflow y el sincronizador de portapapeles en segundo plano.
5. En la interfaz de Deskflow en Windows, selecciona la opción **"Cliente"** (Client), ingresa la dirección IP de tu Linux (`192.168.1.36`) en el campo correspondiente y haz clic en **Start** (Comenzar).
6. La primera vez, acepta la huella digital de seguridad (Fingerprint SSL/TLS) de la conexión de Linux haciendo clic en **Yes/Trust**.

---

## Puertos Utilizados
Asegúrate de que tu red local permita la comunicación a través de los siguientes puertos:
* **Puerto 15101 (TCP):** Utilizado por Deskflow para el movimiento del ratón y teclado.
* **Puerto 15200 (TCP):** Utilizado por ClipSync para la transferencia segura del portapapeles de textos e imágenes.

---

## Uso Diario
Una vez configurado por primera vez:
1. Inicia la aplicación en **Linux** usando el atajo de teclado o el menú de aplicaciones.
2. Inicia el archivo **`run_clipsync.bat`** en **Windows**.
3. ¡Desplaza el ratón hacia el borde de la pantalla para empezar a controlar Windows y compartir tu portapapeles!

import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import struct
import queue
import hashlib
import os
import subprocess

PORT = 15200
DISCOVERY_PORT = 15201
MAGIC_PING = b"SHARING_PING:"

# Types: 0 = Text, 1 = Image (PNG), 2 = File

class SharingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sharing (Universal Continuity)")
        self.geometry("450x350")
        self.resizable(False, False)
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Local identity
        self.hostname = socket.gethostname()
        self.local_ip = self.get_local_ip()
        
        # State
        self.peers = {} # ip -> hostname
        self.active_connections = {} # ip -> socket
        self.queue = queue.Queue()
        self.running = True
        self.last_type = -1
        self.last_hash = ""
        
        self.downloads_dir = os.path.expanduser("~/Downloads/Sharing")
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        self.setup_ui()
        
        # Start networking threads
        threading.Thread(target=self.discovery_receiver, daemon=True).start()
        threading.Thread(target=self.discovery_broadcaster, daemon=True).start()
        threading.Thread(target=self.tcp_server, daemon=True).start()
        
        self.poll_queue()
        self.poll_clipboard()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def setup_ui(self):
        # Top panel
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")
        
        ttk.Label(top_frame, text=f"Equipo local: {self.hostname}", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(top_frame, text=f"IP: {self.local_ip} | Puerto: {PORT}", font=("Helvetica", 10)).pack(anchor="w")
        
        # Divider
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)
        
        # Middle panel (Peers list)
        mid_frame = ttk.Frame(self, padding=10)
        mid_frame.pack(fill="both", expand=True)
        
        ttk.Label(mid_frame, text="Equipos conectados en red local:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0,5))
        
        self.peers_listbox = tk.Listbox(mid_frame, height=6, font=("Helvetica", 10))
        self.peers_listbox.pack(fill="both", expand=True)
        
        # Bottom panel (Actions)
        bot_frame = ttk.Frame(self, padding=10)
        bot_frame.pack(fill="x")
        
        self.send_file_btn = ttk.Button(bot_frame, text="Enviar Archivo (AirDrop)", command=self.send_file_action, state="disabled")
        self.send_file_btn.pack(side="right", padx=5)
        
        self.status_label = ttk.Label(bot_frame, text="Buscando equipos...", font=("Helvetica", 9, "italic"))
        self.status_label.pack(side="left")

    # --- peer discovery (UDP) ------------------------------------------------

    def discovery_broadcaster(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = MAGIC_PING + self.hostname.encode('utf-8')
        while self.running:
            try:
                sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(3)

    def discovery_receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('', DISCOVERY_PORT))
        except Exception as e:
            print(f"[UDP] Failed to bind discovery port: {e}")
            return
            
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                ip = addr[0]
                if ip == self.local_ip:
                    continue
                if data.startswith(MAGIC_PING):
                    name = data[len(MAGIC_PING):].decode('utf-8', 'replace')
                    if ip not in self.peers:
                        self.peers[ip] = name
                        self.queue.put(('peer_found', (ip, name)))
            except Exception:
                pass

    # --- TCP connection server -----------------------------------------------

    def tcp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('0.0.0.0', PORT))
            server.listen(5)
        except Exception as e:
            print(f"[TCP] Server error: {e}")
            return
            
        while self.running:
            try:
                conn, addr = server.accept()
                ip = addr[0]
                threading.Thread(target=self.handle_client, args=(conn, ip), daemon=True).start()
            except Exception:
                pass

    def handle_client(self, conn, ip):
        print(f"[TCP] Peer connected: {ip}")
        self.active_connections[ip] = conn
        self.queue.put(('conn_status', (ip, True)))
        
        buffer = b""
        while self.running:
            try:
                if len(buffer) < 5:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data
                if len(buffer) < 5:
                    continue
                    
                p_type = buffer[0]
                length = struct.unpack("!I", buffer[1:5])[0]
                
                while len(buffer) < 5 + length:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data
                    
                if len(buffer) < 5 + length:
                    break
                    
                payload = buffer[5:5+length]
                buffer = buffer[5+length:]
                
                self.queue.put(('data_recv', (p_type, payload)))
            except Exception:
                break
                
        print(f"[TCP] Peer disconnected: {ip}")
        self.active_connections.pop(ip, None)
        self.queue.put(('conn_status', (ip, False)))

    def connect_to_peer(self, ip):
        if ip in self.active_connections:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PORT))
            threading.Thread(target=self.handle_client, args=(sock, ip), daemon=True).start()
        except Exception:
            pass

    # --- data handlers -------------------------------------------------------

    def poll_queue(self):
        while not self.queue.empty():
            q_type, payload = self.queue.get_nowait()
            if q_type == 'peer_found':
                ip, name = payload
                # Automatically attempt active connection to new peer
                threading.Thread(target=self.connect_to_peer, args=(ip,), daemon=True).start()
            elif q_type == 'conn_status':
                ip, status = payload
                name = self.peers.get(ip, ip)
                self.update_peer_list()
                if status:
                    self.status_label.configure(text=f"Conectado a {name}")
                    self.send_file_btn.configure(state="normal")
                else:
                    self.status_label.configure(text="Esperando conexiones...")
                    if not self.active_connections:
                        self.send_file_btn.configure(state="disabled")
            elif q_type == 'data_recv':
                p_type, data = payload
                self.handle_incoming_data(p_type, data)
                
        self.after(100, self.poll_queue)

    def update_peer_list(self):
        self.peers_listbox.delete(0, "end")
        for ip in self.active_connections:
            name = self.peers.get(ip, "Equipo desconocido")
            self.peers_listbox.insert("end", f"• {name} ({ip})")

    def handle_incoming_data(self, p_type, data):
        try:
            h = hashlib.sha256(data).hexdigest()
            self.last_type = p_type
            self.last_hash = h
            
            if p_type == 0: # Text
                text = data.decode('utf-8', 'replace')
                print(f"[Clipboard] Received text: {repr(text)}")
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
            elif p_type == 1: # Image
                print(f"[Clipboard] Received image ({len(data)} bytes)")
                subprocess.run(["wl-copy", "-t", "image/png"], input=data)
            elif p_type == 2: # File
                # Format: [name_len (2 bytes)][name][file_data]
                name_len = struct.unpack("!H", data[:2])[0]
                filename = data[2:2+name_len].decode('utf-8')
                file_bytes = data[2+name_len:]
                filepath = os.path.join(self.downloads_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(file_bytes)
                print(f"[File] Saved incoming file to: {filepath}")
                self.status_label.configure(text=f"Recibido: {filename}")
                messagebox.showinfo("Sharing - Recibido", f"Se ha recibido el archivo:\n{filename}\n\nGuardado en: {self.downloads_dir}")
        except Exception as e:
            print(f"[Error] Failed processing incoming data: {e}")

    # --- clipboard polling ---------------------------------------------------

    def poll_clipboard(self):
        try:
            targets = self.selection_get(selection="CLIPBOARD", type="TARGETS")
        except Exception:
            targets = ""
            
        p_type = -1
        payload = None
        
        if "image/png" in targets:
            try:
                data = self.selection_get(selection="CLIPBOARD", type="image/png")
                if isinstance(data, str):
                    payload = bytes(int(x, 16) for x in data.split() if x)
                else:
                    payload = data
                p_type = 1
            except Exception:
                pass
        elif "UTF8_STRING" in targets or "STRING" in targets:
            try:
                text = self.clipboard_get()
                payload = text.encode('utf-8')
                p_type = 0
            except Exception:
                pass
                
        if p_type != -1 and payload:
            h = hashlib.sha256(payload).hexdigest()
            if p_type != self.last_type or h != self.last_hash:
                self.last_type = p_type
                self.last_hash = h
                self.send_payload_to_all(p_type, payload)
                
        self.after(1000, self.poll_clipboard)

    def send_payload_to_all(self, p_type, payload):
        if not self.active_connections:
            return
        header = struct.pack("!BI", p_type, len(payload))
        packet = header + payload
        for ip, conn in list(self.active_connections.items()):
            try:
                conn.sendall(packet)
            except Exception:
                self.active_connections.pop(ip, None)

    # --- file transfer action ------------------------------------------------

    def send_file_action(self):
        filepath = filedialog.askopenfilename(title="Selecciona un archivo para enviar")
        if not filepath:
            return
        filename = os.path.basename(filepath)
        threading.Thread(target=self.send_file_worker, args=(filepath, filename), daemon=True).start()

    def send_file_worker(self, filepath, filename):
        try:
            self.status_label.configure(text=f"Enviando {filename}...")
            with open(filepath, "rb") as f:
                file_bytes = f.read()
                
            name_bytes = filename.encode('utf-8')
            payload = struct.pack("!H", len(name_bytes)) + name_bytes + file_bytes
            self.send_payload_to_all(2, payload)
            
            self.status_label.configure(text="Archivo enviado con éxito")
            messagebox.showinfo("Sharing - Completado", f"El archivo '{filename}' se envió con éxito.")
        except Exception as e:
            self.status_label.configure(text="Error al enviar archivo")
            messagebox.showerror("Sharing - Error", f"No se pudo enviar el archivo:\n{e}")

if __name__ == "__main__":
    app = SharingApp()
    app.mainloop()

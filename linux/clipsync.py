import socket
import threading
import time
import tkinter as tk
import struct
import queue
import hashlib
import subprocess

PORT = 15200

# Type: 0 = Text, 1 = Image (PNG)

def socket_read_thread(conn, state):
    print("[ClipSync] Windows client connected.")
    state['connected'] = True
    buffer = b""
    while state['running']:
        try:
            # Read type byte and length prefix (1 + 4 = 5 bytes)
            if len(buffer) < 5:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data
            if len(buffer) < 5:
                continue
                
            p_type = buffer[0]
            length = struct.unpack("!I", buffer[1:5])[0]
            # Read full packet
            while len(buffer) < 5 + length:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data
                
            if len(buffer) < 5 + length:
                break
                
            payload = buffer[5:5+length]
            buffer = buffer[5+length:]
            
            # Put in queue for the main thread to write to clipboard
            state['queue'].put((p_type, payload))
        except Exception as e:
            print(f"[ClipSync] Error reading from socket: {e}")
            break
            
    print("[ClipSync] Windows client disconnected.")
    state['connected'] = False

def write_to_local_clipboard(p_type, payload, root, state):
    try:
        h = hashlib.sha256(payload).hexdigest()
        state['last_type'] = p_type
        state['last_hash'] = h
        
        if p_type == 0:
            text = payload.decode('utf-8', 'replace')
            print(f"[ClipSync] Writing text to Linux: {repr(text)}")
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        elif p_type == 1:
            print(f"[ClipSync] Writing image to Linux ({len(payload)} bytes)")
            # Use wl-copy to set image/png
            subprocess.run(["wl-copy", "-t", "image/png"], input=payload)
    except Exception as e:
        print(f"[ClipSync] Error writing to local clipboard: {e}")

def main():
    root = tk.Tk()
    root.withdraw()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', PORT))
        server.listen(1)
        print(f"[ClipSync] Listening on port {PORT}...")
    except Exception as e:
        print(f"[ClipSync] Failed to bind to port {PORT}: {e}")
        return

    state = {
        'running': True,
        'connected': False,
        'last_type': -1,
        'last_hash': "",
        'queue': queue.Queue()
    }

    def accept_thread():
        while state['running']:
            try:
                server.settimeout(1.0)
                conn, addr = server.accept()
                state['conn'] = conn
                t = threading.Thread(target=socket_read_thread, args=(conn, state), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ClipSync] Accept error: {e}")
                break

    t_accept = threading.Thread(target=accept_thread, daemon=True)
    t_accept.start()

    try:
        while True:
            root.update()
            
            # Process incoming updates from Windows
            while not state['queue'].empty():
                p_type, payload = state['queue'].get_nowait()
                write_to_local_clipboard(p_type, payload, root, state)
            
            # Poll local clipboard
            try:
                targets = root.selection_get(selection="CLIPBOARD", type="TARGETS")
            except Exception:
                targets = ""
                
            p_type = -1
            payload = None
            
            if "image/png" in targets:
                try:
                    data = root.selection_get(selection="CLIPBOARD", type="image/png")
                    if isinstance(data, str):
                        payload = bytes(int(x, 16) for x in data.split() if x)
                    else:
                        payload = data
                    p_type = 1
                except Exception:
                    pass
            elif "UTF8_STRING" in targets or "STRING" in targets:
                try:
                    text = root.clipboard_get()
                    payload = text.encode('utf-8')
                    p_type = 0
                except Exception:
                    pass
                    
            if p_type != -1 and payload:
                h = hashlib.sha256(payload).hexdigest()
                if p_type != state['last_type'] or h != state['last_hash']:
                    state['last_type'] = p_type
                    state['last_hash'] = h
                    if state['connected'] and 'conn' in state:
                        label = "image" if p_type == 1 else "text"
                        print(f"[ClipSync] Sending {label} to Windows ({len(payload)} bytes)")
                        try:
                            header = struct.pack("!BI", p_type, len(payload))
                            state['conn'].sendall(header + payload)
                        except Exception as e:
                            print(f"[ClipSync] Error sending: {e}")
            
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("[ClipSync] Stopping...")
    finally:
        state['running'] = False
        if 'conn' in state:
            try:
                state['conn'].close()
            except:
                pass
        server.close()

if __name__ == "__main__":
    main()

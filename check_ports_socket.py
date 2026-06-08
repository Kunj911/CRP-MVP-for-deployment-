import socket

def test_ports():
    ports = [80, 8000, 8001, 3307]
    results = []
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                results.append(f"Port {port}: OPEN")
            else:
                results.append(f"Port {port}: CLOSED (code {result})")
        except Exception as e:
            results.append(f"Port {port}: ERROR ({e})")
        finally:
            s.close()
            
    with open("ports_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results) + "\n")

if __name__ == "__main__":
    test_ports()

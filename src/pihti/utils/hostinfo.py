"""Host info utility for navbar (works on Raspberry Pi and Windows)."""
import socket


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "unknown"
    finally:
        s.close()
    return ip


def get_hostinfo():
    return {
        "hostname": socket.gethostname(),
        "hostname_local": socket.gethostname() + ".local",
        "ip": get_ip(),
    }

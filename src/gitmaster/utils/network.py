import socket

def is_online(host="8.8.8.8", port=53, timeout=3):
    """
    Check if the machine is connected to the internet by attempting to reach a host.
    
    Args:
        host (str): The host to check connectivity against (default: Google's DNS server).
        port (int): The port to try (default: 53 for DNS).
        timeout (float): Time to wait for a response in seconds (default: 3).
    
    Returns:
        bool: True if connected, False otherwise.
    """
    try:
        # Create a socket object and attempt to connect
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False
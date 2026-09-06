import os
import socket
from app import create_app, socketio

app = create_app()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    local_ip = get_local_ip()
    mail_user = app.config.get('MAIL_USERNAME', '')
    is_mail_ready = bool(mail_user and 'your_' not in mail_user)

    print("\n" + "=" * 65)
    print("🚀 TypeSphere Server is Running!")
    print(f"💻 On your PC:          http://127.0.0.1:{port}")
    print(f"📱 On your Phone:       http://{local_ip}:{port}")
    print(f"📧 Mail Sender Active:  {mail_user if is_mail_ready else '⚠️ NOT CONFIGURED (Edit config.py)'}")
    print("=" * 65 + "\n")

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=True,
        allow_unsafe_werkzeug=True
    )
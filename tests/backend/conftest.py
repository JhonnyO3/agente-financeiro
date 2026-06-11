import os

for var, valor in {
    "JWT_SECRET": "test-secret",
    "JWT_ACCESS_EXPIRES_MIN": "30",
    "JWT_REFRESH_EXPIRES_DAYS": "7",
    "ADMIN_EMAILS": "admin@exemplo.com,jhonatas2004@gmail.com",
}.items():
    os.environ.setdefault(var, valor)

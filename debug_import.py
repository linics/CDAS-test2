import sys
import os

print("Python Path:", sys.path)
print("CWD:", os.getcwd())

try:
    import app
    print("Successfully imported app")
    from app.main import app as fastapi_app
    print("Successfully imported fastapi_app")
except ImportError as e:
    print("ImportError:", e)
except Exception as e:
    print("Error:", e)

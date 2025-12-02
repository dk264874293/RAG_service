import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    import langchain_core
    print(f"langchain_core version: {langchain_core.__version__}")
    print(f"langchain_core path: {langchain_core.__file__}")
except ImportError:
    print("langchain_core module not found")

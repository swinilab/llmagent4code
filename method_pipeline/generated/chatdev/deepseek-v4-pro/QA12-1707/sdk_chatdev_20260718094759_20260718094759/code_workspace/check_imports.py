"""Quick import check."""
from src.main import create_app
app = create_app()
print("App created successfully:", app.title)

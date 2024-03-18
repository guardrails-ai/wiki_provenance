import nltk

from .utils.chroma_utils import install_chroma

# Install chromadb
install_chroma()

# Download NLTK data if not already present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
print("NLTK stuff loaded successfully.")

# Local datasets package initialization
# Expose a dummy Dataset class to prevent namespace collisions when Hugging Face transformers imports this local package expecting the global datasets library.
class Dataset:
    pass

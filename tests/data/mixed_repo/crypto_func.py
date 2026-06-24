import hashlib


def hash_file(filepath: str) -> str:
    digest = hashlib.new(name="sha256")
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


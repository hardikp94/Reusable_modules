"""Private local/object storage with bounded upload and explicit content policy."""
import hashlib
from pathlib import Path
import secrets
import time


class LocalBlobs:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        if len(key) != 32 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Invalid blob key")
        path = self.root / key
        if path.is_symlink():
            raise ValueError("Symlinks forbidden")
        return path

    def put(self, key, content):
        with self._path(key).open("xb") as stream:
            stream.write(content)

    def get(self, key):
        return self._path(key).read_bytes()

    def delete(self, key):
        self._path(key).unlink(missing_ok=True)


class S3Blobs:
    def __init__(self, client, bucket, *, prefix="private/"):
        self.client, self.bucket, self.prefix = client, bucket, prefix

    def put(self, key, content):
        self.client.put_object(Bucket=self.bucket, Key=self.prefix + key, Body=content)

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=self.prefix + key)["Body"].read()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=self.prefix + key)


class Files:
    def __init__(self, store, blobs, *, validate, max_bytes=5_000_000, clock=time.time):
        if not callable(validate) or max_bytes < 1:
            raise ValueError("Explicit content validator and positive limit required")
        self.store, self.blobs, self.validate, self.max_bytes, self.clock = store, blobs, validate, max_bytes, clock

    def upload(self, owner, stream, *, filename, content_type):
        data = stream.read(self.max_bytes + 1)
        if not isinstance(data, bytes) or len(data) > self.max_bytes:
            raise ValueError("Upload too large or invalid stream")
        if not self.validate(data, content_type):
            raise ValueError("Content rejected")
        key = secrets.token_hex(16)
        self.blobs.put(key, data)
        row = {"id": key, "owner": owner, "filename": Path(filename.replace("\\", "/")).name, "content_type": content_type, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "created": self.clock()}
        try:
            self.store.put("files", key, row)
        except BaseException:
            self.blobs.delete(key)
            raise
        return row

    def _owned(self, owner, key):
        row = self.store.get("files", key)
        if not row or row["owner"] != owner:
            raise PermissionError("File not found")
        return row

    def download(self, owner, key):
        row = self._owned(owner, key)
        data = self.blobs.get(key)
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("Stored file integrity failure")
        return row, data

    def delete(self, owner, key):
        self._owned(owner, key)
        self.blobs.delete(key)
        self.store.delete("files", key)

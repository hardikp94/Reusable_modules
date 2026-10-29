# Private file storage

```python
from reusable_foundations.storage import Files, LocalBlobs

def validate_text(data, mime):
    if mime != "text/plain": return False
    try: data.decode("utf-8")
    except UnicodeDecodeError: return False
    return b"\x00" not in data

files = Files(store, LocalBlobs("private-files"), validate=validate_text, max_bytes=100_000)
record = files.upload(user_id, stream, filename="notes.txt", content_type="text/plain")
metadata, content = files.download(user_id, record["id"])
files.delete(user_id, record["id"])
```

Uploads read at most max_bytes+1, use random blob keys rather than user filenames, require an explicit content-policy callback, and record owner/size/SHA256. Downloads check ownership and integrity. Filenames are metadata only and reduced to the final basename. LocalBlobs rejects invalid keys and symlink files; its root must be private and not writable by untrusted users. Local-filesystem attacks by privileged actors are outside this boundary.

For object storage use `S3Blobs(explicit_boto3_s3_client, bucket, prefix='private/')`. Grant the service only required private-object permissions, configure encryption and backups, and never make uploaded objects public by default. S3 adapter calls are synchronous and read downloads fully into memory; choose limits accordingly. There is no presigned multipart upload or video-streaming pipeline.

The validator must inspect actual bytes, allowlisted type/format and any required malware scan/quarantine. Declared MIME alone is insufficient. Supply scanning before acceptance; this library does not install a scanner. A scanner failure should reject the upload. The example permits only a narrow text policy and is not a generic safe-document scanner.

If metadata persistence fails, the service attempts blob cleanup. A process crash can still leave an orphan. Delete can remove bytes before metadata cleanup; retries are safe for local/S3 missing objects. Reconcile metadata and object inventories periodically. Blob storage and metadata backups must be restored consistently.

When serving from your web framework, use an authorized download route, attachment Content-Disposition with a framework-sanitized filename and `X-Content-Type-Options: nosniff`. Do not directly concatenate stored MIME/filename into raw headers or render untrusted HTML inline. No HTTP upload/download routes are mounted automatically.

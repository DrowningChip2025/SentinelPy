# python baseline.py
import os, hashlib, json
hashes = {}
for directory in watched_dirs:
    for root, _, files in os.walk(directory):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                with open(filepath, 'rb') as f:
                    hashes[filepath] = hashlib.sha256(f.read()).hexdigest()
            except (IOError, OSError):
                continue
with open('storage/baseline.json', 'w') as f:
    json.dump(hashes, f, indent=2)
print("Baseline de hashes criado com sucesso!")
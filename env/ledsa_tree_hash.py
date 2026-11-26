"""Line-ending independent fingerprint of a LEDSA source tree (env/README.md, "LEDSA version").

For every file below <root> (excluding __pycache__ folders and *.pyc), sorted by the UTF-8 bytes of its relative
POSIX path: line = <relative path> NUL <sha256 hex of the content with CRLF replaced by LF> LF. Output: SHA-256 over
all lines, and the number of files.

Usage:  python env/ledsa_tree_hash.py <root>
        e.g. <root> = a `git archive` export of tag v0.13.0 of FireDynamics/LEDSmokeAnalysis
"""
import hashlib
import sys
from pathlib import Path


def tree_hash(root: Path) -> tuple[str, int]:
    rels = sorted((p.relative_to(root).as_posix() for p in root.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"),
                  key=lambda r: r.encode("utf-8"))
    h = hashlib.sha256()
    for rel in rels:
        data = (root / rel).read_bytes().replace(b"\r\n", b"\n")
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(data).hexdigest().encode("ascii") + b"\n")
    return h.hexdigest(), len(rels)


if __name__ == "__main__":
    digest, n = tree_hash(Path(sys.argv[1]))
    print(f"{n} files; {digest}")

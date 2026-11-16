#!/usr/bin/env python3
"""Build one portable ZIP per skill, suitable for custom-skill upload."""

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from install import skill_sources


def main():
    root = Path(__file__).resolve().parent.parent
    sources = skill_sources(root)
    output = root / "dist"
    output.mkdir(exist_ok=True)
    checksums = []
    for source in sources:
        target = output / f"{source.name}.zip"
        with ZipFile(target, "w") as archive:
            for path in sorted(source.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(source.parent).as_posix()
                info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        checksums.append(f"{checksum}  {target.name}")
        print(target)
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

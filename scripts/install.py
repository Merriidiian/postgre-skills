#!/usr/bin/env python3
"""Copy portable skills to a chosen client; never overwrite an existing skill."""

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
from pathlib import Path


DIRECTORIES = {"codex": ".agents", "claude": ".claude", "cursor": ".cursor"}
CURSOR_COMPATIBILITY = (".agents", ".claude", ".codex")


def skill_sources(root):
    local = root / "skills"
    entries = local.glob("*/SKILL.md") if local.is_dir() else root.glob("*/skills/*/SKILL.md")
    sources = sorted(entry.parent for entry in entries)
    if not sources:
        raise ValueError("Не найдены skills/<name>/SKILL.md рядом с установщиком.")
    names = set()
    for source in sources:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source.name):
            raise ValueError(f"Недопустимое имя навыка: {source.name}")
        if source.name in names:
            raise ValueError(f"Повтор имени навыка: {source.name}")
        names.add(source.name)
        fingerprint(source)
    return sources


def fingerprint(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Ожидается обычный каталог: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Символическая ссылка требует ручной установки: {path}")
        relative = path.relative_to(directory).as_posix()
        if path.is_dir():
            result[relative + "/"] = None
        elif path.is_file():
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            raise ValueError(f"Неподдерживаемый объект: {path}")
    return result


def check_destination(base, destination):
    current = base
    for part in destination.relative_to(base).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Путь назначения содержит символическую ссылку: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"Путь назначения занят файлом: {current}")


def install(root, tool, base, dry_run=False):
    sources = skill_sources(root)
    plan = []
    for source in sources:
        destination = base / DIRECTORIES[tool] / "skills" / source.name
        candidates = [destination]
        if tool == "cursor":
            candidates += [base / folder / "skills" / source.name for folder in CURSOR_COMPATIBILITY]
        existing = []
        for candidate in candidates:
            check_destination(base, candidate)
            if candidate.exists():
                if fingerprint(candidate) != fingerprint(source):
                    raise ValueError(
                        f"Существующий навык отличается: {candidate}. "
                        "Сравните версии и сохраните старую отдельно перед обновлением."
                    )
                existing.append(candidate)
        plan.append((source, destination, existing))

    # Preflight every skill before creating any directories.
    for source, destination, existing in plan:
        if existing:
            print(f"Уже доступен: {existing[0]}")
            continue
        if dry_run:
            print(f"Будет установлен: {source} -> {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{source.name}-", dir=destination.parent) as temp:
            staged = Path(temp) / source.name
            shutil.copytree(source, staged)
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"Каталог появился во время установки: {destination}")
            staged.rename(destination)
        print(f"Установлен: {destination}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=tuple(DIRECTORIES), required=True)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", type=Path, help="Существующий каталог проекта")
    scope.add_argument("--user", action="store_true", help="Установить для текущего пользователя")
    parser.add_argument("--dry-run", action="store_true", help="Показать план без записи файлов")
    args = parser.parse_args(argv)
    base = (Path.home() if args.user else args.project.expanduser()).resolve()
    try:
        if not base.is_dir():
            raise ValueError(f"Каталог проекта/пользователя не существует: {base}")
        install(Path(__file__).resolve().parent.parent, args.tool, base, args.dry_run)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

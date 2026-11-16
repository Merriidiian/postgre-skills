#!/usr/bin/env python3
"""Install skills and project auto-routing without overwriting unrelated instructions."""

import argparse
import hashlib
import re
import shutil
import os
import stat
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


def read_instruction(base, path):
    check_destination(base, path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Ожидается обычный файл инструкций: {path}")
    return path.read_bytes().decode("utf-8") if path.exists() else None


def managed_block(text, name, body):
    start = f"<!-- BEGIN developer-skills:{name} -->"
    end = f"<!-- END developer-skills:{name} -->"
    block = f"{start}\n{body.rstrip()}\n{end}"
    if start not in text and end not in text:
        separator = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
        return text + separator + block + "\n"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ValueError(f"Повреждены маркеры автоматического правила {name}")
    return text[:text.index(start)] + block + text[text.index(end) + len(end):]


def routing_plan(base, tool, plan):
    updates = {}
    for source, destination, existing in plan:
        template = source / "agents" / "auto-apply.md"
        if not template.is_file():
            continue
        installed = existing[0] if existing else destination
        skill_path = (installed / "SKILL.md").relative_to(base).as_posix()
        body = "Путь к навыку ниже указан относительно корня проекта.\n\n" + template.read_text(
            encoding="utf-8"
        ).replace("{skill_path}", skill_path)
        if tool == "codex":
            override = base / "AGENTS.override.md"
            override_text = read_instruction(base, override)
            path = override if override_text else base / "AGENTS.md"
            old = updates[path][0] if path in updates else read_instruction(base, path)
            current = updates[path][1] if path in updates else (old or "")
            updates[path] = (old, managed_block(current, source.name, body))
        else:
            extension = ".mdc" if tool == "cursor" else ".md"
            path = base / DIRECTORIES[tool] / "rules" / f"{source.name}-auto{extension}"
            old = read_instruction(base, path)
            content = managed_block("", source.name, body)
            if tool == "cursor":
                content = "---\nalwaysApply: true\n---\n\n" + content
            if old is not None and old != content:
                raise ValueError(f"Существующее правило отличается и сохранено без изменений: {path}")
            updates[path] = (old, content)
    return updates


def write_instruction(base, path, old, content):
    # Recheck the snapshot before replacing an instruction file atomically.
    if read_instruction(base, path) != old:
        raise ValueError(f"Файл инструкций изменился во время установки: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".skill-routing-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content.encode("utf-8"))
    try:
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(root, tool, base, dry_run=False, project_rules=True):
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

    # Preflight all skills and routing files before creating any directories.
    routes = routing_plan(base, tool, plan) if project_rules else {}
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

    for path, (old, content) in routes.items():
        if old == content:
            continue
        if dry_run:
            print(f"Будет добавлено автоматическое правило: {path}")
        else:
            write_instruction(base, path, old, content)
            print(f"Автоматическое правило: {path}")


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
        install(Path(__file__).resolve().parent.parent, args.tool, base, args.dry_run,
                project_rules=not args.user)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

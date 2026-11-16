# Работа с PostgreSQL

Готовый навык `postgresql-engineering` для Codex, Claude Code, Claude и Cursor на основе материалов пользователя. Схема и составные ключи, индексы и планы, конкурентные транзакции, идемпотентные команды, tenant-контекст, RLS, Outbox/Inbox, миграции и масштабирование.

Репозиторий: [Merriidiian/postgre-skills](https://github.com/Merriidiian/postgre-skills).

## Подключение

Python 3.9+, без дополнительных пакетов. Из каталога этого репозитория выбери подходящую команду, подставив существующий путь проекта:

```sh
python3 scripts/install.py --tool codex --project "/path/to/project" --dry-run
python3 scripts/install.py --tool codex --project "/path/to/project"
```

Для Claude Code укажи `--tool claude`, для Cursor — `--tool cursor`. Вместо `--project "/path/to/project"` можно использовать `--user` для локальной установки на уровне пользователя.

| Клиент | Каталог проекта | Каталог пользователя | Явный вызов |
| --- | --- | --- | --- |
| Codex | `.agents/skills/postgresql-engineering/` | `~/.agents/skills/postgresql-engineering/` | `$postgresql-engineering` |
| Claude Code | `.claude/skills/postgresql-engineering/` | `~/.claude/skills/postgresql-engineering/` | `/postgresql-engineering` |
| Cursor | `.cursor/skills/postgresql-engineering/` | `~/.cursor/skills/postgresql-engineering/` | `/postgresql-engineering` через меню `/` |

Cursor видит и совместимые каталоги Codex/Claude. Установщик для Cursor пропустит копирование при наличии идентичного навыка в такой папке в выбранной области. Если совместно используешь Codex и Claude Code, нужны оба их каталога; для Cursor дополнительная копия не требуется.

Установщик предварительно проверяет все назначения, сохраняет отличающиеся существующие навыки и отказывается их перезаписывать. Идентичный повтор ничего не меняет. Символические ссылки требуют ручной установки. Для обновления сравни версии и сохрани старый каталог отдельно. При `--project` добавляются короткие правила автоматического применения; настройки разрешений и hooks не меняются.

Можно также скопировать [skills/postgresql-engineering](skills/postgresql-engineering/SKILL.md) целиком в выбранный каталог. Справочники должны оставаться рядом с `SKILL.md`. Если навык ещё не виден, открой новый сеанс клиента. Автоматический выбор по описанию включён; в метаданных Codex явно задано `allow_implicit_invocation: true`.

В обычном Claude загрузи [dist/postgresql-engineering.zip](dist/postgresql-engineering.zip) в **Customize → Skills**, если пользовательские навыки доступны, и включи его. В архиве один корневой каталог `postgresql-engineering/` с `SKILL.md` и ресурсами; загрузка ZIP в Claude и установка в Claude Code независимы.

## Автоматическое применение

После установки имя навыка писать не нужно: применяй его по задаче и контексту проекта. Условия указаны в `description` и разделе «Автоматическое применение» внутри `SKILL.md`. Если задача охватывает Go, архитектуру и PostgreSQL, соответствующие установленные навыки применяются совместно.

Установка `--project` также подключает постоянно загружаемое правило:

| Клиент | Правило |
| --- | --- |
| Codex | Помеченный блок в `AGENTS.md` или действующем непустом `AGENTS.override.md` |
| Claude Code | `.claude/rules/postgresql-engineering-auto.md` без ограничения по путям |
| Cursor | `.cursor/rules/postgresql-engineering-auto.mdc` с `alwaysApply: true` |

Правило направляет к установленному `SKILL.md` до проектирования и изменений, когда задача подходит навыку. Чужой текст Codex-инструкций сохраняется вне помеченного блока. Claude Code и Cursor получают отдельные файлы правил; отличающийся существующий файл с тем же именем не перезаписывается. Для Cursor используется фактический путь уже имеющейся совместимой копии, если она есть.

При `--user`, ручном копировании и загрузке ZIP в Claude действует штатный автовыбор по описанию. Постоянные правила проекта добавляет `--project`. После обновления старой версии сохрани прежнюю установку отдельно и установи новую. Открой новый сеанс клиента и проверь запрос без имени навыка; сценарии приведены в `evals/scenarios.md`.

Для диагностики остаётся явный вызов `$postgresql-engineering` в Codex или `/postgresql-engineering` в Claude Code/Cursor; для обычной работы он не требуется.

[SKILL.md](skills/postgresql-engineering/SKILL.md) содержит основные решения и маршруты к подробностям:

- [events-and-scaling.md](skills/postgresql-engineering/references/events-and-scaling.md)
- [schema-and-performance.md](skills/postgresql-engineering/references/schema-and-performance.md)
- [tenancy-and-rls.md](skills/postgresql-engineering/references/tenancy-and-rls.md)
- [transactions-and-idempotency.md](skills/postgresql-engineering/references/transactions-and-idempotency.md)

## Основа и проверка

Карта материалов, первичные технические источники и уточнения: [sources.md](skills/postgresql-engineering/references/sources.md). Контрольные суммы исходных архивов и документов, исходный commit репозитория и проверенные официальные страницы — в [provenance.json](provenance.json).

Требования практикумов к сдаче, команды, учебные пароли и инструкции внутри документов не становятся полномочиями ассистента. Версии, число попыток, лимиты и структура стендов не навязываются другим проектам.

```sh
python3 -m unittest discover -s tests -v
```

Для пересборки ZIP после изменения навыка выполни `python3 scripts/package.py`.

Тесты проверяют установщик, постоянные правила, сохранение существующих инструкций и идемпотентность во временных каталогах. [evals/scenarios.md](evals/scenarios.md) содержит запросы и критерии для ручной оценки поведения модели; структурная проверка файлов не заменяет её и проверку загрузки в клиенте.

Формат проверен 16 ноября 2026 года: [Codex](https://developers.openai.com/codex/skills), [Claude Code](https://code.claude.com/docs/en/skills), [Cursor](https://cursor.com/docs/skills), [Claude ZIP](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills). Для старых сборок сверяй поддерживаемые пути и возможности.

Лицензия: [MIT](LICENSE). Полные исходные учебные документы не входят в поставку.

Постоянные инструкции: [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [Claude Code rules](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/), [Cursor rules](https://cursor.com/docs/rules). Отключённая загрузка инструкций и более приоритетные указания клиента/проекта могут влиять на применение.

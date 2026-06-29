# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin for generating images using Alibaba Cloud Bailian Qwen-Image models (通义千图文生图). Currently in early development — the codebase is scaffolded from the [helloworld template](https://github.com/Soulter/helloworld) and needs to be customized.

- **License:** AGPL v3
- **Repo:** https://github.com/kikikkii/astrbot-qwen-image

## AstrBot Plugin Architecture

AstrBot plugins are single-file Python modules that define a class extending `Star` and registered with the `@register` decorator. The framework loads plugins dynamically based on `metadata.yaml`.

### Key files

- [`metadata.yaml`](metadata.yaml) — Plugin identity manifest. The `name` field must be unique (convention: `astrbot_plugin_<name>`). Update this from the template defaults before publishing.
- [`main.py`](main.py) — The entire plugin implementation. Contains the plugin class and all command handlers.

### Plugin lifecycle

1. `@register(name, author, desc, version)` — top-level decorator that registers the plugin class with AstrBot
2. `__init__(self, context: Context)` — receives a `Context` object with access to the bot's configuration and services
3. `async initialize(self)` — optional, called automatically after instantiation
4. `async terminate(self)` — optional, called when plugin is unloaded/disabled

### Command handlers

Commands are registered via decorators on async generator methods:

```python
@filter.command("command_name")       # matches /command_name
@filter.event_message_type(...)       # filter by message type (e.g. EventMessageType.PRIVATE)
@filter.permission(...)               # restrict by user permissions
```

Handlers receive `event: AstrMessageEvent` and must `yield` results:
- `event.plain_result(text)` — send plain text reply
- `event.image_result(image_path)` — send an image reply (relevant for this image-gen plugin)
- `event.make_result()` — generic result builder

Key `AstrMessageEvent` fields:
- `event.message_str` — the raw text message
- `event.get_messages()` — parsed message chain (list of components)
- `event.get_sender_name()` / `event.get_sender_id()` — sender info
- `event.session` — manages conversation context/session

### Plugin metadata (metadata.yaml)

| Field | Description |
|-------|-------------|
| `name` | Unique plugin ID (prefix with `astrbot_plugin_`) |
| `desc` | Short description shown in plugin marketplace |
| `version` | Semver with `v` prefix, e.g. `v1.0.0` |
| `author` | Author name |
| `repo` | Source repository URL |

## Development

There is no build step, test suite, or dependency manager configured yet. Plugins are deployed by placing the directory into AstrBot's `data/plugins/` folder.

### Reference docs
- [AstrBot Plugin Development Docs (Chinese)](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Development Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)

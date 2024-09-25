# SendDeploy

A CLI tool to manage SSH keys and upload files via SCP

# Usage

```bash
SendDeploy [-h] filename
```

# Development

## Prerequisites

```bash
python3 -m pip install --upgrade build
```

```bash
python3 -m pip install --upgrade twine
```

## Build package

```bash
python3 -m build
```

## Upload package

```bash
python3 -m twine upload dist/*
```

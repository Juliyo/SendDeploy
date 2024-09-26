# SendDeploy

A CLI tool to upload files via SCP from Windows

# Usage

```bash
SendDeploy [-h] filename
```

# Development

## Prerequisites

```bash
python -m pip install --upgrade build
```

```bash
python -m pip install --upgrade twine
```

## Build package

```bash
python -m build
```

## Upload package

```bash
python -m twine upload dist/*
```

# SendDeploy

A CLI tool to upload a file via SCP

# Prerequisites

```bash
python3 -m pip install --upgrade build
```

```bash
python3 -m pip install --upgrade twine
```

# Build package

```bash
python3 -m build
```

# Upload package

```bash
python3 -m twine upload dist/*
```

# Installation

## Create environment

```bash
conda create -n hydro_fetch python=3.11
conda activate hydro_fetch
```

## Install

```bash
pip install -e ".[docs]"
```

!!! note
    The `[docs]` extra installs MkDocs and mkdocstrings for building documentation locally.
    Omit it for a minimal install: `pip install -e .`

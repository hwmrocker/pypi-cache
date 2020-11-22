# PyPI cache

## install dependencies

```bash
poetry install
```

## run server

```bash
poetry shell
PYTHONTRACEMALLOC=1 PYTHONASYNCIODEBUG=1 python app.py
```

## use cache

```bash
pip install -i http://localhost:8000/simple flask
```

## what is this already doing

[x] transparent proxy to public pypi
[x] caching result in memory

## TODO:

* cache files locally on disk
* expire cache
* log stats
* compile wheels automatically

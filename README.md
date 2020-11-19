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

## TODO:

* cache files locally
* log stats
* compile wheels automatically

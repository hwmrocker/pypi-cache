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

- [x] transparent proxy to public pypi
- [x] caching package files in memory
- [x] dumping packages on disk, 
- [x] loading files from disk, when they are not in memory

## TODO:

- [ ] expire cache
- [ ] use cache when package is requested in parallel
    We should not download / request it twice, and the second one should return the whole package.
- [ ] make the io calls to the file system also async (maybe with curio?)
- [ ] log stats
- [ ] compile wheels automatically
- [ ] add local wheels to the list in /simple/<package>

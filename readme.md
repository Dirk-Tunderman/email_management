for starting the project install the virtual enviroment

```bash
python3 -m venv venv
```

activate the virtual enviroment

```bash
source venv/bin/activate
```


install the required packages if you have poetry, if not install it from here https://python-poetry.org/docs

```bash
poetry install
```

run the server on the default port

```bash
gunicorn main:app --reload
```

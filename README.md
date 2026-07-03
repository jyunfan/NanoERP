# NanoERP
A simple ERP system built with Python and Textual.

Let users manage their business operations efficiently through a terminal or web interface. Use keyboard shortcuts to navigate and perform actions quickly.

# Execution
``` $ uv run main.py ```

# Browser TUI for remote testing
Run NanoERP through `ttyd`:

```sh
./scripts/run_ttyd.sh
```

Then open `http://127.0.0.1:7681`.

Defaults:

- username/password: `nanoerp` / `nanoerp`
- bind address: `127.0.0.1`
- port: `7681`

These can be overridden:

```sh
TTYD_CREDENTIAL='user:password' TTYD_PORT=7682 ./scripts/run_ttyd.sh
```

The script removes `NO_COLOR` for the child process because Textual/Rich
honor `NO_COLOR=1` and will render the TUI in grayscale.

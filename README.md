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
- port: `7681`, or the next available port if `7681` is already in use

These can be overridden:

```sh
TTYD_CREDENTIAL='user:password' TTYD_PORT=7682 ./scripts/run_ttyd.sh
```

The script removes `NO_COLOR` for the child process because Textual/Rich
honor `NO_COLOR=1` and will render the TUI in grayscale.

It also detects whether the installed `ttyd` supports `--writable`. Older
`ttyd` versions are writable by default and do not accept `-W`.

# Test case data
Rebuild a reproducible test database with the current 10 customers, 12 products,
2 suppliers, 3 posted customer-order days, and 1 draft customer-order day:

```sh
python3 scripts/test_cases.py run
```

By default this writes `/tmp/nanoerp_test_cases.db` and prints `PASS` when all
checks succeed. To seed the application database instead:

```sh
python3 scripts/test_cases.py run --db db.sql
```

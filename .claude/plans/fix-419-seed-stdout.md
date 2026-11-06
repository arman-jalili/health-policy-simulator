# Implementation plan — #419

1. Let `create_app` accept an explicit log stream; the seed CLI passes `sys.stderr`.
2. Suppress the Makefile recipe echo with `@`, so `make demo-seed` has no command line on stdout.
3. Keep the API/worker logging default on stdout; only the seed's CLI redirects logs.
4. Prove with a subprocess test that default `LOG_LEVEL=INFO` stdout parses as JSON and stderr carries logs.
5. Remove the `LOG_LEVEL=ERROR`/`make -s` stop-gap from the walkthrough documentation.

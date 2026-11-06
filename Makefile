# Convenience entrypoints for the backend service.
.PHONY: demo-seed demo-reset demo-walkthrough

demo-seed:
	$(MAKE) -C backend demo-seed

demo-reset:
	$(MAKE) -C backend demo-reset

demo-walkthrough:
	$(MAKE) -C backend demo-walkthrough

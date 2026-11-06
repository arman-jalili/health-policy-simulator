# Convenience entrypoints for the backend service.
.PHONY: demo-seed demo-walkthrough

demo-seed:
	$(MAKE) -C backend demo-seed

demo-walkthrough:
	$(MAKE) -C backend demo-walkthrough

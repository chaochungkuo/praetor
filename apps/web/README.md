# Praetor Web

This service is the browser-facing entrypoint for the multi-service stack.

Current role:

- health endpoint
- reverse proxy to the Praetor API app
- stable place to evolve into a dedicated web shell later

It does not run mission logic itself.

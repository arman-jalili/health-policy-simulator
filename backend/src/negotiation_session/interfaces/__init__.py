"""Interfaces layer: HTTP router and published views of NegotiationSession.

The router is concrete by design (ADR-004): there is no separate HTTP interface file. Views in
``published.py`` are the only shapes other contexts may consume.
"""

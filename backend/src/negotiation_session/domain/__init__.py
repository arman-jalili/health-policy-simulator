"""Domain layer: the negotiation aggregate and its owned vocabulary.

Nothing in this package imports an outer layer of the module or an upstream context's adapters,
retrieval hits or vector types (AC 12). Upstream data crosses the ACL as framework-free domain
values, mapped by the adapter package before the aggregate sees it.
"""

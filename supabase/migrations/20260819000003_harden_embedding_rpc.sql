-- F0.4.6 hardening: make RPC name resolution deterministic.
alter function public.match_canonical_embeddings(
    extensions.vector,
    text,
    float,
    int
) set search_path = pg_catalog, public, extensions;

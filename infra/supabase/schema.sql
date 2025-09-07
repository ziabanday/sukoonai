-- Core RAG schema for docs/chunks (Supabase Postgres)
-- Ensure pgvector extension is enabled in your project: Database → Extensions → vector

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "vector";

-- Adjust dimension to your embedding model (e.g., text-embedding-3-small = 1536)
do $$ begin
  if not exists (select 1 from pg_type where typname = 'vector') then
    raise notice 'pgvector extension missing';
  end if;
end $$;

create table if not exists public.docs (
  id uuid primary key default gen_random_uuid(),
  org_id text null,
  source_system text null,     -- 'MedlinePlus' | 'WHO' | 'Web'
  source_url text null,
  title text,
  checksum text unique,        -- md5 to avoid duplicates
  created_at timestamptz not null default now()
);

create table if not exists public.chunks (
  id uuid primary key default gen_random_uuid(),
  doc_id uuid not null references public.docs(id) on delete cascade,
  ord int not null default 0,
  content text not null,
  embedding vector(1536) null,
  checksum text unique,
  created_at timestamptz not null default now()
);
create index if not exists idx_chunks_doc_id on public.chunks (doc_id);
create index if not exists idx_chunks_embedding on public.chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Optional: views for convenient retrieval
create or replace view public.v_doc_chunk as
select c.id as chunk_id, d.id as doc_id, d.title, d.source_system, d.source_url, c.ord, c.content
from public.chunks c
join public.docs d on d.id = c.doc_id;
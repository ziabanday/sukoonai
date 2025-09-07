-- Corrected CKG-lite schema for Supabase Postgres
-- Uses UNIQUE INDEX for case-insensitive names (no expressions in table-level UNIQUE).

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- --- Sources registry
create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  system text not null,
  name text not null,
  base_url text,
  license text,
  unique (system, name)
);

-- --- Conditions
create table if not exists public.conditions (
  id uuid primary key default gen_random_uuid(),
  org_id text null,
  code_system text null,
  code text null,
  name text not null,
  description text null,
  icd11_uri text null,
  mesh_id text null,
  created_at timestamptz not null default now()
);
create index if not exists idx_conditions_name on public.conditions (lower(name));
create unique index if not exists uniq_conditions_org_lower_name on public.conditions (org_id, lower(name));
do $$ begin
  perform 1 from pg_indexes where schemaname='public' and indexname='uniq_conditions_codes';
  if not found then
    execute 'create unique index uniq_conditions_codes on public.conditions (org_id, code_system, code) nulls not distinct';
  end if;
end $$;

-- --- Symptoms
create table if not exists public.symptoms (
  id uuid primary key default gen_random_uuid(),
  org_id text null,
  name text not null,
  mesh_id text null,
  description text null,
  created_at timestamptz not null default now()
);
create index if not exists idx_symptoms_name on public.symptoms (lower(name));
create unique index if not exists uniq_symptoms_org_lower_name on public.symptoms (org_id, lower(name));

-- --- Condition ↔ Symptom
create table if not exists public.condition_symptom (
  condition_id uuid not null references public.conditions(id) on delete cascade,
  symptom_id uuid not null references public.symptoms(id) on delete cascade,
  relation text default 'associated_with',
  primary key (condition_id, symptom_id)
);

-- --- Interventions
create table if not exists public.interventions (
  id uuid primary key default gen_random_uuid(),
  org_id text null,
  name text not null,
  type text null,
  description text null,
  source_url text null,
  created_at timestamptz not null default now()
);
create index if not exists idx_interventions_name on public.interventions (lower(name));
create unique index if not exists uniq_interventions_org_lower_name on public.interventions (org_id, lower(name));

-- --- Condition ↔ Intervention
create table if not exists public.condition_intervention (
  condition_id uuid not null references public.conditions(id) on delete cascade,
  intervention_id uuid not null references public.interventions(id) on delete cascade,
  relation text default 'recommended',
  primary key (condition_id, intervention_id)
);

-- --- Assessments
create table if not exists public.assessments (
  id uuid primary key default gen_random_uuid(),
  org_id text null,
  name text not null,
  instrument text not null,
  min_score int null,
  max_score int null,
  severity_bands jsonb null,
  source_url text null,
  created_at timestamptz not null default now(),
  unique (org_id, instrument)
);

-- --- Topic links
create table if not exists public.topic_links (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('condition','symptom','intervention','assessment')),
  entity_id uuid not null,
  system text not null,
  url text not null,
  created_at timestamptz not null default now(),
  unique (entity_type, entity_id, system)
);
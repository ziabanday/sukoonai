-- Seed CKG-lite demo data (idempotent)
-- Fix: use ON CONFLICT (org_id, lower(name)) where we created unique indexes on expressions.

-- 1) Sources
insert into public.sources (system, name, base_url, license)
values 
  ('MedlinePlus','MedlinePlus','https://medlineplus.gov','U.S. NLM terms'),
  ('WHO','World Health Organization','https://www.who.int','WHO terms')
on conflict (system, name) do update set base_url = excluded.base_url;

-- 2) Condition: Depression (upsert by org_id + lower(name))
with ins as (
  insert into public.conditions (org_id, code_system, code, name, description, icd11_uri, mesh_id)
  values (null, 'ICD-11', '6A70', 'Depression', 'A mood disorder with persistent sadness and loss of interest.', 'https://icd.who.int/browse11/l-m/en#/http://id.who.int/icd/entity/1183832314', null)
  on conflict (org_id, lower(name)) do nothing
  returning id
),
selected as (
  select id from ins
  union all
  select id from public.conditions where org_id is null and lower(name)='depression' limit 1
)
select * from selected;

-- 3) Symptoms (upsert by org_id + lower(name))
insert into public.symptoms (org_id, name, description)
values (null, 'Low mood', 'Feeling down most of the day'), 
       (null, 'Anhedonia', 'Loss of interest or pleasure'),
       (null, 'Sleep disturbance', 'Trouble sleeping or sleeping too much')
on conflict (org_id, lower(name)) do nothing;

-- 4) Interventions (upsert by org_id + lower(name))
insert into public.interventions (org_id, name, type, description, source_url)
values (null, 'Diaphragmatic breathing', 'exercise', 'Slow breathing technique that triggers relaxation response', 'https://medlineplus.gov/ency/patientinstructions/000803.htm'),
       (null, 'Sleep hygiene', 'psychoeducation', 'Habits that improve sleep quality', 'https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response')
on conflict (org_id, lower(name)) do nothing;

-- 5) Assessments (has table-level unique (org_id, instrument))
insert into public.assessments (org_id, name, instrument, min_score, max_score, severity_bands, source_url)
values 
  (null, 'PHQ-9 scoring', 'PHQ-9', 0, 27, '{"0-4":"none","5-9":"mild","10-14":"moderate","15-19":"moderately severe","20-27":"severe"}', 'https://www.phqscreeners.com/select-screener/36'),
  (null, 'GAD-7 scoring', 'GAD-7', 0, 21, '{"0-4":"none","5-9":"mild","10-14":"moderate","15-21":"severe"}', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1526959/')
on conflict (org_id, instrument) do nothing;

-- 6) Wire mappings (Depression ↔ symptoms/interventions)
do $$
declare
  cond uuid;
begin
  select id into cond from public.conditions where org_id is null and lower(name)='depression' limit 1;

  insert into public.condition_symptom (condition_id, symptom_id)
  select cond, s.id from public.symptoms s where lower(s.name) in ('low mood','anhedonia','sleep disturbance')
  on conflict do nothing;

  insert into public.condition_intervention (condition_id, intervention_id)
  select cond, i.id from public.interventions i where lower(i.name) in ('diaphragmatic breathing','sleep hygiene')
  on conflict do nothing;
end $$;

-- 7) Topic links (table-level unique (entity_type, entity_id, system))
do $$
declare
  cond uuid;
begin
  select id into cond from public.conditions where org_id is null and lower(name)='depression' limit 1;

  insert into public.topic_links (entity_type, entity_id, system, url)
  values 
    ('condition', cond, 'MedlinePlus', 'https://medlineplus.gov/depression.html'),
    ('condition', cond, 'WHO', 'https://www.who.int/news-room/fact-sheets/detail/depression')
  on conflict (entity_type, entity_id, system) do nothing;
end $$;
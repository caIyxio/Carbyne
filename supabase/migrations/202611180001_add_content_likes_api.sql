create table public.content_items (
  id uuid primary key,
  creator_id uuid not null references public.profiles(id) on delete cascade,
  content_type text not null check (content_type in ('video', 'spotlight')),
  created_at timestamptz not null default now(),
  unique (id, content_type)
);

alter table public.content_items enable row level security;

create policy "Content items are publicly readable"
  on public.content_items for select
  to anon, authenticated
  using (true);

create policy "Creators can register their own content"
  on public.content_items for insert
  to authenticated
  with check ((select auth.uid()) = creator_id);

create policy "Creators can remove their own content"
  on public.content_items for delete
  to authenticated
  using ((select auth.uid()) = creator_id);

create table public.content_likes (
  content_id uuid not null references public.content_items(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (content_id, user_id)
);

create index content_likes_user_id_idx on public.content_likes(user_id);

alter table public.content_likes enable row level security;

create policy "Content likes are publicly readable"
  on public.content_likes for select
  to anon, authenticated
  using (true);

create policy "Users can like content as themselves"
  on public.content_likes for insert
  to authenticated
  with check (
    (select auth.uid()) = user_id
    and not exists (
      select 1
      from public.content_items
      where content_items.id = content_likes.content_id
        and content_items.creator_id = (select auth.uid())
    )
  );

create policy "Users can remove their own likes"
  on public.content_likes for delete
  to authenticated
  using ((select auth.uid()) = user_id);

create view public.profile_like_counts
with (security_invoker = true)
as
select
  content_items.creator_id,
  count(content_likes.user_id)::bigint as likes_count
from public.content_items
left join public.content_likes on content_likes.content_id = content_items.id
group by content_items.creator_id;

grant select on public.content_items to anon, authenticated;
grant insert, delete on public.content_items to authenticated;
grant select on public.content_likes to anon, authenticated;
grant insert, delete on public.content_likes to authenticated;
grant select on public.profile_like_counts to anon, authenticated;

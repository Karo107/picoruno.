-- 遊んだ回数を1増やす関数（Supabase の SQL Editor に貼って実行）
-- まだ行がないゲーム（あとから追加したゲーム）も、初回で行を作って数え始めます。
create or replace function public.add_play(g text)
returns integer
language sql
security definer
set search_path = public
as $$
  insert into game_stats (game, plays, likes)
  select g, 1, 0
  where length(g) between 1 and 40
  on conflict (game) do update set plays = game_stats.plays + 1
  returning plays;
$$;

grant execute on function public.add_play(text) to anon;

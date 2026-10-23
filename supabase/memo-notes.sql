-- 誰かのメモ帳（memo.html）用のテーブルと関数
-- Supabase の SQL Editor にこのファイルをまるごと貼りつけて Run すれば準備完了です。
-- 何度実行しても壊れないように書いてあります（テーブルと元のメモは残り、関数は上書き）。
--
-- しくみ：
--   ・ブラウザからはテーブルを直接読めない／書けない（RLSを有効にしてポリシーなし）。
--   ・下の5つの関数（rpc）だけを anon に公開し、文字数・NGワード・連投・通報の制限はすべてサーバー側でも確認する。
--   ・IPアドレスはそのまま保存せず、日付つきでハッシュにしたもの（日ごとに変わる）だけを連投・通報の判定に使う。

create table if not exists public.memo_notes (
  id           bigint generated always as identity primary key,
  body         text        not null check (char_length(body) between 1 and 40),
  parent_id    bigint      references public.memo_notes(id) on delete set null,
  depth        int         not null default 1,
  ink          smallint    not null default 0 check (ink between 0 and 3),
  reply_count  int         not null default 0,
  served_count int         not null default 0,
  report_count int         not null default 0,
  hidden       boolean     not null default false,
  author_hash  text,
  created_at   timestamptz not null default now()
);
create index if not exists memo_notes_parent_idx on public.memo_notes(parent_id);
create index if not exists memo_notes_author_idx on public.memo_notes(author_hash, created_at);

create table if not exists public.memo_reports (
  note_id     bigint references public.memo_notes(id) on delete cascade,
  author_hash text   not null,
  created_at  timestamptz not null default now(),
  primary key (note_id, author_hash)
);

alter table public.memo_notes   enable row level security;
alter table public.memo_reports enable row level security;
revoke all on public.memo_notes, public.memo_reports from anon, authenticated;

-- ===== 内部用：送り主のハッシュ（IPそのものは残さない） =====
create or replace function public.memo_client_hash() returns text
language sql stable set search_path = public as $$
  select md5(
    coalesce(split_part(
      coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json->>'x-forwarded-for', ',', 1), 'local')
    || ':' || current_date::text || ':picoruno-memo')
$$;

-- ===== 内部用：書いてはいけない内容か =====
-- 返り値 null ならOK、それ以外は理由（クライアント側にも同じ判定があるので、ふつうはここまで来ない）
create or replace function public.memo_ng_reason(p text) returns text
language plpgsql immutable set search_path = public as $$
declare
  s text := lower(normalize(coalesce(p, ''), NFKC));
  flat text;
begin
  -- カタカナ→ひらがな、空白・記号を取りのぞいて伏せ字をすり抜けにくくする
  flat := translate(s,
    'ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴ',
    'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔ');
  flat := regexp_replace(flat, '[\s　・.,、。!！?？_\-~〜ー*＊/／|｜"''`]+', '', 'g');
  if s ~ '(https?:|www\.|[a-z0-9-]+\.(com|net|org|jp|io|me|ly|gl|co|xyz|info|tv)(?![a-z0-9]))' then return 'link'; end if;
  if s ~ '@[a-z0-9_]{2,}' then return 'handle'; end if;
  if regexp_replace(s, '[\s()‐ー－-]+', '', 'g') ~ '[0-9]{9,}' then return 'number'; end if;
  if flat ~ '(line|らいん|insta|いんすた|discord|でぃすこ|kakao|かかお)(id|あいでぃ|交換|こうかん)' then return 'contact'; end if;
  if flat ~ '(死ね|氏ね|殺す|殺せ|前しね|まえしね|めえしね)' or flat ~ '(^|[^ぁ-ゖ一-龥])しね' then return 'word'; end if;
  if flat ~ '(ころす|ころせ|きえろ|じさつしろ|がいじ|きちがい|きもいんだよ|ちんこ|ちんぽ|まんこ|せっくす|れいぷ|sex|fuck|shit|nigg)' then return 'word'; end if;
  return null;
end $$;

-- ===== 1枚引く =====
-- p_exclude：もう見たメモや自分のメモのid（クライアントが最大200件まで送る）
-- あまり読まれていない新しめのメモが優先して届くように、配った回数＋ゆらぎで並べる
create or replace function public.memo_draw(p_exclude bigint[] default '{}')
returns table(id bigint, body text, depth int, ink smallint, reply_count int, created_at timestamptz)
language plpgsql security definer set search_path = public as $$
declare picked bigint;
begin
  select s.id into picked
    from (select n.id, n.served_count from public.memo_notes n
           where not n.hidden and not (n.id = any(coalesce(p_exclude[1:200], '{}')))
           order by n.id desc limit 3000) s
   order by least(s.served_count, 30) + random() * 4
   limit 1;
  if picked is null then return; end if;
  update public.memo_notes set served_count = served_count + 1 where memo_notes.id = picked;
  return query select n.id, n.body, n.depth, n.ink, n.reply_count, n.created_at
                 from public.memo_notes n where n.id = picked;
end $$;

-- ===== 共有リンクから特定の1枚をひらく =====
create or replace function public.memo_get(p_id bigint)
returns table(id bigint, body text, depth int, ink smallint, reply_count int, created_at timestamptz)
language sql security definer stable set search_path = public as $$
  select n.id, n.body, n.depth, n.ink, n.reply_count, n.created_at
    from public.memo_notes n where n.id = p_id and not n.hidden
$$;

-- ===== 返事を書く（その返事が次の誰かに届く） =====
create or replace function public.memo_post(p_body text, p_parent bigint default null, p_ink int default 0)
returns table(id bigint, depth int)
language plpgsql security definer set search_path = public as $$
declare
  b text;
  h text := public.memo_client_hash();
  d int := 1;
  new_id bigint;
begin
  -- 改行・制御文字を消して、連続する空白を1つに
  b := btrim(regexp_replace(regexp_replace(coalesce(p_body, ''), '[[:cntrl:]]', ' ', 'g'), '\s+', ' ', 'g'));
  if char_length(b) < 1 or char_length(b) > 40 then raise exception 'memo_length' using errcode = '22023'; end if;
  if public.memo_ng_reason(b) is not null then raise exception 'memo_ng' using errcode = '22023'; end if;
  if p_ink is null or p_ink < 0 or p_ink > 3 then p_ink := 0; end if;
  -- 連投よけ：同じ送り主は10分に8枚、1日に40枚まで
  if (select count(*) from public.memo_notes n where n.author_hash = h and n.created_at > now() - interval '10 minutes') >= 8
     or (select count(*) from public.memo_notes n where n.author_hash = h and n.created_at > now() - interval '1 day') >= 40 then
    raise exception 'memo_rate' using errcode = '22023';
  end if;
  -- 同じ人が同じ文を続けて送るのを止める
  if exists (select 1 from public.memo_notes n where n.author_hash = h and n.body = b and n.created_at > now() - interval '1 day') then
    raise exception 'memo_dup' using errcode = '22023';
  end if;
  if p_parent is not null then
    update public.memo_notes n set reply_count = n.reply_count + 1
     where n.id = p_parent and not n.hidden
     returning n.depth + 1 into d;
    if d is null then d := 1; p_parent := null; end if;
  end if;
  insert into public.memo_notes(body, parent_id, depth, ink, author_hash)
  values (b, p_parent, d, p_ink, h) returning memo_notes.id into new_id;
  return query select new_id, d;
end $$;

-- ===== 自分のメモについた返事 =====
-- p_ids：自分が書いたメモのid（最大50件）。各メモにつき新しい返事を3件まで返す
create or replace function public.memo_replies(p_ids bigint[])
returns table(parent_id bigint, id bigint, body text, ink smallint, created_at timestamptz)
language sql security definer stable set search_path = public as $$
  select r.parent_id, r.id, r.body, r.ink, r.created_at from (
    select n.*, row_number() over (partition by n.parent_id order by n.id desc) as rn
      from public.memo_notes n
     where n.parent_id = any(coalesce(p_ids[1:50], '{}')) and not n.hidden
  ) r where r.rn <= 3
  order by r.parent_id, r.id
$$;

-- ===== 通報（ちがう3人から通報されたら見えなくなる） =====
create or replace function public.memo_report(p_id bigint)
returns void
language plpgsql security definer set search_path = public as $$
declare h text := public.memo_client_hash();
begin
  if (select count(*) from public.memo_reports r where r.author_hash = h and r.created_at > now() - interval '1 day') >= 30 then
    return;
  end if;
  insert into public.memo_reports(note_id, author_hash) values (p_id, h) on conflict do nothing;
  if found then
    update public.memo_notes n set report_count = n.report_count + 1,
                                   hidden = n.hidden or n.report_count + 1 >= 3
     where n.id = p_id;
  end if;
exception when foreign_key_violation then
  return;
end $$;

revoke all on function public.memo_client_hash(), public.memo_ng_reason(text) from public, anon, authenticated;
revoke all on function public.memo_draw(bigint[]), public.memo_get(bigint), public.memo_post(text, bigint, int),
                       public.memo_replies(bigint[]), public.memo_report(bigint) from public;
grant execute on function public.memo_draw(bigint[]), public.memo_get(bigint), public.memo_post(text, bigint, int),
                          public.memo_replies(bigint[]), public.memo_report(bigint) to anon, authenticated;

-- ===== はじまりのメモ（空っぽだと誰にも届かないので、最初の数十枚だけ用意） =====
insert into public.memo_notes(body, author_hash)
select v, 'seed' from unnest(array[
  'きょうの晩ごはん、なにがいいと思う？',
  '雨の音を聞きながらこれを書いています',
  'さっき空を見たら、雲がくじらの形だった',
  'ちいさい頃の夢、まだ覚えてる？',
  '最近ちょっとだけがんばってる',
  'あしたは早起きするぞ（たぶん無理）',
  '好きなおにぎりの具を教えてください',
  'コンビニの新作アイス、当たりだった',
  '眠れない夜はなにしてる？',
  '今年いちばんうれしかったことを書いて',
  'このメモ、どこまで旅するんだろう',
  'いま聴いてる曲が最高すぎる',
  '猫派？犬派？それとも…',
  'がんばってる人、えらい',
  '冷蔵庫にプリンがあるのを思い出した',
  '靴ひもがほどけたまま一日すごした',
  'どこか遠くに行きたい気分',
  'しりとりしよう。りんご',
  '知らない誰かさん、こんにちは',
  'ねむい。とにかくねむい',
  '最近笑ったことある？',
  'きょうはいい日だった。あなたは？',
  '夏と冬ならどっちが好き？',
  'いまから自分にごほうびを買いに行く',
  '宇宙人って本当にいると思う',
  'おすすめの本があったら教えて',
  '朝ごはんはパン派です',
  '子どもの頃の秘密基地、どこにあった？',
  'これを読んだ人に、いいことがありますように',
  'お風呂で考えごとをすると長くなる'
]) as v
where not exists (select 1 from public.memo_notes);

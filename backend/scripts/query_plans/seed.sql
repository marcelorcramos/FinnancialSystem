-- 1000 users x 15 labels x 60 months (2021-11..2026-10): one allocation per label/month,
-- two transfers and one addition per month. About 1.1M entries.
SET synchronous_commit = off;
INSERT INTO users (id, email, name) SELECT gen_random_uuid(), 'u' || g || '@lab.test', 'User ' || g FROM generate_series(1, 1000) g;
INSERT INTO labels (id, user_id, name, kind, color, icon)
SELECT gen_random_uuid(), u.id, 'Label ' || l, (ARRAY['expense','saving','investment'])[1 + l % 3], '#FFB74D', 'restaurant'
FROM users u, generate_series(1, 15) l;
INSERT INTO months (id, user_id, year, month)
SELECT gen_random_uuid(), u.id, 2021 + (10 + m) / 12, 1 + (10 + m) % 12 FROM users u, generate_series(0, 59) m;
INSERT INTO entries (id, user_id, month_id, label_id, amount, movement_type, occurred_on)
SELECT gen_random_uuid(), m.user_id, m.id, l.id, (10 + random() * 300)::numeric(14,2), 'allocation', make_date(m.year, m.month, 1)
FROM months m JOIN labels l ON l.user_id = m.user_id;
-- transfers: pairs sharing transfer_id
WITH t AS (
  SELECT gen_random_uuid() AS tid, m.user_id, m.id AS month_id, make_date(m.year, m.month, 10 + k) AS d,
         (SELECT id FROM labels WHERE user_id = m.user_id ORDER BY name OFFSET k LIMIT 1) AS a,
         (SELECT id FROM labels WHERE user_id = m.user_id ORDER BY name OFFSET k + 5 LIMIT 1) AS b
  FROM months m, generate_series(0, 1) k
)
INSERT INTO entries (id, user_id, month_id, label_id, amount, movement_type, transfer_id, occurred_on)
SELECT gen_random_uuid(), user_id, month_id, a, 15, 'transfer_out', tid, d FROM t
UNION ALL SELECT gen_random_uuid(), user_id, month_id, b, 15, 'transfer_in', tid, d FROM t;
WITH i AS (
  INSERT INTO incomes (id, user_id, month_id, source, amount, received_on)
  SELECT gen_random_uuid(), m.user_id, m.id, 'Extra income', 40, make_date(m.year, m.month, 15) FROM months m
  RETURNING id, user_id, month_id, received_on
)
INSERT INTO entries (id, user_id, month_id, label_id, amount, movement_type, income_id, occurred_on)
SELECT gen_random_uuid(), i.user_id, i.month_id,
       (SELECT id FROM labels WHERE user_id = i.user_id ORDER BY name LIMIT 1), 40, 'addition', i.id, i.received_on
FROM i;
ANALYZE;
SELECT count(*) AS entries FROM entries;

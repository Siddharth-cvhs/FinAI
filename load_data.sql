\set ON_ERROR_STOP on

DROP TABLE IF EXISTS live_transcation;
CREATE TABLE live_transcation (
    transaction_id text,
    timestamp timestamp,
    user_id text,
    sender_account text,
    amount text,
    origin_ip text,
    device_id text,
    destination_account text,
    location text
);

DROP TABLE IF EXISTS transaction_history;
CREATE TABLE transaction_history (
    transaction_id text,
    timestamp timestamp,
    user_id text,
    sender_account text,
    amount text,
    origin_ip text,
    device_id text,
    destination_account text,
    location text
);

DROP TABLE IF EXISTS watchlist;
CREATE TABLE watchlist (
    entity_type text,
    entity_value text,
    risk_level text,
    reason text
);

\copy live_transcation FROM 'C:/VH811/Hackathon/db1_live_transactions_clean.csv' WITH (FORMAT csv, HEADER);
\copy transaction_history FROM 'C:/VH811/Hackathon/db2_transaction_history_clean.csv' WITH (FORMAT csv, HEADER);
\copy watchlist FROM 'C:/VH811/Hackathon/db3_watchlist.csv' WITH (FORMAT csv, HEADER);

SELECT 'live_transcation' AS table, COUNT(*) AS rows FROM live_transcation
UNION ALL
SELECT 'transaction_history', COUNT(*) FROM transaction_history
UNION ALL
SELECT 'watchlist', COUNT(*) FROM watchlist;

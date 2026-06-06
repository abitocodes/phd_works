-- Monthly ERC-20 token transfers filtered to wallet set (AWP baseline subset)
-- Parameters: @start_ts, @end_ts, @start_block, @end_block, @wallet_addresses (ARRAY<STRING>)

SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  token_address,
  from_address,
  to_address,
  value
FROM
  `bigquery-public-data.crypto_ethereum.token_transfers`
WHERE
  block_timestamp >= TIMESTAMP(@start_ts)
  AND block_timestamp < TIMESTAMP(@end_ts)
  AND block_number >= @start_block
  AND block_number <= @end_block
  AND (
    from_address IN UNNEST(@wallet_addresses)
    OR to_address IN UNNEST(@wallet_addresses)
  )

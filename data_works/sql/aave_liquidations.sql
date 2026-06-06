-- Aave V3 LiquidationCall events
-- Parameters: @start_ts, @end_ts, @liquidation_topic0, @pool_addresses (ARRAY<STRING>)

SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  address AS pool_address,
  topics[SAFE_OFFSET(1)] AS collateral_asset,
  topics[SAFE_OFFSET(2)] AS debt_asset,
  topics[SAFE_OFFSET(3)] AS user_address,
  data
FROM
  `bigquery-public-data.crypto_ethereum.logs`
WHERE
  block_timestamp >= TIMESTAMP(@start_ts)
  AND block_timestamp < TIMESTAMP(@end_ts)
  AND topics[SAFE_OFFSET(0)] = @liquidation_topic0
  AND LOWER(address) IN (
    SELECT LOWER(addr) FROM UNNEST(@pool_addresses) AS addr
  )

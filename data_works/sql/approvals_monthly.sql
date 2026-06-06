-- Monthly ERC-20 Approval events from crypto_ethereum.logs
-- Parameters: @start_ts, @end_ts, @start_block, @end_block, @approval_topic0

SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  address AS token_address,
  topics[SAFE_OFFSET(1)] AS owner,
  topics[SAFE_OFFSET(2)] AS spender,
  SAFE_CAST(data AS NUMERIC) AS value
FROM
  `bigquery-public-data.crypto_ethereum.logs`
WHERE
  block_timestamp >= TIMESTAMP(@start_ts)
  AND block_timestamp < TIMESTAMP(@end_ts)
  AND block_number >= @start_block
  AND block_number <= @end_block
  AND topics[SAFE_OFFSET(0)] = @approval_topic0

-- reconcile.lua: Atomic multi-worker budget reconciliation for INFUSE Governor
-- KEYS[1] = res_record_key
-- KEYS[2] = active_day_key
-- KEYS[3] = active_month_key
-- KEYS[4] = daily_spend_key
-- KEYS[5] = monthly_spend_key

-- ARGV[1] = reservation_id
-- ARGV[2] = actual_cost (string/number)

local res_record_key = KEYS[1]
local active_day_key = KEYS[2]
local active_month_key = KEYS[3]
local daily_spend_key = KEYS[4]
local monthly_spend_key = KEYS[5]

local res_id = ARGV[1]
local actual_cost = tonumber(ARGV[2]) or 0.0
if actual_cost < 0.0 then
    actual_cost = 0.0
end

local current_status = redis.call('HGET', res_record_key, 'status')
if not current_status then
    return cjson.encode({ status = "NOT_FOUND" })
end

-- Idempotency: If already RECONCILED or RELEASED, do not increment spend again
if current_status == "RECONCILED" or current_status == "RELEASED" then
    local res_id_val = redis.call('HGET', res_record_key, 'reservation_id')
    local exec_id_val = redis.call('HGET', res_record_key, 'execution_id')
    local est_val = redis.call('HGET', res_record_key, 'estimated_cost')
    local act_val = redis.call('HGET', res_record_key, 'actual_cost')
    local res_at_val = redis.call('HGET', res_record_key, 'reserved_at')
    local d_b_val = redis.call('HGET', res_record_key, 'daily_bucket')
    local m_b_val = redis.call('HGET', res_record_key, 'monthly_bucket')
    return cjson.encode({
        status = "NOOP",
        current_status = current_status,
        reservation_id = res_id_val,
        execution_id = exec_id_val,
        estimated_cost = tonumber(est_val) or 0.0,
        actual_cost = tonumber(act_val) or 0.0,
        reserved_at = res_at_val,
        daily_bucket = d_b_val,
        monthly_bucket = m_b_val
    })
end

-- Transition ACTIVE or UNCERTAIN to RECONCILED
redis.call('HSET', res_record_key, 'status', 'RECONCILED', 'actual_cost', tostring(actual_cost))
redis.call('HDEL', active_day_key, res_id)
redis.call('HDEL', active_month_key, res_id)

if actual_cost > 0.0 then
    redis.call('INCRBYFLOAT', daily_spend_key, tostring(actual_cost))
    redis.call('INCRBYFLOAT', monthly_spend_key, tostring(actual_cost))
end

local res_id_val = redis.call('HGET', res_record_key, 'reservation_id')
local exec_id_val = redis.call('HGET', res_record_key, 'execution_id')
local est_val = redis.call('HGET', res_record_key, 'estimated_cost')
local res_at_val = redis.call('HGET', res_record_key, 'reserved_at')
local d_b_val = redis.call('HGET', res_record_key, 'daily_bucket')
local m_b_val = redis.call('HGET', res_record_key, 'monthly_bucket')

return cjson.encode({
    status = "OK",
    reservation_id = res_id_val,
    execution_id = exec_id_val,
    estimated_cost = tonumber(est_val) or 0.0,
    actual_cost = actual_cost,
    reserved_at = res_at_val,
    daily_bucket = d_b_val,
    monthly_bucket = m_b_val,
    current_status = "RECONCILED"
})

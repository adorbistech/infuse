-- reserve.lua: Atomic multi-worker budget reservation for INFUSE Governor
-- KEYS[1] = daily_spend_key
-- KEYS[2] = monthly_spend_key
-- KEYS[3] = active_day_key (Hash: res_id -> estimated_cost)
-- KEYS[4] = active_month_key (Hash: res_id -> estimated_cost)
-- KEYS[5] = res_record_key (Hash: reservation details)

-- ARGV[1] = estimated_cost (string/number)
-- ARGV[2] = task_limit (string or ""/nil)
-- ARGV[3] = daily_limit (string or ""/nil)
-- ARGV[4] = monthly_limit (string or ""/nil)
-- ARGV[5] = reservation_id
-- ARGV[6] = execution_id
-- ARGV[7] = reserved_at (ISO timestamp string)
-- ARGV[8] = daily_bucket
-- ARGV[9] = monthly_bucket
-- ARGV[10] = ttl_seconds

local daily_spend_key = KEYS[1]
local monthly_spend_key = KEYS[2]
local active_day_key = KEYS[3]
local active_month_key = KEYS[4]
local res_record_key = KEYS[5]

local est_cost = tonumber(ARGV[1]) or 0.0
local task_limit_str = ARGV[2]
local daily_limit_str = ARGV[3]
local monthly_limit_str = ARGV[4]
local res_id = ARGV[5]
local exec_id = ARGV[6]
local reserved_at = ARGV[7]
local daily_bucket = ARGV[8]
local monthly_bucket = ARGV[9]
local ttl_seconds = tonumber(ARGV[10]) or 120

-- 1. Check Task Limit
if task_limit_str and task_limit_str ~= "" and task_limit_str ~= "nil" then
    local task_limit = tonumber(task_limit_str)
    if task_limit and est_cost > task_limit then
        return cjson.encode({
            status = "DENIED",
            reason = "max_cost_per_task",
            estimated_cost = est_cost,
            limit = task_limit
        })
    end
end

-- 2. Check Daily Limit
local active_day_vals = redis.call('HVALS', active_day_key)
local active_day_sum = 0.0
for _, v in ipairs(active_day_vals) do
    active_day_sum = active_day_sum + (tonumber(v) or 0.0)
end
local committed_daily = tonumber(redis.call('GET', daily_spend_key) or "0") or 0.0
local total_daily_exposure = committed_daily + active_day_sum

if daily_limit_str and daily_limit_str ~= "" and daily_limit_str ~= "nil" then
    local daily_limit = tonumber(daily_limit_str)
    if daily_limit and (total_daily_exposure + est_cost) > daily_limit then
        return cjson.encode({
            status = "DENIED",
            reason = "max_cost_per_day",
            projected_spend = total_daily_exposure + est_cost,
            current_spent = committed_daily,
            active_reserved = active_day_sum,
            estimated_cost = est_cost,
            limit = daily_limit
        })
    end
end

-- 3. Check Monthly Limit
local active_month_vals = redis.call('HVALS', active_month_key)
local active_month_sum = 0.0
for _, v in ipairs(active_month_vals) do
    active_month_sum = active_month_sum + (tonumber(v) or 0.0)
end
local committed_monthly = tonumber(redis.call('GET', monthly_spend_key) or "0") or 0.0
local total_monthly_exposure = committed_monthly + active_month_sum

if monthly_limit_str and monthly_limit_str ~= "" and monthly_limit_str ~= "nil" then
    local monthly_limit = tonumber(monthly_limit_str)
    if monthly_limit and (total_monthly_exposure + est_cost) > monthly_limit then
        return cjson.encode({
            status = "DENIED",
            reason = "max_cost_per_month",
            projected_spend = total_monthly_exposure + est_cost,
            current_spent = committed_monthly,
            active_reserved = active_month_sum,
            estimated_cost = est_cost,
            limit = monthly_limit
        })
    end
end

-- 4. Record Active Reservation
redis.call('HSET', active_day_key, res_id, tostring(est_cost))
redis.call('HSET', active_month_key, res_id, tostring(est_cost))

redis.call('HSET', res_record_key,
    'reservation_id', res_id,
    'execution_id', exec_id,
    'estimated_cost', tostring(est_cost),
    'actual_cost', '0.00',
    'reserved_at', reserved_at,
    'daily_bucket', daily_bucket,
    'monthly_bucket', monthly_bucket,
    'status', 'ACTIVE'
)
redis.call('EXPIRE', res_record_key, ttl_seconds)

return cjson.encode({
    status = "OK",
    reservation_id = res_id,
    execution_id = exec_id,
    estimated_cost = est_cost,
    reserved_at = reserved_at,
    daily_bucket = daily_bucket,
    monthly_bucket = monthly_bucket
})

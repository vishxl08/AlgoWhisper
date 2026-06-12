# Two Sum - My Strategy

## Approach
Use a hash map to store `{value: index}` as we scan the array once.

## Why it works
For each `nums[i]`, we need `target - nums[i]`. If that complement was seen
earlier, we return both indices immediately.

## Pitfalls
- Don't use the same element twice (check index, not just value)
- Handle negative numbers and zeros correctly

## Complexity
- Time: O(n)
- Space: O(n)

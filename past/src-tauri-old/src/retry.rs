// retry.rs
// Exponential backoff retry logic for connection handling

use std::time::Duration;
use tokio::time::sleep;

/// Retry configuration
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_attempts: u32,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 4,
            initial_delay_ms: 1000,  // 1s
            max_delay_ms: 8000,      // 8s cap
            multiplier: 2.0,         // exponential
        }
    }
}

impl RetryConfig {
    /// Calculate delay for attempt n (0-indexed)
    /// Attempt 0: 0ms (immediate)
    /// Attempt 1: 1000ms
    /// Attempt 2: 2000ms
    /// Attempt 3: 4000ms
    pub fn delay_for_attempt(&self, attempt: u32) -> Duration {
        if attempt == 0 {
            return Duration::ZERO;
        }

        let delay = self.initial_delay_ms as f64
            * self.multiplier.powi(attempt as i32 - 1);
        let capped = delay.min(self.max_delay_ms as f64) as u64;

        Duration::from_millis(capped)
    }
}

/// Result of a retry operation
#[derive(Debug)]
pub enum RetryResult<T, E> {
    Success(T),
    Failed { attempts: u32, last_error: E },
}

/// Execute an async operation with retries
pub async fn with_retry<T, E, F, Fut>(
    config: &RetryConfig,
    mut operation: F,
) -> RetryResult<T, E>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
{
    let mut last_error: Option<E> = None;

    for attempt in 0..config.max_attempts {
        // Wait before retry (no wait on first attempt)
        let delay = config.delay_for_attempt(attempt);
        if !delay.is_zero() {
            sleep(delay).await;
        }

        match operation().await {
            Ok(result) => return RetryResult::Success(result),
            Err(e) => {
                last_error = Some(e);
                // Continue to next attempt
            }
        }
    }

    RetryResult::Failed {
        attempts: config.max_attempts,
        last_error: last_error.unwrap(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_delay_calculation() {
        let config = RetryConfig::default();

        assert_eq!(config.delay_for_attempt(0), Duration::ZERO);
        assert_eq!(config.delay_for_attempt(1), Duration::from_millis(1000));
        assert_eq!(config.delay_for_attempt(2), Duration::from_millis(2000));
        assert_eq!(config.delay_for_attempt(3), Duration::from_millis(4000));
        // Capped at max
        assert_eq!(config.delay_for_attempt(4), Duration::from_millis(8000));
        assert_eq!(config.delay_for_attempt(5), Duration::from_millis(8000));
    }

    #[tokio::test]
    async fn test_retry_succeeds_first_attempt() {
        let config = RetryConfig::default();
        let mut call_count = 0;

        let result: RetryResult<i32, &str> = with_retry(&config, || {
            call_count += 1;
            async { Ok(42) }
        }).await;

        assert!(matches!(result, RetryResult::Success(42)));
        assert_eq!(call_count, 1);
    }

    #[tokio::test]
    async fn test_retry_succeeds_third_attempt() {
        let config = RetryConfig {
            max_attempts: 4,
            initial_delay_ms: 10, // Short for test
            max_delay_ms: 100,
            multiplier: 2.0,
        };
        let mut call_count = 0;

        let result: RetryResult<i32, &str> = with_retry(&config, || {
            call_count += 1;
            async move {
                if call_count < 3 {
                    Err("not yet")
                } else {
                    Ok(42)
                }
            }
        }).await;

        assert!(matches!(result, RetryResult::Success(42)));
        assert_eq!(call_count, 3);
    }

    #[tokio::test]
    async fn test_retry_exhausted() {
        let config = RetryConfig {
            max_attempts: 3,
            initial_delay_ms: 10,
            max_delay_ms: 100,
            multiplier: 2.0,
        };
        let mut call_count = 0;

        let result: RetryResult<i32, &str> = with_retry(&config, || {
            call_count += 1;
            async { Err("always fails") }
        }).await;

        assert!(matches!(result, RetryResult::Failed { attempts: 3, .. }));
        assert_eq!(call_count, 3);
    }
}
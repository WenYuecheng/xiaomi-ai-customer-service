"""
文件职责：
该文件负责实现基于内存的访问频率限制功能，主要用于防止恶意注册和接口滥用。

所属功能：
安全防护与速率限制。

主要流程：
使用滑动窗口算法，在指定的时间窗口内记录并限制同一来源的请求次数。超过限制则抛出异常。
"""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from app.core.errors import AppError


class RegistrationRateLimiter:
    """
    类职责：
    注册接口的频率限制器。用于防止同一 IP 或来源在短时间内大量请求注册接口。

    生命周期：
    通常作为应用级单例存在（例如绑定在 FastAPI 的 app.state 上），
    随应用启动创建，随应用关闭销毁。

    重要属性：
    - limit: 时间窗口内允许的最大请求次数。
    - window_seconds: 滑动窗口的时间跨度（秒）。
    - _attempts: 用于记录每个来源（如 IP）最近请求时间戳的哈希表，值是双端队列。
    - _lock: 线程锁，确保在多线程环境下更新记录的并发安全。
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        """
        初始化频率限制器。

        Args:
            limit (int): 窗口期内最大允许的请求次数。
            window_seconds (int): 时间窗口的长度（以秒为单位）。
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, source: str) -> None:
        """
        检查指定来源的请求是否超出频率限制。

        Args:
            source (str): 请求的唯一标识符（例如客户端的 IP 地址）。

        Returns:
            None: 如果未触发限制，则直接返回。

        Raises:
            AppError: 如果请求频率过高，抛出 HTTP 429 错误。
        """
        # 获取当前的单调时间，不受系统时钟修改的影响
        now = monotonic()

        # 加锁以保证并发场景下的原子操作
        with self._lock:
            attempts = self._attempts[source]

            # 清理过期的记录：如果队列中最老的时间戳早于当前时间减去窗口长度，则移除
            while attempts and attempts[0] <= now - self.window_seconds:
                attempts.popleft()

            # 检查当前窗口内的请求次数是否已经达到上限
            if len(attempts) >= self.limit:
                # 计算需要等待多长时间才能重试
                retry_after = max(1, int(self.window_seconds - (now - attempts[0])))
                raise AppError(
                    429,
                    "registration_rate_limited",
                    "注册尝试过于频繁，请稍后再试",
                    headers={"Retry-After": str(retry_after)},
                )

            # 如果未达上限，则将当前请求的时间戳追加到队列中
            attempts.append(now)

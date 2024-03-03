from __future__ import annotations

import collections
import contextlib
import logging
import sys
import time
from types import TracebackType
from typing import Any

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    from typing import Self
else:  # pragma: <3.11 cover
    from typing_extensions import Self

from proxystore.proxy import Proxy
from proxystore.store.base import Store
from proxystore.store.future import Future
from proxystore.stream.interface import StreamConsumer

from psbench.benchmarks.stream_scaling.config import RunConfig
from psbench.benchmarks.stream_scaling.config import RunResult
from psbench.benchmarks.stream_scaling.generator import generator_task
from psbench.config import StreamConfig
from psbench.executor.protocol import Executor
from psbench.logging import TESTING_LOG_LEVEL

logger = logging.getLogger('stream-scaling')


def compute_task(data: bytes, sleep: float) -> None:
    # Resolve data if necessary
    assert isinstance(data, bytes)

    time.sleep(sleep)


def pregenerate(
    size: int,
    interval: float,
    example_size: int = 100_000_000,
    example_time: float = 0.250,
) -> bool:
    # Determine if the data size is too large to generate within a given
    # time interval.
    #
    # Benchmark with QueuePublisher and Store[FileConnector]:
    #   - 1000 x 1MB: 1.8s (556 items/s) (1MB in 1.8 ms)
    #   - 25 x 100MB: 5.7s (4.4 items/s) (100MB in 228 ms)
    # To err on the safe side, I've chose 100 MB in 0.25 s as the
    # example interval. Note that this was on a pretty fast workstation.
    example_rate = example_size / example_time
    expected_time = size / example_rate
    return expected_time > interval


class Benchmark:
    name = 'Stream Scaling'
    config_type = RunConfig
    result_type = RunResult

    def __init__(
        self,
        consumer: StreamConsumer[bytes],
        executor: Executor,
        store: Store[Any],
        stream_config: StreamConfig,
    ) -> None:
        self.consumer = consumer
        self.executor = executor
        self.store = store
        self.stream_config = stream_config

        if self.executor.max_workers is None:  # pragma: no cover
            raise ValueError(
                'Executor max_workers is None but this benchmark requires '
                'the executor to define the maximum number of workers.',
            )
        self.max_workers = self.executor.max_workers

    def __enter__(self) -> Self:
        # https://stackoverflow.com/a/39172487
        with contextlib.ExitStack() as stack:
            stack.enter_context(self.consumer)
            stack.enter_context(self.executor)
            # The consumer will also call close on the store, but close should
            # be idempotent so it is okay.
            stack.enter_context(self.store)
            self._stack = stack.pop_all()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self._stack.__exit__(exc_type, exc_value, exc_traceback)

    def config(self) -> dict[str, Any]:
        return {
            'executor': self.executor.__class__.__name__,
            'connector': self.store.connector.__class__.__name__,
            'subscriber': self.consumer._subscriber.__class__.__name__,
            'stream-config': self.stream_config,
        }

    def run(self, config: RunConfig) -> RunResult:
        compute_workers = self.max_workers - 1
        producer_interval = config.task_sleep / compute_workers
        pregen_data = pregenerate(config.data_size_bytes, producer_interval)
        logger.log(TESTING_LOG_LEVEL, f'Compute workers: {compute_workers}')
        logger.log(TESTING_LOG_LEVEL, 'Generator workers: 1')
        logger.log(
            TESTING_LOG_LEVEL,
            f'Generator item interval: {producer_interval}',
        )

        stop_generator: Future[bool] = self.store.future()
        generator_task_future = self.executor.submit(
            generator_task,
            store_config=self.store.config(),
            stream_config=self.stream_config,
            stop_generator=stop_generator,
            item_size_bytes=config.data_size_bytes,
            max_items=config.task_count,
            pregenerate=pregen_data,
            interval=producer_interval,
            topic=self.stream_config.topic,
        )
        logger.log(
            TESTING_LOG_LEVEL,
            'Submitted generator task: '
            f'item_size_bytes={config.data_size_bytes}, '
            f'max_items={config.task_count}, '
            f'interval_seconds={producer_interval}, '
            f'pregenerate={pregen_data}',
        )
        completed_tasks = 0
        running_tasks: collections.deque[Future[bytes]] = collections.deque()

        start = time.time()

        try:
            for i, item in enumerate(self.consumer):
                if isinstance(item, Proxy):
                    # Quick hack because Parsl will accidentally resolve
                    # proxy when it scans tasks inputs for any special
                    # files.
                    item.__wrapped__ = None
                task_future = self.executor.submit(
                    compute_task,
                    item,
                    sleep=config.task_sleep,
                )
                logger.log(
                    TESTING_LOG_LEVEL,
                    f'Submitted compute task {i+1}/{config.task_count}',
                )
                running_tasks.append(task_future)

                # Only start waiting on old tasks once we've filled the
                # available compute workers.
                if len(running_tasks) >= compute_workers:
                    oldest_task_future = running_tasks.popleft()
                    oldest_task_future.result()
                    completed_tasks += 1
        except KeyboardInterrupt:  # pragma: no cover
            logger.warning(
                'Caught KeyboardInterrupt... sending stop signal to generator',
            )
            stop_generator.set_result(True)
        finally:
            logger.log(TESTING_LOG_LEVEL, 'Waiting on generator task')
            generator_task_future.result()

        logger.log(
            TESTING_LOG_LEVEL,
            'Finished submitting new compute tasks',
        )

        logger.log(TESTING_LOG_LEVEL, 'Waiting on generator task')
        generator_task_future.result()

        # Wait on remaining tasks. There should be compute_workers number
        # of tasks remaining unless a KeyboardInterrupt occurred.
        logger.log(TESTING_LOG_LEVEL, 'Waiting on outstanding compute tasks')
        while len(running_tasks) > 0:
            task = running_tasks.popleft()
            task.result()
            completed_tasks += 1

        logger.log(TESTING_LOG_LEVEL, 'All compute tasks finished')

        end = time.time()

        assert self.stream_config.kind is not None
        return RunResult(
            executor=self.executor.__class__.__name__,
            connector=self.store.connector.__class__.__name__,
            stream=self.stream_config.kind,
            data_size_bytes=config.data_size_bytes,
            task_count=config.task_count,
            task_sleep=config.task_sleep,
            workers=self.max_workers,
            completed_tasks=completed_tasks,
            start_submit_tasks_timestamp=start,
            end_tasks_done_timestamp=end,
        )

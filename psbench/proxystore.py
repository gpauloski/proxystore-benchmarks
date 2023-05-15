from __future__ import annotations

import argparse
from typing import Any

from proxystore.connectors.connector import Connector
from proxystore.connectors.dim.margo import MargoConnector
from proxystore.connectors.dim.ucx import UCXConnector
from proxystore.connectors.dim.zmq import ZeroMQConnector
from proxystore.connectors.endpoint import EndpointConnector
from proxystore.connectors.file import FileConnector
from proxystore.connectors.globus import GlobusConnector
from proxystore.connectors.globus import GlobusEndpoints
from proxystore.connectors.redis import RedisConnector
from proxystore.store import register_store
from proxystore.store import Store


def init_store_from_args(
    args: argparse.Namespace,
    **kwargs: Any,
) -> Store[Any] | None:
    """Initialize a ProxyStore Store from CLI arguments.

    Usage:
        >>> parser = argparse.ArgumentParser(...)
        >>> add_proxystore_options(parser, required=...)
        >>> args = parser.parse_args()
        >>> store= init_store_from_args(args)

    Args:
        args (Namespace): namespace returned by argument parser.
        kwargs: additional keyword arguments to pass to the Store.

    Returns:
        Store or None if no store was specified.
    """
    if not args.ps_backend:
        return None

    connector: Connector

    if args.ps_backend == 'ENDPOINT':
        connector = EndpointConnector(args.ps_endpoints)
    elif args.ps_backend == 'FILE':
        connector = FileConnector(args.ps_file_dir)
    elif args.ps_backend == 'GLOBUS':
        endpoints = GlobusEndpoints.from_json(args.ps_globus_config)
        connector = GlobusConnector(endpoints)
    elif args.ps_backend == 'REDIS':
        connector = RedisConnector(args.ps_host, args.ps_port)
    elif args.ps_backend == 'MARGO':
        connector = MargoConnector(
            port=args.ps_port,
            protocol=args.ps_margo_protocol,
            address=args.ps_address,
            interface=args.ps_interface,
        )
    elif args.ps_backend == 'UCX':
        connector = UCXConnector(
            port=args.ps_port,
            interface=args.ps_interface,
            address=args.ps_address,
        )
    elif args.ps_backend == 'ZMQ':
        connector = ZeroMQConnector(
            port=args.ps_port,
            interface=args.ps_interface,
            address=args.ps_address,
        )
    else:
        raise ValueError(f'Invalid backend: {args.ps_backend}')

    store = Store(f'{args.ps_backend}-STORE', connector, **kwargs)
    register_store(store)

    return store

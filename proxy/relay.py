from __future__ import annotations

import asyncio


async def relay_streams(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_reader: asyncio.StreamReader,
    upstream_writer: asyncio.StreamWriter,
) -> tuple[int, int]:
    async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> int:
        total = 0
        try:
            while chunk := await reader.read(65536):
                total += len(chunk)
                writer.write(chunk)
                await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        return total

    client_to_upstream, upstream_to_client = await asyncio.gather(
        pipe(client_reader, upstream_writer),
        pipe(upstream_reader, client_writer),
    )
    return client_to_upstream, upstream_to_client

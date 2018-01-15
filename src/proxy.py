import sys
from utils import hexdump
import asyncio
from contextlib import suppress

local_host = None
remote_host = None
local_port = 0
remote_port = 0

def main():
    global local_host
    global local_port
    global remote_host
    global remote_port

    # no fancy command-line parsing here
    if len(sys.argv[1:]) != 4:
        print(f"Usage: {sys.argv[0]} <localhost> <localport>"
                " <remotehost> <remoteport>")
        print(f"Example: {sys.argv[0]} 127.0.0.1 8000 "
                "10.12.132.1 8000")
        return 1

    # setup local listening parameters
    local_host = sys.argv[1]
    local_port = int(sys.argv[2])

    # setup remote target
    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    server = loop.run_until_complete(
            asyncio.start_server(proxy_start, local_host, local_port))

    with suppress(KeyboardInterrupt):
        loop.run_forever()
    server.close()
    loop.close()
 
    return 0

async def proxy(reader, writer, index, init_close):
    l_arrow, l_name, r_arrow, r_name = '[<==]', 'local', '[==>]', 'remote'
    peer = writer.get_extra_info('peername')
    if index == 1:
        l_arrow, l_name, r_arrow, r_name = r_arrow, r_name, l_arrow, l_name
    while True:
        try:
            data = await reader.read(4096)
            len_buf = len(data)
            if len_buf == 0: # FYN received
                print(f"{r_arrow} Connection Closed by {l_name} host.")
                init_close[(index+1)%2] = 1
                if init_close[index] == 1:
                    writer.close()
                elif init_close[index] == 0:
                    writer.write_eof()
                return

            print(f"{r_arrow} Received {len_buf} bytes from {l_name} host")
            hexdump(data)
            # check if FYN
            # hexdump it
            print(f"{r_arrow} sent to {r_name} host {peer}")
            writer.write(data)
            await writer.drain()
        except ConnectionResetError as e:
            init_close[(index+1)%2] = -1
            if reader.exception():
                writer.close()
            return

async def proxy_start(l_reader, l_writer):
    print(f'Establishing connection to {remote_host}:{remote_port}')
    r_reader, r_writer = await asyncio.open_connection(
            remote_host, remote_port)

    init_close = [0,0]
    asyncio.ensure_future(proxy(l_reader, r_writer, 0, init_close))
    asyncio.ensure_future(proxy(r_reader, l_writer, 1, init_close))

if __name__ == '__main__':
    sys.exit(main())





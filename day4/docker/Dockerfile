FROM mont43/rpi-buster-tf2.0:1.1

RUN pip3 --no-cache-dir install \
            pyserial-asyncio \
            dask distributed

WORKDIR "/code"

# Test
RUN python3 -c "import asyncio; import serial_asyncio;"

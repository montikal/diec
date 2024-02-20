# Online Training on Raspberry Pi using TensorFlow

This example performs online training of a gesture detector on a Raspberry Pi,
using live sensor readings from a BBC Micro:bit.

1. Collect data from Micro:bit
2. Train initial model using your machine, save a model checkpoint
3. Load model checkpoint on a Raspberry Pi
4. Continue training on the Raspberry Pi, using live sensor data from the Micro:bit

## Micro:bit Programming
Using the [Python Micro:bit Editor](https://python.microbit.org/v/3), flash a Micro:bit with [microbit/device_code.py](microbit/device_code.py)

## Initial data collection
In this section, you will collect data for your own Micro:bit gesture.

1. Find the serial port path associated with Micro:bit & you need to calibrate micro:bit by tilting it till all LEDs light-up ended with a smiley icon

   a. With the Micro:bit **disconnected**:

       On MacOS, use `ls /dev/cu.*`

       On Windows, open Device Manager and expand "Ports (COM & LPT)"

   b. Connect the Micro:bit:

       On MacOS, use `ls /dev/cu.*`, you should see a path that looks similar to `/dev/cu.usbmodemXXXX`

       On Windows, a new COMXX node should appear under "Ports (COM & LPT)"
   
2. Edit acquire_data.py, update comport to the path found in step 1:

   On MacOS:
    ```
    comport = '/dev/cu.usbmodem144102' # Example MacOS path
    ```

   On Windows:
    ```
    comport = 'COM3' # Example Windows path
    ```

3. Setup the data collection script
    ```
    conda activate diec (same as day 3 conda env)
    conda install pyserial-asyncio
    ```

4. Run the data collection script. 
    ```
    python acquire_data.py
    ```
   As the script is running:
      - press button A to perform the gesture (by moving the Micro:bit)
      - release button A when your gesture completes
      - repeat about 10 times to gather enough data

   Data will be saved to `data.csv`

## Training
1. Open notebook on your laptop under created conda env (python-3.7): [edge_online_learning.ipynb](edge_online_learning.ipynb)
2. Make a copy of the notebook
3. Run each cell of the notebook, step by step
4. Download *.pkl and *.h5 from Colab storage to your laptop

## Online Learning
1. Deploy the *.pkl and *.h5 files to the Raspberry Pi. You can use [WinSCP](https://winscp.net/eng/download.php) (on Windows) or scp (on MacOS) to transfer files to the Raspberry Pi. You should copy the files to this folder:
```
~/diec/day4/rpi
``` 

2. Connect the Micro:bit device to the Raspberry Pi 3, check its serial path:
```
ls /dev/ttyA*
```
Note down the serial path, e.g. `/dev/ttyACM0`

**Important**: the Micro:bit must be connected **before** the docker container is launched, in order for the container to find the serial device.

3. From the Raspberry Pi 3, launch docker container
```
cd ~/diec/day4/docker
sh ./launch_docker.sh
```

4. From the **docker container** on the Raspberry Pi, verify that the serial device can be seen:
```
ls /dev/ttyA*
```

5. From the **docker container** on the Raspberry Pi, incrementally update the model in intervals of N timesteps:
```
cd day4/rpi
python3 incremental_train.py /dev/ttyACM0 --update_interval=2
```
(Substitute `/dev/ttyACM0` with the path from step 2)

## Troubleshooting
For troubleshooting training issues, the incremental_train.py script can also be run on the laptop with the Micro:bit connected. Use the appropriate serial path.
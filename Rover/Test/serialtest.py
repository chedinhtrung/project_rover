import serial

import struct

# Configure the serial port (ttyS0 or ttyAMA0)
ser = serial.Serial(
    port='/dev/ttyS0',  # Use /dev/ttyAMA0 for older Raspberry Pi models
    baudrate=115200,      # Set the baud rate to match your device
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1           # Read timeout in seconds
)

# Function to read data from UART
def read_uart():
    size = struct.calcsize('5f')
    try:
        while True:
            if ser.in_waiting > 0:  # Check if there is data waiting to be read
                data = ser.read(size)
                print(f"Received: {struct.unpack('5f', data)}")  # Print the received data
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()  # Close the serial port

if __name__ == "__main__":
    read_uart()

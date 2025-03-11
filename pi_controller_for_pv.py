# PI controller gains (tune these as needed)
Kp = 0.035
Ki = 0.001

# Sampling time in seconds
dt = 0.5

# Helper functions to parse human-readable sizes and format speeds
def parse_size(s):
    """
    Convert a human-readable size string (e.g. "5.0GiB", "55M", "1K") to bytes.
    Assumes binary multipliers: K = 1024, M = 1024^2, G = 1024^3.
    """
    pattern = r'([\d\.]+)\s*([a-zA-Z]+)'
    m = re.match(pattern, s)
    if not m:
        raise ValueError(f"Invalid size format: {s}")
    value, unit = m.groups()
    value = float(value)
    unit = unit.upper()
    if unit in ['K', 'KB', 'KIB']:
        multiplier = 1024
    elif unit in ['M', 'MB', 'MIB']:
        multiplier = 1024**2
    elif unit in ['G', 'GB', 'GIB']:
        multiplier = 1024**3
    else:
        multiplier = 1
    return int(value * multiplier)

def format_speed(speed):
    """
    Format the speed (in bytes per second) to a string acceptable by pv.
    If the speed is at least 1M, show in M; if at least 1K, show in K; otherwise, in bytes.
    """
    if speed >= 1024**2:
        # Show in megabytes (rounded to nearest integer)
        speed_in_m = speed / (1024**2)
        return f"{int(speed_in_m)}M"
    elif speed >= 1024:
        speed_in_k = speed / 1024
        return f"{int(speed_in_k)}K"
    else:
        return f"{int(speed)}B"

# Convert global strings to numerical values (in bytes)
MAX_SPEED = parse_size(MAX_SPEED_STR)
MIN_SPEED = parse_size(MIN_SPEED_STR)
SETPOINT  = parse_size(SETPOINT_STR)

def get_directory_size(path):
    """
    Run "du -sh <path>" and return the directory size in bytes.
    """
    try:
        # Capture the human-readable size (first field of du output)
        output = subprocess.check_output(["du", "-sh", path], universal_newlines=True)
        size_str = output.split()[0]
        return parse_size(size_str)
    except Exception as e:
        print(f"Error getting directory size: {e}")
        return None

def set_transfer_speed(speed_str):
    """
    Adjust the transfer speed by executing the pv remote command.
    """
    try:
        cmd = ["pv", "--remote", str(PV_PID), "-L", speed_str]
        subprocess.run(cmd, check=True)
        print(f"Set transfer speed to {speed_str}")
    except Exception as e:
        print(f"Error setting transfer speed: {e}")

def main():
    integral = 0.0  # integral term initialization
    path = "/mnt/Argon/upload_to_telia/ramdisk/chunks/"

    while True:
        current_size = get_directory_size(path)
        if current_size is None:
            time.sleep(dt)
            continue

        # Compute error (in bytes)
        error = SETPOINT - current_size

        # Update the integral term
        integral += error * dt

        # PI controller output: u = Kp * error + Ki * integral
        # This output is interpreted as the desired transfer speed in bytes/s.
        u = Kp * error + Ki * integral

        # Clamp the controller output between MIN_SPEED and MAX_SPEED
        u = max(MIN_SPEED, min(u, MAX_SPEED))

        # Format speed for the pv command
        speed_str = format_speed(u)

        # Set the new transfer speed
        set_transfer_speed(speed_str)

        time.sleep(dt)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("PI controller stopped.")
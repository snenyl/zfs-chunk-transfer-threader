import time
import hashlib
import subprocess
from pathlib import Path
from queue import Queue
import uuid

WATCH_DIR = Path("/mnt/Argon/upload_to_telia/ramdisk/chunks")
MD5_FILE = Path("simon-dataset.md5")
REMOTE_PATH = "telia_privat:simon-dataset"
CHECK_INTERVAL = 0.5  # Seconds
MAX_THREADS = 10

# Queue for files that are stable and ready for processing.
file_queue = Queue()

def is_file_stable(file_path, interval=2, checks=3):
    """Blocking check to see if file size is stable over several checks."""
    print(f"Checking if file is stable: {file_path}")
    previous_size = -1
    stable_checks = 0
    while stable_checks < checks:
        try:
            current_size = file_path.stat().st_size
        except FileNotFoundError:
            print(f"File not found during stability check: {file_path}")
            return False
        print(f"File size check ({stable_checks+1}/{checks}): {current_size}")
        if current_size == previous_size:
            stable_checks += 1
        else:
            stable_checks = 0
            previous_size = current_size
        time.sleep(interval)
    print(f"File is stable: {file_path}")
    return True

def monitor_file(file_path):
    """Monitors a file until it becomes stable, then enqueues it for processing."""
    if is_file_stable(file_path):
        file_queue.put(file_path)
    else:
        print(f"File {file_path} did not become stable, skipping.")

def calculate_md5(file_path, chunk_size=4096):
    """Calculates the MD5 checksum for a given file."""
    print(f"Calculating MD5 for: {file_path}")
    md5 = hashlib.md5()
    with file_path.open('rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            md5.update(chunk)
    md5sum = md5.hexdigest()
    print(f"MD5 calculated: {md5sum}")
    return md5sum

def append_md5_to_file(md5, filename):
    """Appends an MD5 checksum and filename to the MD5 file if not already present."""
    entry = f"{md5}  {filename}\n"
    if MD5_FILE.exists():
        with MD5_FILE.open('r') as f:
            if any(filename == line.strip().split('  ')[1] for line in f):
                print(f"Entry already exists for {filename}, skipping.")
                return
    print(f"Appending MD5 to file: {MD5_FILE}, Entry: {entry.strip()}")
    with MD5_FILE.open('a') as f:
        f.write(entry)

def verify_remote_copy(local_path):
    """Verifies a single uploaded file using rclone check."""
    print(f"Verifying remote copy for: {local_path.name}")
    temp_md5_file = Path(f"temp_verify_{uuid.uuid4().hex}.md5")
    md5sum = calculate_md5(local_path)  # Recalculate MD5 to ensure consistency
    with temp_md5_file.open('w') as dst:
        dst.write(f"{md5sum}  {local_path.name}\n")
    result = subprocess.run(
        ["rclone", "check", "--one-way", "-C", "md5", str(temp_md5_file), REMOTE_PATH, "-vv"],
        capture_output=True, text=True
    )
    temp_md5_file.unlink(missing_ok=True)
    verification = "0 differences found" in result.stderr
    print(f"rclone stdout: {result.stdout}")
    print(f"rclone stderr: {result.stderr}")
    print(f"Verification result for {local_path.name}: {'Success' if verification else 'Failure'}")
    return verification

def process_file():
    """Worker thread that processes stable files from the file_queue."""
    while True:
        file_path = file_queue.get()
        if file_path is None:
            print("Worker received shutdown signal.")
            break

        print(f"Processing file: {file_path}")
        # File is assumed to be stable, so directly calculate MD5 and proceed.
        md5sum = calculate_md5(file_path)
        print(f"Starting rclone copy for: {file_path}")
        copy_result = subprocess.run(
            ["rclone", "copy", str(file_path), REMOTE_PATH],
            capture_output=True, text=True
        )
        print(f"rclone copy output: {copy_result.stdout}")
        print(f"rclone copy error (if any): {copy_result.stderr}")

        if copy_result.returncode == 0 and verify_remote_copy(file_path):
            append_md5_to_file(md5sum, file_path.name)
            print(f"Deleting local file: {file_path}")
            file_path.unlink()
        else:
            print(f"Failed to copy or verify: {file_path}")

        file_queue.task_done()
        print(f"Finished processing file: {file_path}")

def watch_directory():
    """Watches for new files and spawns a monitor thread for each new file."""
    print("Starting directory watch.")
    # Start worker threads
    worker_threads = []
    for _ in range(MAX_THREADS):
        t = threading.Thread(target=process_file, daemon=True)
        t.start()
        worker_threads.append(t)

    monitored_files = set()
    while True:
        current_files = set(WATCH_DIR.glob("*"))
        new_files = current_files - monitored_files
        for file_path in new_files:
            if file_path.is_file():
                print(f"New file detected: {file_path}")
                monitored_files.add(file_path)
                # Launch a dedicated thread to monitor this file until it is stable.
                threading.Thread(target=monitor_file, args=(file_path,), daemon=True).start()
        time.sleep(CHECK_INTERVAL)

    # Cleanup (this part will likely not be reached in an infinite loop).
    file_queue.join()
    for _ in worker_threads:
        file_queue.put(None)
    for t in worker_threads:
        t.join()

if __name__ == "__main__":
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Watching directory: {WATCH_DIR}")
    watch_directory()


# ZFSChunkTransferThreader

ZFSChunkTransfer is a multi-threaded file transfer utility that monitors a directory (chunks/), detects new files, verifies their stability, computes MD5 checksums, and transfers them to a remote destination using rclone. It ensures data integrity by verifying each transfer before deleting local copies.

This tool is especially useful when your ZFS pool is reaching 80% capacity and you need to backup datasets to the cloud, rebuild a new pool, and then restore them using zfs receive.

⚠️ **Note:** Use at your own risk—I take no responsibility for missing chunks.



## Features

- **Multi-threaded Processing**: Utilizes up to 30 worker threads for concurrent file transfers.
- **File Stability Check**: Ensures files are fully written before processing.
- **MD5 Hashing**: Computes and logs MD5 checksums for data integrity.
- **Automatic Transfer**: Uses `rclone` to copy files to a remote location.
- **Transfer Verification**: Confirms successful file transfers by comparing MD5 hashes.
- **Automatic Cleanup**: Deletes local files after successful verification.
- **Designed for FreeBSD**: Uses `split` and `zfs send` for snapshot transfers.

## Installation

Ensure `rclone` is installed and configured for your remote storage destination. You can install `rclone` via:

```shell
pkg install rclone  # FreeBSD
apt install rclone  # Debian-based Linux
brew install rclone # macOS
```

## Usage

1. **Start the script**:

   ```shell
   python3 main.py
   ```

   This will start watching the `chunks/` directory for new files.

2. **Send a ZFS snapshot and split into chunks**:

   ```shell
   zfs send --raw Argon/Private@manual-2025-03-10_18-33 | split -b 64M - dataset-snap.img.
   ```

   You can adjust the desired chunk size based on how fast the dataset is converted and your internet speed. A chunk size of `128M` works well for `1Gbit` links.

3. **Monitor the directory**:

   ```shell
   while :; do du -sh; sleep 1; done
   ```

   ```shell
   while :; do ls | wc -l; sleep 1; done
   ```

   ```shell
   while :; do ps -f | grep rclone | wc -l; sleep 1; done
   ```

4. **Completed transfer, verify with the gerated MD5 file**:
   ```shell
   rclone check --one-way  -C md5 files.md5 telia_privat:plugins -vv
   ```

## Configuration

The script's parameters can be adjusted in `main.py`:

- **`WATCH_DIR`**: Directory to monitor for new files (`./chunks/` by default).
- **`REMOTE_PATH`**: Remote storage destination (`telia_privat:plugins`).
- **`CHECK_INTERVAL`**: Interval (in seconds) to scan for new files (`5s` by default).
- **`MAX_THREADS`**: Number of worker threads (`30` by default).

## How It Works

1. Watches the `chunks/` directory for new files.
2. Waits for each file to stabilize (i.e., stop growing in size).
3. Computes the MD5 checksum of the stable file.
4. Transfers the file to the remote destination using `rclone`.
5. Verifies the remote copy by comparing MD5 hashes.
6. If successful, logs the MD5 checksum and deletes the local file.
7. Repeats for all new files detected.

## Notes

- The script is optimized for FreeBSD, where `watch` is not natively installed.
- Uses `rclone check` to validate transfers, ensuring data integrity.
- If `rclone` reports a transfer failure, the local file is not deleted.

## License

This project is licensed under the MIT License.



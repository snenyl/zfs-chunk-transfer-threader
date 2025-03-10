# Placeholder for saving chunks



## Useful command

Run the following command inside chunks

```shell
zfs send --raw Argon/Private@manual-2025-03-10_18-33 | split -b 64M - dataset-snap.img.
```


### Some other useful commands to run while inside chunks/ for monitoring

```shell 
while :; do du -sh; sleep 1; done
```

```shell 
while :; do ls | wc -l; sleep 1; done
```

```shell 
while :; do ps -f | grep rclone | wc -l; sleep 1; done
```

Note, this is intended to run on FreeBSD as "watch" is not natevly installed


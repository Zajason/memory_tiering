# Research storage on this workstation

Ubuntu, its EFI files, source code and compilation remain on the Samsung 980 SSD.
The additional TOSHIBA DT01ACA100 HDD (serial 88IWB87MS) is mounted at
`/mnt/research` as ext4, UUID `959220bd-c653-4630-9360-4bd0498b7812`.
Its startup entry uses `nofail` and a ten-second device timeout; losing the data
drive does not prevent Ubuntu from booting.

`/mnt/research/memory-tiering/` contains large datasets, verified raw records,
checkpoint-validation runs and simulator snapshots. None of these are required
to boot. The HDD has lower random-I/O performance than the SSD, so hot source
trees and builds remain on the SSD. Instrumented wall times are never treated
as application performance measurements.

`experiments/migrate_raw_storage.py` verifies SHA256 after copying each ignored
raw record file, then atomically replaces its original path with a symlink to
the verified HDD copy. Commands and recorded result prefixes remain usable.
The destination includes a JSON hash/size record. It does not move tracked
summaries, plots or source code. The first migration freed roughly 12 GiB on
the SSD. Do not delete the HDD copies: the repository links depend on them.

The mount is verified now; actual reboot mounting has not yet been tested.
After reboot, check `findmnt /mnt/research` before starting jobs. Linux being
shut down still stops computation: disk snapshots must be finalized before
switching to Windows. Do not modify snapshot inputs from Windows.

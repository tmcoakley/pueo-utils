# xilframe

Converts a clock region's worth of RAMB36s (12) into their
contents.

Note that for PUEO this isn't built locally, the binary is
stored in scripts/ since obviously it needs to be ARM64.

There are tons of magic words in this file. They're extracted
from the logic location file, and then offset and such. Don't
worry about them.

Dumps to stdout, so just do xilframe dump > contents

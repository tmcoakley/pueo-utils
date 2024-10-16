# PUEO extra modules in PyRun

These directories need to be copied into the python installation
directory during the PyRun build so that PyRun can see them.

We can only add pure Python modules this way (I think). The
custom fork of PyRun modifies the Makefile to add targets to
do this semi-automatically if you tar up this directory
and pass it as PYRUNEXTRAS=this_tar.gz: you do

```
make interpreter
make install-pyrun-extras
make runtime
```

although you need to make sure PYTHONFULLVERSION and PYTHONTARDIR
are specified correctly as well.
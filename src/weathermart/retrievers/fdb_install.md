# Install spack
```bash
git clone --depth=100 --branch=releases/v0.22 https://github.com/spack/spack.git ~/spack
vim spack-env.yaml
```
# Set up spack command line tool
To write "spack ..." you need to install the command line tool.
```bash
cd spack
. ./share/spack/setup-env.sh
```

# Create the spack environment for FDB
Create the following file in your home directory (or scratch, or wherever). This file will be used to configure the Spack environment.
```yaml
spack:
  specs:
    - fdb@=5.11.126 +tools
    - eckit@=1.26.3 ~mpi
    - eccodes@=2.35.0 jp2k=none
    - metkit@=1.11.14
  view: $SCRATCH/spack-view
  concretizer:
    unify: true
  config:
    install_tree:
      root: $SCRATCH/spack-root
```

# Install FDB
Then you can install FDB. The FDB retriever will now be accessible.
```bash
spack env create spack-env spack-env.yaml
spack env activate -p spack-env
spack install
```

In your conda environment, you should also execute the following command to make the FDB retriever accessible:
```bash
git clone -b mars-levtype-echotop-2 https://github.com/cfkanesan/eccodes-cosmo-resources.git $CONDA_PREFIX/share/eccodes-cosmo-resources
```

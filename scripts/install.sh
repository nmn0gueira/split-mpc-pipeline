#!/usr/bin/env bash

set -e

fromsource=$1
MP_SPDZ_VERSION="0.4.2"

if [ "$fromsource" = "yes" ]; then
    # this may take a long time
    git clone https://github.com/data61/MP-SPDZ.git
    cd MP-SPDZ
    git checkout v$MP_SPDZ_VERSION

    make setup
    make all -j
else
    curl -L https://github.com/data61/MP-SPDZ/releases/download/v$MP_SPDZ_VERSION/mp-spdz-$MP_SPDZ_VERSION.tar.xz | tar xJv
    mv mp-spdz-$MP_SPDZ_VERSION MP-SPDZ
    cd MP-SPDZ
    Scripts/tldr.sh
fi


CLIENT=client-input

# Add rules to compile our client file with MP-SPDZ libs. These are just copied to be the same as the ones from the bankers-bonus-client example
sed -i -E "/^externalIO/ s/$/ ${CLIENT}.x/" Makefile

echo "${CLIENT}.x: ExternalIO/${CLIENT}.o \$(COMMON)
	\$(CXX) \$(CFLAGS) -o \$@ $^ \$(LDLIBS)" >> Makefile

cp "../src/${CLIENT}.cpp" "ExternalIO/${CLIENT}.cpp"

make "${CLIENT}.x"

# Scripts/setup-ssl.sh 3
# Scripts/setup-clients.sh 3

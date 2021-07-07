FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive

###############################
########## PACKAGES ###########
###############################

RUN apt-get update \
    && apt-get install -y software-properties-common curl tzdata libgtk2.0-0 libxtst6 \
    libwebkitgtk-3.0-0 python python-dev python-pip r-base r-recommended

###### MARVIN ####

WORKDIR /home/extra_packages/

ENV MARVIN_VERSION=20.9

COPY marvin_linux_$MARVIN_VERSION.deb /home/extra_packages/
COPY license.cxl /home/extra_packages/
ENV CHEMAXON_LICENSE_URL /home/extra_packages/license.cxl
RUN dpkg -i /home/extra_packages/marvin_linux_$MARVIN_VERSION.deb
RUN rm /home/extra_packages/marvin_linux_$MARVIN_VERSION.deb

###############################
########## RETROPATH 2 ########
###############################

WORKDIR /home/rp2/

ENV KNIME_VERSION_SHORT=4.3
ENV KNIME_VERSION=$KNIME_VERSION_SHORT.0
ENV INSTALLATION_DIR_RP2 /usr/local
ENV KNIME_DIR $INSTALLATION_DIR_RP2/knime
ENV HOME_KNIME_DIR /home/rp2/knime

 # Download KNIME
RUN curl -L "https://download.knime.org/analytics-platform/linux/knime_$KNIME_VERSION.linux.gtk.x86_64.tar.gz" | tar vxz -C $INSTALLATION_DIR_RP2 \
    && mv $INSTALLATION_DIR_RP2/knime_* $INSTALLATION_DIR_RP2/knime

#Install pandas and protobuf so KNIME can communicate with python
RUN pip install pandas protobuf

# Install Rserver so KNIME can communicate with R
RUN R -e 'install.packages(c("Rserve"), repos="http://cran.rstudio.com/")'

# Build argument for the workflow directory
ONBUILD ARG WORKFLOW_DIR="workflow/"
# Build argument for additional update sites
ONBUILD ARG UPDATE_SITES

# Create workflow directory and copy from host
ONBUILD RUN mkdir -p /payload
ONBUILD COPY $WORKFLOW_DIR /payload/workflow
 
# Create metadata directory
ONBUILD RUN mkdir -p /payload/meta

# Copy necessary scripts onto the image
RUN mkdir /home/rp2/scripts/
COPY docker_conf/getversion.py /home/rp2/scripts/getversion.py
COPY docker_conf/listvariables.py /home/rp2/scripts/listvariables.py
COPY docker_conf/listplugins.py /home/rp2/scripts/listplugins.py
COPY docker_conf/run.sh /home/rp2/scripts/run.sh

# Let anyone run the workflow
RUN chmod +x /home/rp2/scripts/run.sh

# Add KNIME update site and trusted community update site that fit the version the workflow was created with
ONBUILD RUN full_version=$(python /home/rp2/scripts/getversion.py /payload/workflow/) \
	&& version=$(python /home/rp2/scripts/getversion.py /payload/workflow/ | awk '{split($0,a,"."); print a[1]"."a[2]}') \
	&& echo "http://update.knime.org/analytics-platform/$version" >> /payload/meta/updatesites \
	&& echo "http://update.knime.org/community-contributions/trusted/$version" >> /payload/meta/updatesites \
	# Add user provided update sites
	&& echo $UPDATE_SITES | tr ',' '\n' >> /payload/meta/updatesites

# Save the workflow's variables in a file
ONBUILD RUN find /payload/workflow -name settings.xml -exec python /home/rp2/scripts/listplugins.py {} \; | sort -u | awk '!a[$0]++' > /payload/meta/features

ONBUILD RUN python /home/rp2/scripts/listvariables.py /payload/workflow

# Install required features
ONBUILD RUN "$KNIME_DIR/knime" -application org.eclipse.equinox.p2.director \
	-r "$(cat /payload/meta/updatesites | tr '\n' ',' | sed 's/,*$//' | sed 's/^,*//')" \
	-p2.arch x86_64 \
	-profileProperties org.eclipse.update.install.features=true \
	-i "$(cat /payload/meta/features | tr '\n' ',' | sed 's/,*$//' | sed 's/^,*//')" \
	-p KNIMEProfile \
	-nosplash

############################### Workflow ##############################

#version 9
#ENV RETROPATH_VERSION 9
#ENV RETROPATH_URL https://myexperiment.org/workflows/4987/download/RetroPath2.0_-_a_retrosynthesis_workflow_with_tutorial_and_example_data-v${RETROPATH_VERSION}.zip?version=9
#ENV RETROPATH_SHA256 79069d042df728a4c159828c8f4630efe1b6bb1d0f254962e5f40298be56a7c4

#version 10
ENV RETROPATH_VERSION 10
ENV RETROPATH_URL https://myexperiment.org/workflows/4987/download/RetroPath2.0_-_a_retrosynthesis_workflow_with_tutorial_and_example_data-v${RETROPATH_VERSION}.zip?version=10
ENV RETROPATH_SHA256 e2ac2c94e9ebe4ede454195bb26f788d3ad7e219bb0e16605cf9a5c72aae9b57

# Download RetroPath2.0
#WORKDIR /home/
RUN echo "$RETROPATH_SHA256 RetroPath2_0.zip" > /home/rp2/RetroPath2_0.zip.sha256
RUN cat /home/rp2/RetroPath2_0.zip.sha256
RUN echo Downloading $RETROPATH_URL
#RUN curl -v -L -o /home/rp2/RetroPath2_0.zip $RETROPATH_URL && sha256sum /home/rp2/RetroPath2_0.zip && sha256sum -c RetroPath2_0.zip.sha256
RUN curl -v -L -o RetroPath2_0.zip $RETROPATH_URL && sha256sum RetroPath2_0.zip && sha256sum -c /home/rp2/RetroPath2_0.zip.sha256
RUN unzip RetroPath2_0.zip && mv RetroPath2.0/* /home/rp2/
RUN rm RetroPath2_0.zip
RUN rm -r RetroPath2.0
RUN rm -r __MACOSX

#install the additional packages required for running retropath KNIME workflow
#RUN /usr/local/knime/knime -application org.eclipse.equinox.p2.director -nosplash -consolelog \
#-r http://update.knime.org/community-contributions/trunk,\
#http://update.knime.com/analytics-platform/$KNIME_VERSION_SHORT,\
#http://update.knime.com/community-contributions/trusted/$KNIME_VERSION_SHORT \
#-l org.knime.features.chem.types.feature.group,\
#org.knime.features.datageneration.feature.group,\
#jp.co.infocom.cheminfo.marvin.feature.feature.group,\
#org.knime.features.python.feature.group,\
#org.rdkit.knime.feature.feature.group \
#-bundlepool /usr/local/knime/ -d /usr/local/knime/

RUN /usr/local/knime/knime -application org.eclipse.equinox.p2.director -nosplash -consolelog -r http://update.knime.org/community-contributions/trunk,http://update.knime.com/analytics-platform/$KNIME_VERSION_SHORT,http://update.knime.com/community-contributions/trusted/4.2 -i org.rdkit.knime.feature.feature.group,org.knime.features.python.feature.group,org.knime.features.datageneration.feature.group,org.knime.features.chem.types.feature.group -bundlepool /usr/local/knime/ -d /usr/local/knime/

############################################
############ RP2paths ######################
############################################

RUN apt-get update \
    && apt-get install -y ca-certificates build-essential cmake wget xz-utils \
    libboost-dev \
    libboost-iostreams-dev \
    libboost-python-dev \
    libboost-regex-dev \
    libboost-serialization-dev \
    libboost-system-dev \
    libboost-thread-dev \
    libcairo2-dev \
    libeigen3-dev \
    python3 python3-dev python3-pip \
    supervisor redis redis-server \
    graphviz default-jdk libxrender-dev libxext6  

RUN pip3 install pandas graphviz pydotplus lxml numpy

#### install RDKIT #####
WORKDIR /
ARG RDKIT_VERSION=Release_2021_03_3
RUN wget --quiet https://github.com/rdkit/rdkit/archive/${RDKIT_VERSION}.tar.gz \
	&& tar -xzf ${RDKIT_VERSION}.tar.gz \
	&& mv rdkit-${RDKIT_VERSION} /rdkit \
	&& rm ${RDKIT_VERSION}.tar.gz

RUN cd /rdkit/External/INCHI-API && \
	./download-inchi.sh

WORKDIR /rdkit/build/

RUN cmake -D RDK_BUILD_INCHI_SUPPORT=ON \ 
          -D PYTHON_EXECUTABLE=/usr/bin/python3.6 \
	.. && \
	make && \
	make install 

RUN make -j $(nproc) \
	&& make install

ENV RDBASE /rdkit
ENV LD_LIBRARY_PATH $RDBASE/lib
ENV PYTHONPATH $PYTHONPATH:$RDBASE

RUN mkdir /home/rp2paths/
WORKDIR /home/rp2paths/

# Download and "install" rp2paths release
# Check for new versions from 
# https://github.com/brsynth/rp2paths/releases
ENV RP2PATHS_VERSION 1.4.2
#ENV RP2PATHS_URL https://github.com/brsynth/rp2paths/archive/v${RP2PATHS_VERSION}.tar.gz
ENV RP2PATHS_URL https://github.com/brsynth/rp2paths/archive/refs/tags/${RP2PATHS_VERSION}.tar.gz
# NOTE: Update sha256sum for each release
ENV RP2PATHS_SHA256 2583997c5de12905b0fa534067cffbd072fed7a6a458d683b552cc43ff5c2cc7
RUN echo "$RP2PATHS_SHA256  rp2paths.tar.gz" > /home/rp2paths/rp2paths.tar.gz.sha256
RUN cat /home/rp2paths/rp2paths.tar.gz.sha256
RUN echo Downloading $RP2PATHS_URL
RUN curl -v -L -o rp2paths.tar.gz $RP2PATHS_URL
RUN echo "sha256sum rp2paths.tar.gz"
RUN sha256sum rp2paths.tar.gz && sha256sum -c /home/rp2paths/rp2paths.tar.gz.sha256
RUN tar xfv rp2paths.tar.gz && mv rp2paths-*/* /home/rp2paths/
RUN rm rp2paths.tar.gz
RUN rm -r rp2paths-*

#############################################
######### RetroRules ########################
#############################################

RUN mkdir /home/retrorules/
WORKDIR /home/retrorules/

RUN wget https://retrorules.org/dl/preparsed/rr02/rp2/hs -O /home/retrorules/rules_rall_rp2.tar.gz && \
    tar xf /home/retrorules/rules_rall_rp2.tar.gz -C /home/retrorules/ && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_forward.csv /home/retrorules/rules_rall_rp2_forward.csv && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_retro.csv /home/retrorules/rules_rall_rp2_retro.csv && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_all.csv /home/retrorules/rules_rall_rp2.csv && \
    rm -r /home/retrorules/retrorules_rr02_rp2_hs && \
    rm /home/retrorules/rules_rall_rp2.tar.gz

########## sanity test ##########

ADD retrosynthesis /home/retrosynthesis/
COPY README.md /home/README.md
COPY LICENSE /home/LICENSE
#IMPORTANT: tells KNIME where to find the python executables
COPY docker_conf/pref.epf /home/retrosynthesis/pref.epf
WORKDIR /home/retrosynthesis/
RUN pip3 install -e .

COPY test/sanity_test.py /home/
COPY test/sanity_test.tar.xz /home/
RUN tar xfv /home/sanity_test.tar.xz -C /home/
RUN tar xfv /home/sanity_test/rules.tar -C /home/sanity_test/

############################# Files and Tests #############################

ENV RP2_STANDALONE_SHA256 6d461c38ea2913e26be1c60b32691914e6c823f543bdf37ac83506322ffa5813
ENV RP2PATHS_PATH_STANDALONE_SHA256 9ff541870684a7dae3587cfe266bf5c369fbb430368dec786cf08c9fa6989dcb
ENV RP2PATHS_CMP_STANDALONE_SHA256 dd60ef2de5b876092d324b09905db1b5d4704885cb5f3206c4f26ec51f465e90
ENV RP2_PIPE_SHA256 2acddab18572d27fe7000d6d70c0621c2e3e9cee4e1beb6f4a12ec9ecf3e7502
ENV RP2PATHS_PATH_PIPE_SHA256 7e11aeba4fb76735f3b40d356df88a10c8bb75d260cc85216b02b78c7c329f90 
ENV RP2PATHS_CMP_PIPE_SHA256 d09cf7c1adbe091cf4e534aa2bdeac86462efd475e7c71306f540fd24d776045
RUN runRP2 -sink_path /home/sanity_test/sinkfile.csv -source_inchi 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1' -results_csv /home/sanity_test/results.csv -rules_path /home/sanity_test/Rules.csv
RUN echo "$RP2_STANDALONE_SHA256 /home/sanity_test/results.csv" | sha256sum --check
RUN runRP2paths -rp2_pathways /home/sanity_test/results.csv -out_paths /home/sanity_test/rp2_paths.csv -out_compounds /home/sanity_test/rp2_cmps.csv
RUN echo "$RP2PATHS_PATH_STANDALONE_SHA256 /home/sanity_test/rp2_paths.csv" | sha256sum --check
RUN echo "$RP2PATHS_CMP_STANDALONE_SHA256 /home/sanity_test/rp2_cmps.csv" | sha256sum --check
RUN rppipeline -sink /home/sanity_test/sinkfile.csv -source 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1' -orp /home/sanity_test/rp2.csv -orp2p /home/sanity_test/rp2paths_p.csv -orp2pc /home/sanity_test/rp2paths_c.csv
RUN echo "$RP2_PIPE_SHA256 /home/sanity_test/rp2.csv" | sha256sum --check
RUN echo "$RP2PATHS_PATH_PIPE_SHA256 /home/sanity_test/rp2paths_p.csv" | sha256sum --check
RUN echo "$RP2PATHS_CMP_PIPE_SHA256 /home/sanity_test/rp2paths_c.csv" | sha256sum --check
WORKDIR /home/

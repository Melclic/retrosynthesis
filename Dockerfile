FROM ubuntu:18.04

###############################
########## PACKAGES ###########
###############################

RUN apt-get update \
    && apt-get install -y software-properties-common curl ca-certificates build-essential wget xz-utils \
    tzdata libgtk2.0-0 libxtst6 libwebkitgtk-3.0-0 python python-dev python-pip python3 python3-dev python3-pip \
    r-base r-recommended \
    supervisor redis redis-server \
    graphviz openjdk-8-jre libxrender-dev libxext6  

RUN R -e 'install.packages(c("Rserve"), repos="http://cran.rstudio.com/")'

RUN pip3 install pandas protobuf flask-restful redis rq graphviz pydotplus lxml

###############################
########## RETROPATH 2 ########
###############################

WORKDIR /home/
RUN mkdir /home/rp2/
RUN cd /home/rp2/

ENV DOWNLOAD_URL_RP2 https://download.knime.org/analytics-platform/linux/knime_4.2.2.linux.gtk.x86_64.tar.gz
ENV INSTALLATION_DIR_RP2 /usr/local
ENV KNIME_DIR $INSTALLATION_DIR_RP2/knime
ENV HOME_KNIME_DIR /home/rp2/knime

 # Download KNIME
RUN curl -L "$DOWNLOAD_URL_RP2" | tar vxz -C $INSTALLATION_DIR_RP2 \
    && mv $INSTALLATION_DIR_RP2/knime_* $INSTALLATION_DIR_RP2/knime

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
COPY rp2/docker_conf/getversion.py /home/rp2/scripts/getversion.py
COPY rp2/docker_conf/listvariables.py /home/rp2/scripts/listvariables.py
COPY rp2/docker_conf/listplugins.py /home/rp2/scripts/listplugins.py
COPY rp2/docker_conf/run.sh /home/rp2/scripts/run.sh

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

ENV RETROPATH_VERSION 9
ENV RETROPATH_URL https://myexperiment.org/workflows/4987/download/RetroPath2.0_-_a_retrosynthesis_workflow_with_tutorial_and_example_data-v${RETROPATH_VERSION}.zip
ENV RETROPATH_SHA256 79069d042df728a4c159828c8f4630efe1b6bb1d0f254962e5f40298be56a7c4

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
RUN /usr/local/knime/knime -application org.eclipse.equinox.p2.director -nosplash -consolelog \
-r http://update.knime.org/community-contributions/trunk,\
http://update.knime.com/analytics-platform/4.2,\
http://update.knime.com/community-contributions/trusted/4.2 \
-i org.knime.features.chem.types.feature.group,\
org.knime.features.datageneration.feature.group,\
jp.co.infocom.cheminfo.marvin.feature.feature.group,\
org.knime.features.python.feature.group,\
org.rdkit.knime.feature.feature.group \
-bundlepool /usr/local/knime/ -d /usr/local/knime/

############################# Files and Tests #############################

COPY rp2/callRP2.py /home/
COPY rp2/supervisor.conf /home/
COPY rp2/start_rp2.sh /home/
git@github.com:Galaxy-SynBioCAD/RetroPath2.git
COPY rp2/rp2_sanity_test.tar.xz /home/rp2/

#test
ENV RP2_RESULTS_SHA256 7428ebc0c25d464fbfdd6eb789440ddc88011fb6fc14f4ce7beb57a6d1fbaec2
RUN tar xf /home/rp2/rp2_sanity_test.tar.xz -C /home/rp2/
RUN chmod +x /home/callRP2.py
RUN /home/callRP2.py -sinkfile /home/rp2/test/sink.csv -sourcefile /home/rp2/test/source.csv -rulesfile /home/rp2/test/rules.tar -rulesfile_format tar -max_steps 3 -output_csv /home/rp2/test_scope.csv
RUN echo "$RP2_RESULTS_SHA256 /home/rp2/test_scope.csv" | sha256sum --check

############################################
############ RP2paths ######################
############################################

RUN mkdir /home/rp2paths/
RUN cd /home/rp2paths/

# Download and "install" rp2paths release
# Check for new versions from 
# https://github.com/brsynth/rp2paths/releases
ENV RP2PATHS_VERSION 1.0.2
ENV RP2PATHS_URL https://github.com/brsynth/rp2paths/archive/v${RP2PATHS_VERSION}.tar.gz
# NOTE: Update sha256sum for each release
ENV RP2PATHS_SHA256 3813460dea8bb02df48e1f1dfb60751983297520f09cdfcc62aceda316400e66
RUN echo "$RP2PATHS_SHA256  rp2paths.tar.gz" > /home/rp2paths/rp2paths.tar.gz.sha256
RUN cat /home/rp2paths/rp2paths.tar.gz.sha256
RUN echo Downloading $RP2PATHS_URL
RUN curl -v -L -o rp2paths.tar.gz $RP2PATHS_URL && sha256sum rp2paths.tar.gz && sha256sum -c /home/rp2paths/rp2paths.tar.gz.sha256
RUN tar xfv rp2paths.tar.gz && mv rp2paths-*/* /home/rp2paths/
RUN grep -q '^#!/' /home/rp2paths/RP2paths.py || sed -i '1i #!/usr/bin/env python3' /home/rp2paths/RP2paths.py
RUN rm rp2paths.tar.gz
RUN rm -r rp2paths-*

COPY rp2paths/callRP2paths.py /home/

#############################################
######### RetroRules ########################
#############################################

RUN mkdir /home/retrorules/
RUN cd /home/retrorules/

RUN wget https://retrorules.org/dl/preparsed/rr02/rp2/hs -O /home/retrorules/rules_rall_rp2.tar.gz && \
    tar xf /home/retrorules/rules_rall_rp2.tar.gz -C /home/retrorules/ && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_forward.csv /home/retrorules/rules_rall_rp2_forward.csv && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_retro.csv /home/retrorules/rules_rall_rp2_retro.csv && \
    mv /home/retrorules/retrorules_rr02_rp2_hs/retrorules_rr02_rp2_flat_all.csv /home/retrorules/rules_rall_rp2.csv && \
    rm -r /home/retrorules/retrorules_rr02_rp2_hs && \
    rm /home/retrorules/rules_rall_rp2.tar.gz

COPY retrorules/callRR.py /home/

RUN cd /home/

ENTRYPOINT []

from --platform=linux/amd64 knime/knime:r-4.7.8-738

USER root

ENV CONDA_DIR=/home/knime/miniconda3

RUN 	apt-get update && \
	apt-get install unzip curl python2 bzip2 ca-certificates --yes && \
	apt-get clean && \
	curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" && \
	bash Miniforge3-$(uname)-$(uname -m).sh -b -p $CONDA_DIR && \
	rm Miniforge3-$(uname)-$(uname -m).sh && \
	chown -R knime:knime $CONDA_DIR

USER knime

ENV PATH=/home/knime/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN conda install -c rdkit -c conda-forge -c brsynth -c bioconda rrparser retropath2_wrapper rp2paths rp2paths rdkit=2025.03.6 -y

WORKDIR /home/knime

RUN /home/knime/knime/knime -application org.eclipse.equinox.p2.director -nosplash -consolelog -r \
https://update.knime.org/community-contributions/trunk,\
https://update.knime.com/analytics-platform/4.7,\
https://update.knime.com/community-contributions/trusted/4.7 \
-i \
org.knime.features.chem.types.feature.group/4.7.1.v202301311311,\
org.knime.features.core.columnar.feature.group/4.7.4.v202306091215,\
org.knime.features.datageneration.feature.group/4.7.0.v202211082353,\
org.knime.features.js.views.feature.group/4.7.0.v202211091556,\
org.knime.features.javasnippet.feature.group/4.7.0.v202211082357,\
org.knime.features.json.feature.group/4.7.0.v202212030000,\
org.knime.features.ext.jep.feature.group/4.7.0.v202208041429,\
org.knime.features.python.feature.group/4.7.1.v202301311311,\
org.knime.features.js.quickforms.feature.group/4.7.4.v202306091222,\
org.knime.features.stats.feature.group/4.7.0.v202206271529,\
org.knime.features.timeseries.feature.group/4.7.0.v202209020834,\
org.knime.features.xml.feature.group/4.7.0.v202211082337,\
org.rdkit.knime.binaries.feature.feature.group/4.9.1.v202312081930,\
org.rdkit.knime.feature.feature.group/4.9.1.v202312081930 \
-bundlepool /home/knime/knime/ -d /home/knime/knime/

#######################################
######## RetroPath2 ###################
#######################################

WORKDIR /home/rp2/

ENV RETROPATH_VERSION 16
ENV RETROPATH_URL http://www.myexperiment.org/workflows/4987/download/RetroPath2.0_-_a_retrosynthesis_workflow_with_tutorial_and_example_data-v$RETROPATH_VERSION.zip?version=$RETROPATH_VERSION
ENV RETROPATH_SHA256 842a3a7545dd3a25aed87aba6e54ffefdcec6fc043da5924e37ae7602d677317

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




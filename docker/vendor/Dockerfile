ARG NODE_VERSION=24

FROM diatem/nodejs:${NODE_VERSION}

ARG WWWUSER=prod
# Create a group and user
RUN adduser -D $WWWUSER -G node -s /bin/bash 
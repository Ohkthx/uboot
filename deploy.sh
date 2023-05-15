#!/usr/bin/env bash

# MUST HAVE THE FOLLOWING VOLUMES
# docker volume create uboot_dbs
# docker volume create uboot_images
# docker volume create uboot_configs

# Stop the container
echo "Stopping the container if it is running..."
docker stop uboot

# Remove all old containers / images
echo -e "\nRemoving container..."
docker container rm uboot

echo -e "\nRemoving image..."
docker image rm uboot

# Create new image.
echo -e "\nBuild new image..."
docker build -t uboot .

# Start new container.
echo -e "\nStarting new container..."
docker run -d --restart unless-stopped --name uboot \
	--mount source=uboot_dbs,destination=/dbs \
	--mount source=uboot_images,destination=/images \
	--mount source=uboot_configs,destination=/configs \
	uboot

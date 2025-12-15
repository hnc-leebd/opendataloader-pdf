/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.json.serializers;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;
import org.opendataloader.pdf.containers.StaticLayoutContainers;
import org.opendataloader.pdf.json.JsonName;
import org.opendataloader.pdf.json.JsonSerializationContext;
import org.verapdf.wcag.algorithms.entities.content.ImageChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.consumers.ContrastRatioConsumer;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

public class ImageSerializer extends StdSerializer<ImageChunk> {

    protected static final Logger LOGGER = Logger.getLogger(ImageSerializer.class.getCanonicalName());

    public ImageSerializer(Class<ImageChunk> t) {
        super(t);
    }

    @Override
    public void serialize(ImageChunk imageChunk, JsonGenerator jsonGenerator, SerializerProvider serializerProvider)
            throws IOException {
        jsonGenerator.writeStartObject();
        SerializerUtil.writeEssentialInfo(jsonGenerator, imageChunk, JsonName.IMAGE_CHUNK_TYPE);

        if (JsonSerializationContext.isAddImageToJson()) {
            String imagePath = extractAndSaveImage(imageChunk);
            if (imagePath != null) {
                jsonGenerator.writeStringField(JsonName.IMAGE_PATH, imagePath);
            }
        }

        jsonGenerator.writeEndObject();
    }

    private String extractAndSaveImage(ImageChunk image) {
        try {
            int currentImageIndex = StaticLayoutContainers.incrementImageIndex();
            String imageDirectoryName = JsonSerializationContext.getImageDirectoryName();

            if (currentImageIndex == 1) {
                new File(imageDirectoryName).mkdirs();
                String pdfFileName = JsonSerializationContext.getPdfFileName();
                String password = JsonSerializationContext.getPassword();
                ContrastRatioConsumer consumer = StaticLayoutContainers.getContrastRatioConsumer(
                    pdfFileName, password, false, null);
                JsonSerializationContext.setContrastRatioConsumer(consumer);
            }

            String fileName = String.format("%s%simage_%d.png",
                imageDirectoryName, File.separator, currentImageIndex);

            boolean isFileCreated = createImageFile(image, fileName);
            if (isFileCreated) {
                return fileName;
            }
            return null;
        } catch (Exception e) {
            LOGGER.log(Level.WARNING, "Unable to extract image for JSON output: " + e.getMessage());
            return null;
        }
    }

    private boolean createImageFile(ImageChunk image, String fileName) {
        try {
            BoundingBox imageBox = image.getBoundingBox();
            ContrastRatioConsumer contrastRatioConsumer = JsonSerializationContext.getContrastRatioConsumer();
            BufferedImage targetImage = contrastRatioConsumer != null ?
                contrastRatioConsumer.getPageSubImage(imageBox) : null;
            if (targetImage == null) {
                return false;
            }

            File outputFile = new File(fileName);
            ImageIO.write(targetImage, "png", outputFile);
            return true;
        } catch (IOException e) {
            LOGGER.log(Level.WARNING, "Unable to create image file: " + e.getMessage());
            return false;
        }
    }
}

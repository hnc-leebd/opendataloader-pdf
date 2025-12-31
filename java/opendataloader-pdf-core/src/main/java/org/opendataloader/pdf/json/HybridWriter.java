/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.json;

import com.fasterxml.jackson.core.JsonEncoding;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.util.DefaultPrettyPrinter;
import org.opendataloader.pdf.containers.StaticLayoutContainers;
import org.opendataloader.pdf.processors.TriageProcessor.PageTriage;
import org.verapdf.as.ASAtom;
import org.verapdf.cos.COSDictionary;
import org.verapdf.cos.COSObjType;
import org.verapdf.cos.COSObject;
import org.verapdf.cos.COSTrailer;
import org.verapdf.gf.model.impl.cos.GFCosInfo;
import org.verapdf.pd.PDDocument;
import org.verapdf.tools.StaticResources;
import org.verapdf.wcag.algorithms.entities.IObject;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.consumers.ContrastRatioConsumer;
import org.verapdf.wcag.algorithms.semanticalgorithms.containers.StaticContainers;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Writer for hybrid mode output files.
 * Produces triage.json, fast_pages.json, and page images for AI processing.
 */
public class HybridWriter {
    private static final Logger LOGGER = Logger.getLogger(HybridWriter.class.getCanonicalName());

    private static final String TRIAGE_FILE_NAME = "triage.json";
    private static final String FAST_PAGES_FILE_NAME = "fast_pages.json";
    private static final String AI_PAGES_DIR_NAME = "ai_pages";

    private static JsonGenerator createJsonGenerator(String fileName) throws IOException {
        JsonFactory jsonFactory = new JsonFactory();
        return jsonFactory.createGenerator(new File(fileName), JsonEncoding.UTF8)
                .setPrettyPrinter(new DefaultPrettyPrinter())
                .setCodec(ObjectMapperHolder.getObjectMapper());
    }

    /**
     * Writes triage.json containing page routing decisions.
     *
     * @param outputDir the output directory
     * @param triageResults list of triage results for each page
     * @throws IOException if unable to write the file
     */
    public static void writeTriageJson(File outputDir, List<PageTriage> triageResults) throws IOException {
        String fileName = outputDir.getAbsolutePath() + File.separator + TRIAGE_FILE_NAME;
        try (JsonGenerator gen = createJsonGenerator(fileName)) {
            gen.writeStartObject();
            gen.writeArrayFieldStart("pages");
            for (PageTriage triage : triageResults) {
                gen.writeStartObject();
                gen.writeNumberField("page", triage.getPageNumber() + 1); // 1-indexed for output
                gen.writeStringField("path", triage.getPath());
                if (triage.isNeedsOcr()) {
                    gen.writeBooleanField("needs_ocr", true);
                }
                if (triage.isNeedsTableAi()) {
                    gen.writeBooleanField("needs_table_ai", true);
                }
                gen.writeEndObject();
            }
            gen.writeEndArray();
            gen.writeEndObject();
            LOGGER.log(Level.INFO, "Created {0}", fileName);
        }
    }

    /**
     * Writes fast_pages.json containing extraction results for fast-path pages.
     *
     * @param outputDir the output directory
     * @param pdfName the PDF file name
     * @param fastPageContents map of page number to processed contents
     * @throws IOException if unable to write the file
     */
    public static void writeFastPagesJson(File outputDir, String pdfName,
                                          Map<Integer, List<IObject>> fastPageContents) throws IOException {
        StaticLayoutContainers.resetImageIndex();
        String fileName = outputDir.getAbsolutePath() + File.separator + FAST_PAGES_FILE_NAME;
        try (JsonGenerator gen = createJsonGenerator(fileName)) {
            gen.writeStartObject();
            writeDocumentInfo(gen, pdfName);
            gen.writeArrayFieldStart(JsonName.KIDS);
            for (int pageNumber = 0; pageNumber < StaticContainers.getDocument().getNumberOfPages(); pageNumber++) {
                if (fastPageContents.containsKey(pageNumber)) {
                    for (IObject content : fastPageContents.get(pageNumber)) {
                        gen.writePOJO(content);
                    }
                }
            }
            gen.writeEndArray();
            gen.writeEndObject();
            LOGGER.log(Level.INFO, "Created {0}", fileName);
        }
    }

    /**
     * Renders and writes page images for AI processing.
     *
     * @param outputDir the output directory
     * @param pdfPath the path to the PDF file
     * @param password the PDF password (may be null)
     * @param aiPageNumbers list of page numbers requiring AI processing (0-indexed)
     * @throws IOException if unable to render or write images
     */
    public static void writeAiPageImages(File outputDir, String pdfPath, String password,
                                         List<Integer> aiPageNumbers) throws IOException {
        if (aiPageNumbers.isEmpty()) {
            LOGGER.log(Level.INFO, "No AI pages to render");
            return;
        }

        File aiPagesDir = new File(outputDir, AI_PAGES_DIR_NAME);
        if (!aiPagesDir.exists()) {
            aiPagesDir.mkdirs();
        }

        ContrastRatioConsumer contrastRatioConsumer = null;
        try {
            contrastRatioConsumer = StaticLayoutContainers.getContrastRatioConsumer(pdfPath, password, false, null);
            if (contrastRatioConsumer == null) {
                LOGGER.log(Level.WARNING, "Unable to create page renderer");
                return;
            }

            for (int pageNumber : aiPageNumbers) {
                renderPageImage(contrastRatioConsumer, aiPagesDir, pageNumber);
            }
        } finally {
            // ContrastRatioConsumer doesn't implement Closeable, cleanup handled internally
        }
    }

    private static void renderPageImage(ContrastRatioConsumer consumer, File outputDir, int pageNumber) {
        try {
            BoundingBox pageBox = getPageBoundingBox(pageNumber);
            if (pageBox == null) {
                LOGGER.log(Level.WARNING, "Unable to get page bounding box for page {0}", pageNumber);
                return;
            }

            // Use getPageSubImage with the full page bounding box to render the entire page
            BufferedImage pageImage = consumer.getPageSubImage(pageBox);
            if (pageImage == null) {
                LOGGER.log(Level.WARNING, "Unable to render page {0}", pageNumber);
                return;
            }

            String fileName = String.format("page_%03d.png", pageNumber + 1); // 1-indexed
            File outputFile = new File(outputDir, fileName);
            ImageIO.write(pageImage, "png", outputFile);
            LOGGER.log(Level.INFO, "Created page image: {0}", outputFile.getAbsolutePath());
        } catch (IOException e) {
            LOGGER.log(Level.WARNING, "Unable to write page image for page " + pageNumber + ": " + e.getMessage());
        }
    }

    private static BoundingBox getPageBoundingBox(int pageNumber) {
        PDDocument document = StaticResources.getDocument();
        if (document == null || pageNumber >= document.getNumberOfPages()) {
            return null;
        }
        double[] pageBoundary = document.getPage(pageNumber).getCropBox();
        if (pageBoundary == null || pageBoundary.length < 4) {
            return null;
        }
        return new BoundingBox(pageNumber, pageBoundary);
    }

    private static void writeDocumentInfo(JsonGenerator generator, String pdfName) throws IOException {
        PDDocument document = StaticResources.getDocument();
        generator.writeStringField(JsonName.FILE_NAME, pdfName);
        generator.writeNumberField(JsonName.NUMBER_OF_PAGES, document.getNumberOfPages());
        COSTrailer trailer = document.getDocument().getTrailer();
        COSObject object = trailer.getKey(ASAtom.INFO);
        GFCosInfo info = new GFCosInfo((COSDictionary)
                (object != null && object.getType() == COSObjType.COS_DICT ?
                        object.getDirectBase() : COSDictionary.construct().get()));
        generator.writeStringField(JsonName.AUTHOR, info.getAuthor() != null ? info.getAuthor() : info.getXMPCreator());
        generator.writeStringField(JsonName.TITLE, info.getTitle() != null ? info.getTitle() : info.getXMPTitle());
        generator.writeStringField(JsonName.CREATION_DATE, info.getCreationDate() != null ?
                info.getCreationDate() : info.getXMPCreateDate());
        generator.writeStringField(JsonName.MODIFICATION_DATE, info.getModDate() != null ?
                info.getModDate() : info.getXMPModifyDate());
    }
}

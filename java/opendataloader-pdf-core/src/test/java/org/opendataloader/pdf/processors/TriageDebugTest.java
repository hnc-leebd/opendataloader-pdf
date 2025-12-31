/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.processors;

import org.junit.jupiter.api.Test;
import org.opendataloader.pdf.api.Config;
import org.opendataloader.pdf.processors.TriageProcessor.PageTriage;
import org.opendataloader.pdf.processors.TriageProcessor.TriageSignals;
import org.verapdf.wcag.algorithms.entities.content.IChunk;
import org.verapdf.wcag.algorithms.entities.content.LineArtChunk;
import org.verapdf.wcag.algorithms.entities.content.LineChunk;
import org.verapdf.wcag.algorithms.entities.content.TextChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.containers.StaticContainers;
import org.verapdf.wcag.algorithms.semanticalgorithms.utils.NodeUtils;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.List;

/**
 * Debug test to analyze False Negative documents.
 */
public class TriageDebugTest {

    private static final Path SAMPLES_DIR = Paths.get("../../../opendataloader-bench/pdfs");

    // False Negative documents - have tables but not detected
    private static final List<String> FALSE_NEGATIVE_DOCS = Arrays.asList(
        "01030000000110.pdf",
        "01030000000122.pdf",
        "01030000000132.pdf",
        "01030000000166.pdf",
        "01030000000182.pdf"
    );

    // Constants from TriageProcessor for reference
    private static final double Y_DIFFERENCE_EPSILON = 0.1;
    private static final double X_DIFFERENCE_EPSILON = 1.5;

    @Test
    public void analyzeFalseNegatives() throws IOException {
        if (!Files.exists(SAMPLES_DIR)) {
            System.out.println("Samples directory not found");
            return;
        }

        System.out.println("=== False Negative Document Analysis ===\n");

        for (String fileName : FALSE_NEGATIVE_DOCS) {
            Path pdfPath = SAMPLES_DIR.resolve(fileName);
            if (!Files.exists(pdfPath)) {
                System.out.println("File not found: " + fileName);
                continue;
            }

            analyzeDocument(pdfPath.toFile(), fileName);
        }
    }

    private void analyzeDocument(File pdfFile, String fileName) throws IOException {
        System.out.println("=== " + fileName + " ===");

        Config config = new Config();
        DocumentProcessor.preprocessing(pdfFile.getAbsolutePath(), config);

        int numberOfPages = StaticContainers.getDocument().getNumberOfPages();
        System.out.println("Total pages: " + numberOfPages);

        for (int pageNumber = 0; pageNumber < numberOfPages; pageNumber++) {
            List<IChunk> rawContents = StaticContainers.getDocument().getArtifacts(pageNumber);
            BoundingBox pageBoundingBox = DocumentProcessor.getPageBoundingBox(pageNumber);

            // Get triage result
            PageTriage triage = TriageProcessor.triagePage(pageNumber, rawContents, pageBoundingBox);
            TriageSignals signals = triage.getSignals();

            // Count text chunks and analyze patterns
            int textChunkCount = 0;
            int tablePatternCount = 0;
            int yReversalCount = 0;
            int horizontalGapCount = 0;
            int maxConsecutiveStreak = 0;
            int currentStreak = 0;
            TextChunk previousTextChunk = null;
            int horizontalLineCount = 0;
            int verticalLineCount = 0;
            int lineArtCount = 0;
            int rowSeparatorPatternCount = 0;
            boolean lastWasHorizontalLine = false;
            double pageWidth = pageBoundingBox.getRightX() - pageBoundingBox.getLeftX();
            java.util.List<double[]> shortLines = new java.util.ArrayList<>(); // [leftX, width]

            for (IChunk chunk : rawContents) {
                if (chunk instanceof LineChunk) {
                    BoundingBox box = chunk.getBoundingBox();
                    double width = box.getRightX() - box.getLeftX();
                    double height = box.getTopY() - box.getBottomY();
                    if (width > height * 3) {
                        horizontalLineCount++;
                        if (!lastWasHorizontalLine) {
                            rowSeparatorPatternCount++;
                        }
                        // Track short lines (< 50% page width)
                        if (pageWidth > 0 && width < pageWidth * 0.5) {
                            shortLines.add(new double[]{box.getLeftX(), width});
                        }
                        lastWasHorizontalLine = true;
                    } else if (height > width * 3) {
                        verticalLineCount++;
                    }
                } else if (chunk instanceof LineArtChunk) {
                    lineArtCount++;
                } else if (chunk instanceof TextChunk) {
                    lastWasHorizontalLine = false;
                    TextChunk current = (TextChunk) chunk;
                    if (!current.isWhiteSpaceChunk()) {
                        textChunkCount++;

                        if (previousTextChunk != null) {
                            boolean isSuspicious = false;
                            String patternType = "";

                            // Y-reversal check
                            if (previousTextChunk.getTopY() < current.getBottomY()) {
                                yReversalCount++;
                                isSuspicious = true;
                                patternType = "Y-reversal";
                            }
                            // Horizontal gap check
                            else if (NodeUtils.areCloseNumbers(previousTextChunk.getBaseLine(), current.getBaseLine(),
                                    current.getHeight() * Y_DIFFERENCE_EPSILON)) {
                                double gap = current.getLeftX() - previousTextChunk.getRightX();
                                if (gap > current.getHeight() * X_DIFFERENCE_EPSILON) {
                                    horizontalGapCount++;
                                    isSuspicious = true;
                                    patternType = "H-gap(" + String.format("%.1f", gap) + ")";
                                }
                            }

                            if (isSuspicious) {
                                tablePatternCount++;
                                currentStreak++;
                                if (currentStreak > maxConsecutiveStreak) {
                                    maxConsecutiveStreak = currentStreak;
                                }
                            } else {
                                currentStreak = 0;
                            }
                        }
                        previousTextChunk = current;
                    }
                }
            }

            double patternDensity = textChunkCount > 0 ? (double) tablePatternCount / textChunkCount : 0;

            System.out.println("\nPage " + pageNumber + ":");
            System.out.println("  Text chunks: " + textChunkCount);
            System.out.println("  Table patterns: " + tablePatternCount);
            System.out.println("    - Y-reversal: " + yReversalCount);
            System.out.println("    - Horizontal gap: " + horizontalGapCount);
            System.out.println("  Max consecutive streak: " + maxConsecutiveStreak);
            System.out.println("  Pattern density: " + String.format("%.4f", patternDensity));
            System.out.println("  Detected as table: " + triage.isNeedsTableAi());
            System.out.println("  Signals: gridAligned=" + signals.isHasGridAlignedText() +
                             ", suspiciousGaps=" + signals.isHasSuspiciousTextGaps());
            System.out.println("  Vector graphics:");
            System.out.println("    - Horizontal lines: " + horizontalLineCount);
            System.out.println("    - Vertical lines: " + verticalLineCount);
            System.out.println("    - LineArt chunks: " + lineArtCount);
            System.out.println("    - Row separator patterns: " + rowSeparatorPatternCount);
            System.out.println("    - Short lines (leftX, width): ");
            for (double[] line : shortLines) {
                System.out.println("        [" + String.format("%.1f", line[0]) + ", " + String.format("%.1f", line[1]) + "]");
            }
        }
        System.out.println();
    }
}

/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.processors;

import org.opendataloader.pdf.api.Config;
import org.verapdf.wcag.algorithms.entities.IObject;
import org.verapdf.wcag.algorithms.entities.content.IChunk;
import org.verapdf.wcag.algorithms.entities.content.ImageChunk;
import org.verapdf.wcag.algorithms.entities.content.TextChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;

import java.util.List;

/**
 * Processor for triaging PDF pages to determine processing path.
 * Analyzes page content to decide between fast (heuristic) and AI processing.
 */
public class TriageProcessor {

    /** Processing path: use fast heuristic extraction. */
    public static final String PATH_FAST = "fast";
    /** Processing path: use AI-based processing. */
    public static final String PATH_AI = "ai";

    /**
     * Result of page triage analysis.
     */
    public static class PageTriage {
        private final int pageNumber;
        private final String path;
        private final boolean needsOcr;
        private final boolean needsTableAi;
        private final TriageSignals signals;

        public PageTriage(int pageNumber, String path, boolean needsOcr, boolean needsTableAi, TriageSignals signals) {
            this.pageNumber = pageNumber;
            this.path = path;
            this.needsOcr = needsOcr;
            this.needsTableAi = needsTableAi;
            this.signals = signals;
        }

        public int getPageNumber() {
            return pageNumber;
        }

        public String getPath() {
            return path;
        }

        public boolean isNeedsOcr() {
            return needsOcr;
        }

        public boolean isNeedsTableAi() {
            return needsTableAi;
        }

        public TriageSignals getSignals() {
            return signals;
        }
    }

    /**
     * Signals analyzed from page content for triage decision.
     */
    public static class TriageSignals {
        private final double imageAreaRatio;
        private final double textCoverage;
        private final double missingToUnicodeRatio;
        private final boolean hasType3Fonts;
        private final boolean hasGridAlignedText;
        private final boolean hasSuspiciousTextGaps;

        public TriageSignals(double imageAreaRatio, double textCoverage, double missingToUnicodeRatio,
                             boolean hasType3Fonts, boolean hasGridAlignedText, boolean hasSuspiciousTextGaps) {
            this.imageAreaRatio = imageAreaRatio;
            this.textCoverage = textCoverage;
            this.missingToUnicodeRatio = missingToUnicodeRatio;
            this.hasType3Fonts = hasType3Fonts;
            this.hasGridAlignedText = hasGridAlignedText;
            this.hasSuspiciousTextGaps = hasSuspiciousTextGaps;
        }

        public double getImageAreaRatio() {
            return imageAreaRatio;
        }

        public double getTextCoverage() {
            return textCoverage;
        }

        public double getMissingToUnicodeRatio() {
            return missingToUnicodeRatio;
        }

        public boolean isHasType3Fonts() {
            return hasType3Fonts;
        }

        public boolean isHasGridAlignedText() {
            return hasGridAlignedText;
        }

        public boolean isHasSuspiciousTextGaps() {
            return hasSuspiciousTextGaps;
        }
    }

    /**
     * Performs triage on a page to determine processing path.
     *
     * @param pageNumber the page number (0-indexed)
     * @param contents the raw page contents
     * @param pageBoundingBox the page bounding box
     * @param config the configuration settings
     * @return the triage result indicating processing path and requirements
     */
    public static PageTriage triagePage(int pageNumber, List<IChunk> contents,
                                        BoundingBox pageBoundingBox, Config config) {
        TriageSignals signals = analyzePageSignals(contents, pageBoundingBox);

        boolean needsOcr = checkNeedsOcr(signals, config);
        boolean needsTableAi = checkNeedsTableAi(signals);

        String path = (needsOcr || needsTableAi) ? PATH_AI : PATH_FAST;

        return new PageTriage(pageNumber, path, needsOcr, needsTableAi, signals);
    }

    /**
     * Analyzes page contents to extract triage signals.
     *
     * @param contents the raw page contents
     * @param pageBoundingBox the page bounding box
     * @return the analyzed signals
     */
    static TriageSignals analyzePageSignals(List<IChunk> contents, BoundingBox pageBoundingBox) {
        double pageArea = calculateBoundingBoxArea(pageBoundingBox);
        if (pageArea <= 0) {
            return new TriageSignals(0, 0, 0, false, false, false);
        }

        double totalImageArea = 0;
        double totalTextArea = 0;
        int totalFonts = 0;
        int fontsWithoutToUnicode = 0;
        boolean hasType3Fonts = false;
        boolean hasGridAlignedText = false;
        boolean hasSuspiciousTextGaps = false;

        TextChunk previousTextChunk = null;

        for (IChunk chunk : contents) {
            if (chunk instanceof ImageChunk) {
                ImageChunk image = (ImageChunk) chunk;
                totalImageArea += calculateBoundingBoxArea(image.getBoundingBox());
            } else if (chunk instanceof TextChunk) {
                TextChunk textChunk = (TextChunk) chunk;
                totalTextArea += calculateBoundingBoxArea(textChunk.getBoundingBox());

                // Check font properties
                if (textChunk.getFontName() != null) {
                    totalFonts++;
                    // Check for Type3 font (font name often contains "Type3")
                    if (textChunk.getFontName().contains("Type3")) {
                        hasType3Fonts = true;
                    }
                    // ToUnicode mapping check - fonts without proper mapping often have
                    // replacement characters or unmapped glyphs
                    if (hasUnmappedCharacters(textChunk.getValue())) {
                        fontsWithoutToUnicode++;
                    }
                }

                // Check for suspicious text gaps (table detection signal)
                if (previousTextChunk != null) {
                    if (detectSuspiciousTextGap(previousTextChunk, textChunk)) {
                        hasSuspiciousTextGaps = true;
                    }
                    if (detectGridAlignment(previousTextChunk, textChunk)) {
                        hasGridAlignedText = true;
                    }
                }
                previousTextChunk = textChunk;
            }
        }

        double imageAreaRatio = totalImageArea / pageArea;
        double textCoverage = totalTextArea / pageArea;
        double missingToUnicodeRatio = totalFonts > 0 ? (double) fontsWithoutToUnicode / totalFonts : 0;

        return new TriageSignals(imageAreaRatio, textCoverage, missingToUnicodeRatio,
                hasType3Fonts, hasGridAlignedText, hasSuspiciousTextGaps);
    }

    /**
     * Checks if page needs OCR processing based on signals and thresholds.
     */
    private static boolean checkNeedsOcr(TriageSignals signals, Config config) {
        // High image area suggests scanned content
        if (signals.getImageAreaRatio() > config.getImageAreaThreshold()) {
            return true;
        }
        // Low text coverage suggests image-based content
        if (signals.getTextCoverage() < config.getTextCoverageThreshold()) {
            return true;
        }
        // Many fonts without ToUnicode mapping
        if (signals.getMissingToUnicodeRatio() > config.getMissingToUnicodeThreshold()) {
            return true;
        }
        // Type3 fonts are image-based glyphs
        if (signals.isHasType3Fonts()) {
            return true;
        }
        return false;
    }

    /**
     * Checks if page needs AI-based table detection.
     */
    private static boolean checkNeedsTableAi(TriageSignals signals) {
        // Grid-aligned text with suspicious gaps suggests borderless table
        return signals.isHasGridAlignedText() && signals.isHasSuspiciousTextGaps();
    }

    /**
     * Calculates the area of a bounding box.
     */
    private static double calculateBoundingBoxArea(BoundingBox box) {
        if (box == null) {
            return 0;
        }
        double width = box.getRightX() - box.getLeftX();
        double height = box.getTopY() - box.getBottomY();
        return Math.max(0, width * height);
    }

    /**
     * Checks if text contains unmapped/replacement characters.
     * These indicate fonts without proper ToUnicode mapping.
     */
    private static boolean hasUnmappedCharacters(String text) {
        if (text == null || text.isEmpty()) {
            return false;
        }
        for (char c : text.toCharArray()) {
            // Unicode replacement character
            if (c == '\uFFFD') {
                return true;
            }
            // Private Use Area (often used for unmapped glyphs)
            if (c >= '\uE000' && c <= '\uF8FF') {
                return true;
            }
        }
        return false;
    }

    /**
     * Detects suspicious text gaps that may indicate table structure.
     * Large horizontal gaps on the same baseline suggest table cell boundaries.
     */
    private static boolean detectSuspiciousTextGap(TextChunk previous, TextChunk current) {
        if (previous == null || current == null) {
            return false;
        }
        BoundingBox prevBox = previous.getBoundingBox();
        BoundingBox currBox = current.getBoundingBox();
        if (prevBox == null || currBox == null) {
            return false;
        }

        // Check if on same baseline (within tolerance)
        double baselineTolerance = previous.getFontSize() * 0.3;
        boolean sameBaseline = Math.abs(prevBox.getBottomY() - currBox.getBottomY()) < baselineTolerance;

        if (sameBaseline) {
            // Check for large horizontal gap (more than 3x character height)
            double xGap = currBox.getLeftX() - prevBox.getRightX();
            double charHeight = previous.getFontSize();
            if (charHeight > 0 && xGap > charHeight * 3) {
                return true;
            }
        }
        return false;
    }

    /**
     * Detects grid-aligned text patterns.
     * Text going backwards (multi-column layout) or aligned columns suggest tables.
     */
    private static boolean detectGridAlignment(TextChunk previous, TextChunk current) {
        if (previous == null || current == null) {
            return false;
        }
        BoundingBox prevBox = previous.getBoundingBox();
        BoundingBox currBox = current.getBoundingBox();
        if (prevBox == null || currBox == null) {
            return false;
        }

        // Text going backwards suggests multi-column layout
        if (prevBox.getTopY() < currBox.getBottomY()) {
            return true;
        }
        return false;
    }
}

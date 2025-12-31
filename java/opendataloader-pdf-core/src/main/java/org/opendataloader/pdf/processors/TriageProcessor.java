/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.processors;

import org.verapdf.wcag.algorithms.entities.content.IChunk;
import org.verapdf.wcag.algorithms.entities.content.ImageChunk;
import org.verapdf.wcag.algorithms.entities.content.LineArtChunk;
import org.verapdf.wcag.algorithms.entities.content.LineChunk;
import org.verapdf.wcag.algorithms.entities.content.TextChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.utils.NodeUtils;

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

    // Constants matching AbstractTableProcessor for table detection
    private static final double Y_DIFFERENCE_EPSILON = 0.1;
    private static final double X_DIFFERENCE_EPSILON = 1.5;

    // Minimum number of suspicious patterns required to flag as table
    // Reduces false positives from simple multi-column layouts or indented text
    private static final int MIN_TABLE_PATTERNS = 3;

    // Pattern density threshold (patterns / text chunks)
    // High density with fewer absolute patterns can still indicate a table
    private static final double MIN_PATTERN_DENSITY = 0.10;
    private static final int MIN_PATTERNS_FOR_DENSITY = 2;

    // Multi-column layout filter: X shift ratio to detect column change
    // If X moves left by more than this ratio of text width, it's likely a new column
    private static final double MULTI_COLUMN_X_SHIFT_RATIO = 2.0;

    // Consecutive pattern validation: require patterns to occur in sequence
    // Isolated patterns are likely not tables
    private static final int MIN_CONSECUTIVE_PATTERNS = 2;

    // High pattern count threshold: if pattern count exceeds this,
    // skip consecutive pattern check (handles complex tables with scattered patterns)
    private static final int HIGH_PATTERN_COUNT_THRESHOLD = 30;

    // Vector graphics thresholds for table border detection
    // Minimum number of line segments to suggest table borders
    private static final int MIN_LINE_COUNT_FOR_TABLE = 8;
    // Minimum number of horizontal + vertical line pairs for grid pattern
    // Having both H and V lines is a strong indicator, so threshold is lower
    private static final int MIN_GRID_LINES = 3;

    // Row separator pattern: horizontal lines alternating with text
    // Minimum number of line-text-line alternations to detect row separator pattern
    private static final int MIN_ROW_SEPARATOR_PATTERN = 5;

    // Aligned short horizontal lines pattern: short lines (< 50% page width) with same length
    // vertically aligned suggest table row separators
    private static final double SHORT_LINE_MAX_WIDTH_RATIO = 0.5;
    private static final double LINE_LENGTH_TOLERANCE = 0.05; // 5% tolerance for "same length"
    private static final int MIN_ALIGNED_SHORT_LINES = 2; // need 2+ lines with same X and length

    private TriageProcessor() {
        // Utility class
    }

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
        private final boolean hasImage;
        private final boolean hasText;

        public TriageSignals(double imageAreaRatio, double textCoverage, double missingToUnicodeRatio,
                             boolean hasType3Fonts, boolean hasGridAlignedText, boolean hasSuspiciousTextGaps,
                             boolean hasImage, boolean hasText) {
            this.imageAreaRatio = imageAreaRatio;
            this.textCoverage = textCoverage;
            this.missingToUnicodeRatio = missingToUnicodeRatio;
            this.hasType3Fonts = hasType3Fonts;
            this.hasGridAlignedText = hasGridAlignedText;
            this.hasSuspiciousTextGaps = hasSuspiciousTextGaps;
            this.hasImage = hasImage;
            this.hasText = hasText;
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

        public boolean isHasImage() {
            return hasImage;
        }

        public boolean isHasText() {
            return hasText;
        }
    }

    /**
     * Performs triage on a page to determine processing path.
     *
     * @param pageNumber the page number (0-indexed)
     * @param contents the raw page contents
     * @param pageBoundingBox the page bounding box
     * @return the triage result indicating processing path and requirements
     */
    public static PageTriage triagePage(int pageNumber, List<IChunk> contents,
                                        BoundingBox pageBoundingBox) {
        TriageSignals signals = analyzePageSignals(contents, pageBoundingBox);

        boolean needsOcr = checkNeedsOcr(signals);
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
            return new TriageSignals(0, 0, 0, false, false, false, false, false);
        }

        double pageWidth = pageBoundingBox.getRightX() - pageBoundingBox.getLeftX();
        SignalAccumulator accumulator = new SignalAccumulator(pageWidth);

        for (IChunk chunk : contents) {
            if (chunk instanceof ImageChunk) {
                accumulator.addImageArea(calculateBoundingBoxArea(chunk.getBoundingBox()));
            } else if (chunk instanceof TextChunk) {
                accumulator.processTextChunk((TextChunk) chunk);
            } else if (chunk instanceof LineChunk) {
                accumulator.processLineChunk((LineChunk) chunk);
            } else if (chunk instanceof LineArtChunk) {
                accumulator.processLineArtChunk();
            }
        }

        return accumulator.buildSignals(pageArea);
    }

    /**
     * Helper class to accumulate signals during page analysis.
     */
    private static class SignalAccumulator {
        private final double pageWidth;
        private double totalImageArea = 0;
        private double totalTextArea = 0;
        private int totalFonts = 0;
        private int fontsWithoutToUnicode = 0;
        private boolean hasType3Fonts = false;
        private int tablePatternCount = 0;
        private int currentConsecutiveStreak = 0;
        private int maxConsecutiveStreak = 0;
        private int textChunkCount = 0;
        private boolean hasImage = false;
        private boolean hasText = false;
        private TextChunk previousTextChunk = null;
        private int horizontalLineCount = 0;
        private int verticalLineCount = 0;
        private int lineArtCount = 0;
        // Row separator pattern tracking: line-text-line alternation
        private boolean lastWasHorizontalLine = false;
        private int rowSeparatorPatternCount = 0;
        // Aligned short horizontal lines tracking: stores (leftX, width) pairs
        private java.util.List<double[]> shortHorizontalLines = new java.util.ArrayList<>();

        SignalAccumulator(double pageWidth) {
            this.pageWidth = pageWidth;
        }

        void addImageArea(double area) {
            totalImageArea += area;
            hasImage = true;
        }

        void processLineChunk(LineChunk lineChunk) {
            BoundingBox box = lineChunk.getBoundingBox();
            double width = box.getRightX() - box.getLeftX();
            double height = box.getTopY() - box.getBottomY();
            // Horizontal line: width >> height
            if (width > height * 3) {
                horizontalLineCount++;
                // Track row separator pattern: if we see a horizontal line after text,
                // it could be a row separator
                if (!lastWasHorizontalLine) {
                    // Text was between this line and the previous line
                    rowSeparatorPatternCount++;
                }
                // Track short horizontal lines (< 50% page width) for aligned pattern detection
                if (pageWidth > 0 && width < pageWidth * SHORT_LINE_MAX_WIDTH_RATIO) {
                    shortHorizontalLines.add(new double[]{box.getLeftX(), width});
                }
                lastWasHorizontalLine = true;
            }
            // Vertical line: height >> width
            else if (height > width * 3) {
                verticalLineCount++;
            }
        }

        void processLineArtChunk() {
            lineArtCount++;
        }

        void processTextChunk(TextChunk textChunk) {
            totalTextArea += calculateBoundingBoxArea(textChunk.getBoundingBox());
            hasText = true;
            checkFontProperties(textChunk);
            checkTablePattern(textChunk);
            // Mark that we've seen text (for row separator pattern detection)
            lastWasHorizontalLine = false;
        }

        private void checkFontProperties(TextChunk textChunk) {
            if (textChunk.getFontName() == null) {
                return;
            }
            totalFonts++;
            if (textChunk.getFontName().contains("Type3")) {
                hasType3Fonts = true;
            }
            if (hasUnmappedCharacters(textChunk.getValue())) {
                fontsWithoutToUnicode++;
            }
        }

        /**
         * Checks if text contains unmapped/replacement characters.
         * These indicate fonts without proper ToUnicode mapping.
         */
        private boolean hasUnmappedCharacters(String text) {
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

        private void checkTablePattern(TextChunk current) {
            if (current.isWhiteSpaceChunk()) {
                return;
            }
            textChunkCount++;
            if (previousTextChunk != null && areSuspiciousTextChunks(previousTextChunk, current)) {
                tablePatternCount++;
                currentConsecutiveStreak++;
                if (currentConsecutiveStreak > maxConsecutiveStreak) {
                    maxConsecutiveStreak = currentConsecutiveStreak;
                }
            } else {
                currentConsecutiveStreak = 0;
            }
            previousTextChunk = current;
        }

        /**
         * Detects suspicious text chunks that may indicate table structure.
         * Uses the same logic as AbstractTableProcessor.areSuspiciousTextChunks().
         */
        private boolean areSuspiciousTextChunks(TextChunk previous, TextChunk current) {
            // Text going backwards suggests multi-column layout or table
            if (previous.getTopY() < current.getBottomY()) {
                // Filter out multi-column layout: X moves significantly left
                double xShift = previous.getLeftX() - current.getLeftX();
                double textWidth = previous.getRightX() - previous.getLeftX();
                if (textWidth > 0 && xShift > textWidth * MULTI_COLUMN_X_SHIFT_RATIO) {
                    // Large leftward shift indicates new column, not table
                    return false;
                }
                return true;
            }
            // Same baseline with large horizontal gap suggests table cell boundaries
            if (NodeUtils.areCloseNumbers(previous.getBaseLine(), current.getBaseLine(),
                    current.getHeight() * Y_DIFFERENCE_EPSILON)) {
                return current.getLeftX() - previous.getRightX() > current.getHeight() * X_DIFFERENCE_EPSILON;
            }
            return false;
        }

        /**
         * Checks if there are aligned short horizontal lines with same length and same X position.
         * Short lines (< 50% page width) with matching leftX and width suggest table row separators.
         * Requires MIN_ALIGNED_SHORT_LINES lines with the same position and length.
         */
        private boolean hasAlignedShortHorizontalLines() {
            if (shortHorizontalLines.size() < MIN_ALIGNED_SHORT_LINES) {
                return false;
            }
            // Count lines with same leftX and length (within tolerance)
            for (int i = 0; i < shortHorizontalLines.size(); i++) {
                double[] refLine = shortHorizontalLines.get(i);
                double refLeftX = refLine[0];
                double refLen = refLine[1];
                int matchCount = 1; // count the reference line itself
                for (int j = i + 1; j < shortHorizontalLines.size(); j++) {
                    double[] line = shortHorizontalLines.get(j);
                    double leftX = line[0];
                    double len = line[1];
                    // Check both leftX and length match within tolerance
                    double xDiff = Math.abs(refLeftX - leftX);
                    double lenDiff = Math.abs(refLen - len);
                    double maxLen = Math.max(refLen, len);
                    boolean xMatches = maxLen > 0 && xDiff / maxLen <= LINE_LENGTH_TOLERANCE;
                    boolean lenMatches = maxLen > 0 && lenDiff / maxLen <= LINE_LENGTH_TOLERANCE;
                    if (xMatches && lenMatches) {
                        matchCount++;
                        if (matchCount >= MIN_ALIGNED_SHORT_LINES) {
                            return true;
                        }
                    }
                }
            }
            return false;
        }

        TriageSignals buildSignals(double pageArea) {
            double imageAreaRatio = totalImageArea / pageArea;
            double textCoverage = totalTextArea / pageArea;
            double missingToUnicodeRatio = totalFonts > 0 ? (double) fontsWithoutToUnicode / totalFonts : 0;

            // Calculate pattern density (patterns per text chunk)
            double patternDensity = textChunkCount > 0
                    ? (double) tablePatternCount / textChunkCount
                    : 0;

            // Vector graphics based table detection
            // Grid pattern: both horizontal and vertical lines present
            boolean hasGridLines = horizontalLineCount >= MIN_GRID_LINES && verticalLineCount >= MIN_GRID_LINES;
            // Sufficient line segments for table borders
            boolean hasTableBorderLines = (horizontalLineCount + verticalLineCount) >= MIN_LINE_COUNT_FOR_TABLE;
            // LineArt (rectangles, paths) can also indicate table structure
            boolean hasSignificantLineArt = lineArtCount >= MIN_LINE_COUNT_FOR_TABLE;
            // Row separator pattern: horizontal lines alternating with text (line-text-line-text-line)
            boolean hasRowSeparatorPattern = rowSeparatorPatternCount >= MIN_ROW_SEPARATOR_PATTERN;
            // Aligned short horizontal lines: short lines (< 50% page width) with same length
            boolean hasAlignedShortLines = hasAlignedShortHorizontalLines();

            // Table detection requires:
            // 1. At least MIN_CONSECUTIVE_PATTERNS consecutive patterns (filters isolated patterns)
            //    OR high pattern count (handles complex tables with scattered patterns)
            //    OR vector graphics indicating table borders
            // 2. Either absolute count OR high density with minimum patterns OR vector graphics
            boolean hasConsecutivePatterns = maxConsecutiveStreak >= MIN_CONSECUTIVE_PATTERNS;
            boolean hasHighPatternCount = tablePatternCount >= HIGH_PATTERN_COUNT_THRESHOLD;
            boolean hasVectorTableBorders = hasGridLines || hasTableBorderLines || hasSignificantLineArt
                    || hasRowSeparatorPattern || hasAlignedShortLines;

            boolean hasTablePattern = hasVectorTableBorders
                    || ((hasConsecutivePatterns || hasHighPatternCount)
                        && (tablePatternCount >= MIN_TABLE_PATTERNS
                            || (patternDensity >= MIN_PATTERN_DENSITY && tablePatternCount >= MIN_PATTERNS_FOR_DENSITY)));

            return new TriageSignals(imageAreaRatio, textCoverage, missingToUnicodeRatio,
                    hasType3Fonts, hasTablePattern, hasTablePattern, hasImage, hasText);
        }
    }

    /**
     * Checks if page needs OCR processing.
     * Only returns true when page contains images but no text chunks.
     * Same logic as OCRProcessor.isPossibleScannedPage().
     */
    private static boolean checkNeedsOcr(TriageSignals signals) {
        // Page has images but no text at all - pure image page needs OCR
        return signals.isHasImage() && !signals.isHasText();
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
}

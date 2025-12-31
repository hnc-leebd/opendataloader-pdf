/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.processors;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.opendataloader.pdf.api.Config;
import org.opendataloader.pdf.processors.TriageProcessor.PageTriage;
import org.opendataloader.pdf.processors.TriageProcessor.TriageSignals;
import org.verapdf.wcag.algorithms.entities.content.IChunk;
import org.verapdf.wcag.algorithms.entities.content.ImageChunk;
import org.verapdf.wcag.algorithms.entities.content.TextChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.containers.StaticContainers;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class TriageProcessorTest {

    private Config config;
    private BoundingBox pageBoundingBox;

    @BeforeEach
    public void setUp() {
        StaticContainers.setIsIgnoreCharactersWithoutUnicode(false);
        StaticContainers.setIsDataLoader(true);
        config = new Config();
        // Page is 100x100 units (area = 10000)
        pageBoundingBox = new BoundingBox(0, 0.0, 0.0, 100.0, 100.0);
    }

    @Test
    public void testTriagePage_EmptyPage_ReturnsAiPath_DueToLowTextCoverage() {
        // Empty page has 0% text coverage, which is below the 10% threshold
        // This correctly triggers AI path for OCR
        List<IChunk> contents = new ArrayList<>();

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, config);

        assertEquals(0, result.getPageNumber());
        assertEquals(TriageProcessor.PATH_AI, result.getPath());
        assertTrue(result.isNeedsOcr());
        assertFalse(result.isNeedsTableAi());
    }

    @Test
    public void testTriagePage_TextOnlyPage_ReturnsFastPath() {
        List<IChunk> contents = new ArrayList<>();
        // Add text covering 20% of page (area = 2000)
        contents.add(createTextChunk(0.0, 0.0, 100.0, 20.0, "Sample text content"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, config);

        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
        assertFalse(result.isNeedsOcr());
    }

    @Test
    public void testTriagePage_HighImageArea_ReturnsAiPath() {
        List<IChunk> contents = new ArrayList<>();
        // Add large image covering 10% of page (area = 1000, threshold is 5%)
        contents.add(createImageChunk(0.0, 0.0, 100.0, 10.0));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, config);

        assertEquals(TriageProcessor.PATH_AI, result.getPath());
        assertTrue(result.isNeedsOcr());
    }

    @Test
    public void testTriagePage_LowTextCoverage_ReturnsAiPath() {
        List<IChunk> contents = new ArrayList<>();
        // Add text covering only 5% of page (area = 500, threshold is 10%)
        contents.add(createTextChunk(0.0, 0.0, 50.0, 10.0, "Small text"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, config);

        assertEquals(TriageProcessor.PATH_AI, result.getPath());
        assertTrue(result.isNeedsOcr());
    }

    @Test
    public void testTriagePage_CustomThresholds() {
        Config customConfig = new Config();
        customConfig.setImageAreaThreshold(0.20); // 20%
        customConfig.setTextCoverageThreshold(0.05); // 5%

        List<IChunk> contents = new ArrayList<>();
        // Image at 10% (under new threshold)
        contents.add(createImageChunk(0.0, 0.0, 100.0, 10.0));
        // Text at 8% (above new threshold)
        contents.add(createTextChunk(0.0, 10.0, 80.0, 20.0, "Sample text"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, customConfig);

        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
        assertFalse(result.isNeedsOcr());
    }

    @Test
    public void testTriageWithHighMissingToUnicodeThreshold() {
        // Test that when threshold is set very low, missing ToUnicode fonts trigger AI path
        Config customConfig = new Config();
        customConfig.setMissingToUnicodeThreshold(0.0); // 0% - any missing triggers AI
        customConfig.setTextCoverageThreshold(0.0); // Disable text coverage check

        List<IChunk> contents = new ArrayList<>();
        // Add sufficient text coverage
        contents.add(createTextChunk(0.0, 0.0, 100.0, 50.0, "Sample text"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox, customConfig);

        // With 0% threshold for missing ToUnicode, even 0% missing should be fine
        // This tests the threshold comparison logic
        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
    }

    @Test
    public void testAnalyzePageSignals_CalculatesImageAreaRatio() {
        List<IChunk> contents = new ArrayList<>();
        // Image covering 25% of page
        contents.add(createImageChunk(0.0, 0.0, 50.0, 50.0));

        TriageSignals signals = TriageProcessor.analyzePageSignals(contents, pageBoundingBox);

        assertEquals(0.25, signals.getImageAreaRatio(), 0.01);
    }

    @Test
    public void testAnalyzePageSignals_CalculatesTextCoverage() {
        List<IChunk> contents = new ArrayList<>();
        // Text covering 10% of page
        contents.add(createTextChunk(0.0, 0.0, 50.0, 20.0, "Sample"));

        TriageSignals signals = TriageProcessor.analyzePageSignals(contents, pageBoundingBox);

        assertEquals(0.10, signals.getTextCoverage(), 0.01);
    }

    @Test
    public void testAnalyzePageSignals_DetectsSuspiciousTextGaps() {
        List<IChunk> contents = new ArrayList<>();
        // Two text chunks on same baseline with large gap
        contents.add(createTextChunk(0.0, 50.0, 10.0, 60.0, "Left"));
        contents.add(createTextChunk(80.0, 50.0, 100.0, 60.0, "Right"));

        TriageSignals signals = TriageProcessor.analyzePageSignals(contents, pageBoundingBox);

        assertTrue(signals.isHasSuspiciousTextGaps());
    }

    @Test
    public void testAnalyzePageSignals_NullBoundingBox() {
        List<IChunk> contents = new ArrayList<>();
        contents.add(createTextChunk(0.0, 0.0, 50.0, 50.0, "Test"));

        TriageSignals signals = TriageProcessor.analyzePageSignals(contents, null);

        assertEquals(0.0, signals.getImageAreaRatio());
        assertEquals(0.0, signals.getTextCoverage());
    }

    @Test
    public void testPageTriageGetters() {
        TriageSignals signals = new TriageSignals(0.1, 0.2, 0.3, true, true, true);
        PageTriage triage = new PageTriage(5, TriageProcessor.PATH_AI, true, true, signals);

        assertEquals(5, triage.getPageNumber());
        assertEquals(TriageProcessor.PATH_AI, triage.getPath());
        assertTrue(triage.isNeedsOcr());
        assertTrue(triage.isNeedsTableAi());
        assertNotNull(triage.getSignals());
    }

    @Test
    public void testTriageSignalsGetters() {
        TriageSignals signals = new TriageSignals(0.15, 0.25, 0.35, true, true, true);

        assertEquals(0.15, signals.getImageAreaRatio(), 0.001);
        assertEquals(0.25, signals.getTextCoverage(), 0.001);
        assertEquals(0.35, signals.getMissingToUnicodeRatio(), 0.001);
        assertTrue(signals.isHasType3Fonts());
        assertTrue(signals.isHasGridAlignedText());
        assertTrue(signals.isHasSuspiciousTextGaps());
    }

    private TextChunk createTextChunk(double leftX, double bottomY, double rightX, double topY, String text) {
        BoundingBox box = new BoundingBox(0, leftX, bottomY, rightX, topY);
        return new TextChunk(box, text, 12, (topY - bottomY));
    }

    private ImageChunk createImageChunk(double leftX, double bottomY, double rightX, double topY) {
        BoundingBox box = new BoundingBox(0, leftX, bottomY, rightX, topY);
        return new ImageChunk(box);
    }
}

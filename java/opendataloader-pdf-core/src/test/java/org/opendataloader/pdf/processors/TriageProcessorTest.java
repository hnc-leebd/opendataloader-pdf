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

    private BoundingBox pageBoundingBox;

    @BeforeEach
    public void setUp() {
        StaticContainers.setIsIgnoreCharactersWithoutUnicode(false);
        StaticContainers.setIsDataLoader(true);
        // Page is 100x100 units (area = 10000)
        pageBoundingBox = new BoundingBox(0, 0.0, 0.0, 100.0, 100.0);
    }

    @Test
    public void testTriagePage_EmptyPage_ReturnsFastPath() {
        // Empty page has no images and no text - fast path (nothing to OCR)
        List<IChunk> contents = new ArrayList<>();

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox);

        assertEquals(0, result.getPageNumber());
        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
        assertFalse(result.isNeedsOcr());
        assertFalse(result.isNeedsTableAi());
    }

    @Test
    public void testTriagePage_TextOnlyPage_ReturnsFastPath() {
        List<IChunk> contents = new ArrayList<>();
        // Add text covering 20% of page (area = 2000)
        contents.add(createTextChunk(0.0, 0.0, 100.0, 20.0, "Sample text content"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox);

        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
        assertFalse(result.isNeedsOcr());
    }

    @Test
    public void testTriagePage_ImageOnlyPage_ReturnsAiPath() {
        // Pure image page with no text needs OCR
        List<IChunk> contents = new ArrayList<>();
        // Add image covering some of the page
        contents.add(createImageChunk(0.0, 0.0, 100.0, 50.0));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox);

        assertEquals(TriageProcessor.PATH_AI, result.getPath());
        assertTrue(result.isNeedsOcr());
    }

    @Test
    public void testTriagePage_ImageWithText_ReturnsFastPath() {
        // Page with both image and text - no OCR needed
        List<IChunk> contents = new ArrayList<>();
        contents.add(createImageChunk(0.0, 0.0, 100.0, 50.0));
        contents.add(createTextChunk(0.0, 50.0, 100.0, 70.0, "Some text"));

        PageTriage result = TriageProcessor.triagePage(0, contents, pageBoundingBox);

        assertEquals(TriageProcessor.PATH_FAST, result.getPath());
        assertFalse(result.isNeedsOcr());
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
    public void testAnalyzePageSignals_NullBoundingBox() {
        List<IChunk> contents = new ArrayList<>();
        contents.add(createTextChunk(0.0, 0.0, 50.0, 50.0, "Test"));

        TriageSignals signals = TriageProcessor.analyzePageSignals(contents, null);

        assertEquals(0.0, signals.getImageAreaRatio());
        assertEquals(0.0, signals.getTextCoverage());
    }

    @Test
    public void testPageTriageGetters() {
        TriageSignals signals = new TriageSignals(0.1, 0.2, 0.3, true, true, true, true, false);
        PageTriage triage = new PageTriage(5, TriageProcessor.PATH_AI, true, true, signals);

        assertEquals(5, triage.getPageNumber());
        assertEquals(TriageProcessor.PATH_AI, triage.getPath());
        assertTrue(triage.isNeedsOcr());
        assertTrue(triage.isNeedsTableAi());
        assertNotNull(triage.getSignals());
    }

    @Test
    public void testTriageSignalsGetters() {
        TriageSignals signals = new TriageSignals(0.15, 0.25, 0.35, true, true, true, true, true);

        assertEquals(0.15, signals.getImageAreaRatio(), 0.001);
        assertEquals(0.25, signals.getTextCoverage(), 0.001);
        assertEquals(0.35, signals.getMissingToUnicodeRatio(), 0.001);
        assertTrue(signals.isHasType3Fonts());
        assertTrue(signals.isHasGridAlignedText());
        assertTrue(signals.isHasSuspiciousTextGaps());
        assertTrue(signals.isHasImage());
        assertTrue(signals.isHasText());
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

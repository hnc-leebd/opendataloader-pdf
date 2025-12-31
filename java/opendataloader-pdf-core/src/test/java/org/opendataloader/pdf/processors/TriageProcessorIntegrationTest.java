/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.processors;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.opendataloader.pdf.api.Config;
import org.opendataloader.pdf.processors.TriageProcessor.PageTriage;
import org.verapdf.wcag.algorithms.entities.content.IChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;
import org.verapdf.wcag.algorithms.semanticalgorithms.containers.StaticContainers;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for TriageProcessor using real PDF files.
 *
 * Tests that:
 * - Documents with tables (42 documents) are detected as needing table AI
 * - Documents without tables are NOT detected as needing table AI
 */
public class TriageProcessorIntegrationTest {

    private static final Path SAMPLES_DIR = Paths.get("../../samples/pdf");

    // Document IDs that have tables (teds score is not null in evaluation.json)
    // These 42 documents should be detected as needing table AI
    private static final Set<String> DOCUMENTS_WITH_TABLES = new HashSet<>(Arrays.asList(
        "01030000000045", "01030000000046", "01030000000047", "01030000000051",
        "01030000000052", "01030000000053", "01030000000064", "01030000000078",
        "01030000000081", "01030000000082", "01030000000083", "01030000000084",
        "01030000000088", "01030000000089", "01030000000090", "01030000000110",
        "01030000000116", "01030000000117", "01030000000119", "01030000000120",
        "01030000000121", "01030000000122", "01030000000127", "01030000000128",
        "01030000000130", "01030000000132", "01030000000146", "01030000000147",
        "01030000000149", "01030000000150", "01030000000165", "01030000000166",
        "01030000000170", "01030000000178", "01030000000180", "01030000000182",
        "01030000000187", "01030000000188", "01030000000189", "01030000000190",
        "01030000000197", "01030000000200"
    ));

    @BeforeAll
    public static void checkSamplesExist() {
        if (!Files.exists(SAMPLES_DIR)) {
            System.out.println("WARNING: samples/pdf directory not found at " + SAMPLES_DIR.toAbsolutePath());
            System.out.println("Skipping integration tests. Copy PDF files to run these tests.");
        }
    }

    /**
     * Provides all PDF files in the samples directory that match the 01030*.pdf pattern.
     */
    static Stream<String> benchmarkPdfFiles() throws IOException {
        if (!Files.exists(SAMPLES_DIR)) {
            return Stream.empty();
        }
        return Files.list(SAMPLES_DIR)
            .filter(p -> p.getFileName().toString().matches("01030\\d+\\.pdf"))
            .map(p -> p.getFileName().toString())
            .sorted();
    }

    /**
     * Tests that documents with tables are detected as needing table AI.
     */
    @ParameterizedTest(name = "Table detection: {0}")
    @MethodSource("documentsWithTables")
    public void testDocumentWithTables_ShouldDetectTableAi(String fileName) throws IOException {
        Path pdfPath = SAMPLES_DIR.resolve(fileName);
        if (!Files.exists(pdfPath)) {
            System.out.println("Skipping " + fileName + " - file not found");
            return;
        }

        boolean needsTableAi = checkDocumentNeedsTableAi(pdfPath.toFile());

        assertTrue(needsTableAi,
            "Document " + fileName + " has tables but was NOT detected as needing table AI");
    }

    /**
     * Tests that documents without tables are NOT detected as needing table AI.
     */
    @ParameterizedTest(name = "No table detection: {0}")
    @MethodSource("documentsWithoutTables")
    public void testDocumentWithoutTables_ShouldNotDetectTableAi(String fileName) throws IOException {
        Path pdfPath = SAMPLES_DIR.resolve(fileName);
        if (!Files.exists(pdfPath)) {
            System.out.println("Skipping " + fileName + " - file not found");
            return;
        }

        boolean needsTableAi = checkDocumentNeedsTableAi(pdfPath.toFile());

        assertFalse(needsTableAi,
            "Document " + fileName + " has no tables but WAS detected as needing table AI (false positive)");
    }

    /**
     * Provides file names for documents that have tables.
     */
    static Stream<String> documentsWithTables() throws IOException {
        return benchmarkPdfFiles()
            .filter(name -> {
                String docId = name.replace(".pdf", "");
                return DOCUMENTS_WITH_TABLES.contains(docId);
            });
    }

    /**
     * Provides file names for documents that do NOT have tables.
     */
    static Stream<String> documentsWithoutTables() throws IOException {
        return benchmarkPdfFiles()
            .filter(name -> {
                String docId = name.replace(".pdf", "");
                return !DOCUMENTS_WITH_TABLES.contains(docId);
            });
    }

    /**
     * Checks if any page in the document is detected as needing table AI.
     */
    private boolean checkDocumentNeedsTableAi(File pdfFile) throws IOException {
        Config config = new Config();
        DocumentProcessor.preprocessing(pdfFile.getAbsolutePath(), config);

        int numberOfPages = StaticContainers.getDocument().getNumberOfPages();

        for (int pageNumber = 0; pageNumber < numberOfPages; pageNumber++) {
            List<IChunk> rawContents = StaticContainers.getDocument().getArtifacts(pageNumber);
            BoundingBox pageBoundingBox = DocumentProcessor.getPageBoundingBox(pageNumber);
            PageTriage triage = TriageProcessor.triagePage(pageNumber, rawContents, pageBoundingBox);

            if (triage.isNeedsTableAi()) {
                return true;
            }
        }

        return false;
    }

    /**
     * Summary test that runs all files and reports statistics.
     */
    @Test
    public void testTriageAccuracySummary() throws IOException {
        if (!Files.exists(SAMPLES_DIR)) {
            System.out.println("Skipping summary test - samples directory not found");
            return;
        }

        List<String> allFiles = benchmarkPdfFiles().collect(java.util.stream.Collectors.toList());
        if (allFiles.isEmpty()) {
            System.out.println("No benchmark PDF files found");
            return;
        }

        int truePositives = 0;  // Has table, detected as table
        int falseNegatives = 0; // Has table, NOT detected
        int trueNegatives = 0;  // No table, NOT detected
        int falsePositives = 0; // No table, detected as table

        List<String> falseNegativeFiles = new ArrayList<>();
        List<String> falsePositiveFiles = new ArrayList<>();

        for (String fileName : allFiles) {
            Path pdfPath = SAMPLES_DIR.resolve(fileName);
            if (!Files.exists(pdfPath)) {
                continue;
            }

            String docId = fileName.replace(".pdf", "");
            boolean hasTable = DOCUMENTS_WITH_TABLES.contains(docId);
            boolean detectedTable = checkDocumentNeedsTableAi(pdfPath.toFile());

            if (hasTable && detectedTable) {
                truePositives++;
            } else if (hasTable && !detectedTable) {
                falseNegatives++;
                falseNegativeFiles.add(fileName);
            } else if (!hasTable && !detectedTable) {
                trueNegatives++;
            } else {
                falsePositives++;
                falsePositiveFiles.add(fileName);
            }
        }

        int total = truePositives + falseNegatives + trueNegatives + falsePositives;
        double precision = truePositives + falsePositives > 0
            ? (double) truePositives / (truePositives + falsePositives) : 0;
        double recall = truePositives + falseNegatives > 0
            ? (double) truePositives / (truePositives + falseNegatives) : 0;
        double f1 = precision + recall > 0
            ? 2 * precision * recall / (precision + recall) : 0;

        System.out.println("\n=== Triage Accuracy Summary ===");
        System.out.println("Total documents: " + total);
        System.out.println("Documents with tables: " + (truePositives + falseNegatives));
        System.out.println("Documents without tables: " + (trueNegatives + falsePositives));
        System.out.println();
        System.out.println("True Positives (correctly detected tables): " + truePositives);
        System.out.println("False Negatives (missed tables): " + falseNegatives);
        System.out.println("True Negatives (correctly no table): " + trueNegatives);
        System.out.println("False Positives (false table detection): " + falsePositives);
        System.out.println();
        System.out.printf("Precision: %.2f%%\n", precision * 100);
        System.out.printf("Recall: %.2f%%\n", recall * 100);
        System.out.printf("F1 Score: %.2f%%\n", f1 * 100);

        if (!falseNegativeFiles.isEmpty()) {
            System.out.println("\nFalse Negatives (tables not detected):");
            falseNegativeFiles.forEach(f -> System.out.println("  - " + f));
        }

        if (!falsePositiveFiles.isEmpty()) {
            System.out.println("\nFalse Positives (incorrectly detected as table):");
            falsePositiveFiles.forEach(f -> System.out.println("  - " + f));
        }

        // The test passes but prints summary - adjust these assertions based on requirements
        // For now, we just ensure no exceptions occurred
        assertTrue(total > 0 || !Files.exists(SAMPLES_DIR),
            "Should process at least some files if samples exist");
    }
}

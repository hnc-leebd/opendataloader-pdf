/*
 * Copyright 2025 Hancom Inc.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.opendataloader.pdf.json;

import org.verapdf.wcag.algorithms.semanticalgorithms.consumers.ContrastRatioConsumer;

/**
 * Thread-local context for JSON serialization, providing access to shared resources
 * needed during image extraction and other serialization operations.
 */
public class JsonSerializationContext {
    private static final ThreadLocal<String> imageDirectoryName = new ThreadLocal<>();
    private static final ThreadLocal<String> pdfFileName = new ThreadLocal<>();
    private static final ThreadLocal<String> password = new ThreadLocal<>();
    private static final ThreadLocal<Boolean> addImageToJson = new ThreadLocal<>();
    private static final ThreadLocal<ContrastRatioConsumer> contrastRatioConsumer = new ThreadLocal<>();

    public static void clear() {
        imageDirectoryName.remove();
        pdfFileName.remove();
        password.remove();
        addImageToJson.set(false);
        contrastRatioConsumer.remove();
    }

    public static String getImageDirectoryName() {
        return imageDirectoryName.get();
    }

    public static void setImageDirectoryName(String directoryName) {
        imageDirectoryName.set(directoryName);
    }

    public static String getPdfFileName() {
        return pdfFileName.get();
    }

    public static void setPdfFileName(String fileName) {
        pdfFileName.set(fileName);
    }

    public static String getPassword() {
        return password.get();
    }

    public static void setPassword(String pwd) {
        password.set(pwd);
    }

    public static Boolean isAddImageToJson() {
        Boolean value = addImageToJson.get();
        return value != null && value;
    }

    public static void setAddImageToJson(Boolean value) {
        addImageToJson.set(value);
    }

    public static ContrastRatioConsumer getContrastRatioConsumer() {
        return contrastRatioConsumer.get();
    }

    public static void setContrastRatioConsumer(ContrastRatioConsumer consumer) {
        contrastRatioConsumer.set(consumer);
    }
}

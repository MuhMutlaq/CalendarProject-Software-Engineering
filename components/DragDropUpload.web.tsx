import React, { useState, useCallback } from "react";
import { View, Text, StyleSheet } from "react-native";

interface DragDropUploadProps {
  onFileSelected: (file: File) => void;
  acceptedTypes?: string[];
  children?: React.ReactNode;
}

export default function DragDropUpload({
  onFileSelected,
  acceptedTypes = ["application/pdf", "image/jpeg", "image/png", "image/jpg"],
  children,
}: DragDropUploadProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Only hide if we're leaving the window entirely
    const relatedTarget = e.relatedTarget as Node;
    if (!relatedTarget || relatedTarget.nodeName === "HTML") {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        const file = files[0];

        // Check if file type is accepted
        if (acceptedTypes.length > 0) {
          const isAccepted = acceptedTypes.some((type) => {
            if (type.endsWith("/*")) {
              // Handle wildcard types like "image/*"
              const baseType = type.replace("/*", "");
              return file.type.startsWith(baseType);
            }
            return file.type === type;
          });

          if (!isAccepted) {
            alert(`File type not supported. Please upload: ${acceptedTypes.join(", ")}`);
            return;
          }
        }

        onFileSelected(file);
      }
    },
    [acceptedTypes, onFileSelected]
  );

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
      }}
    >
      {children}

      {isDragging && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.3)",
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            zIndex: 1000,
            pointerEvents: "none",
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "90%",
              maxWidth: "500px",
              backgroundColor: "rgba(0, 122, 255, 0.95)",
              border: "3px dashed #FFFFFF",
              borderRadius: "16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "30px",
              boxShadow: "0 10px 40px rgba(0, 0, 0, 0.3)",
              marginBottom: "20px",
            }}
          >
            <View style={styles.dropOverlay}>
              <Text style={styles.dropText}>📁</Text>
              <Text style={styles.dropText}>Drop file here</Text>
              <Text style={styles.dropSubtext}>PDF or Image files</Text>
            </View>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = StyleSheet.create({
  dropOverlay: {
    alignItems: "center",
    justifyContent: "center",
  },
  dropText: {
    fontSize: 24,
    fontWeight: "700",
    color: "#FFFFFF",
    textAlign: "center",
    marginBottom: 8,
  },
  dropSubtext: {
    fontSize: 14,
    color: "#E3F2FD",
    textAlign: "center",
  },
});
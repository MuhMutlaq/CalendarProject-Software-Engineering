import React from "react";
import { View } from "react-native";

interface DragDropUploadProps {
  onFileSelected?: (file: File) => void;
  acceptedTypes?: string[];
  children?: React.ReactNode;
}

// Fallback component for iOS and Android - just renders children without drag-and-drop
export default function DragDropUpload({
  children,
}: DragDropUploadProps) {
  return <View style={{ flex: 1 }}>{children}</View>;
}

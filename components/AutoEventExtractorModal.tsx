import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  TextInput,
  Alert,
  Platform,
} from "react-native";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import DragDropUpload from "./DragDropUpload";

export interface ExtractedEvent {
  id: string;
  date: string;
  title: string;
  description: string;
  confidence?: number; // Optional: AI confidence score
}

interface AutoEventExtractorModalProps {
  visible: boolean;
  onClose: () => void;
  onSaveEvents: (events: Omit<ExtractedEvent, "id">[]) => Promise<void>;
}

export default function AutoEventExtractorModal({
  visible,
  onClose,
  onSaveEvents,
}: AutoEventExtractorModalProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [extractedEvents, setExtractedEvents] = useState<ExtractedEvent[]>([]);
  const [allEvents, setAllEvents] = useState<ExtractedEvent[]>([]); // Store all events before filtering
  const [availableMajors, setAvailableMajors] = useState<string[]>([]);
  const [availableLevels, setAvailableLevels] = useState<string[]>([]);
  const [selectedMajor, setSelectedMajor] = useState<string>("All");
  const [selectedLevel, setSelectedLevel] = useState<string>("All");
  const [showFilters, setShowFilters] = useState(false);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDate, setEditDate] = useState("");

  // Backend URL - Update this with your actual backend URL
  // For local development: http://localhost:5000 (for web)
  // For iOS simulator: http://localhost:5000
  // For Android emulator: http://10.0.2.2:5000
  // For physical device: http://YOUR_COMPUTER_IP:5000
  const BACKEND_URL = Platform.select({
    android: "http://10.0.2.2:5000",
    ios: "http://localhost:5000",
    default: "http://localhost:5000",
  });

  const uploadFileToBackend = async (fileUri: string, fileName: string, fileBlob?: Blob) => {
    console.log("Starting upload:", fileName, "Blob:", !!fileBlob);
    setIsProcessing(true);

    try {
      const formData = new FormData();

      // Create file blob for upload
      const fileType = fileName.split(".").pop()?.toLowerCase();
      const mimeType = fileType === "pdf"
        ? "application/pdf"
        : `image/${fileType}`;

      if (fileBlob) {
        // Web: Use the File object directly
        console.log("Appending file to FormData:", fileName, mimeType);
        formData.append("file", fileBlob, fileName);
      } else {
        // Mobile: Use the URI
        formData.append("file", {
          uri: fileUri,
          name: fileName,
          type: mimeType,
        } as any);
      }

      console.log("Sending to backend:", `${BACKEND_URL}/extract-events`);
      const response = await fetch(`${BACKEND_URL}/extract-events`, {
        method: "POST",
        body: formData,
        headers: Platform.OS === "web" ? {} : {
          "Content-Type": "multipart/form-data",
        },
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log("Backend response:", data);

      if (data.success && data.events && data.events.length > 0) {
        // Convert backend events to our format
        const events: ExtractedEvent[] = data.events.map(
          (event: any, index: number) => ({
            id: `temp-${Date.now()}-${index}`,
            date: event.date,
            title: event.title || "Untitled Event",
            description: event.description || "",
            confidence: event.confidence || 0.7,
          })
        );

        console.log("Extracted events:", events);

        // Store all events
        setAllEvents(events);
        setExtractedEvents(events);

        // Set available majors and levels from backend
        if (data.majors && data.majors.length > 0) {
          setAvailableMajors(data.majors);
          setShowFilters(true);
        }
        if (data.levels && data.levels.length > 0) {
          setAvailableLevels(data.levels);
        }

        // Reset filters
        setSelectedMajor("All");
        setSelectedLevel("All");
      } else {
        console.log("No events found in response");
        Alert.alert(
          "No Events Found",
          "Could not extract any dates from the file. Please try another file."
        );
      }
    } catch (error) {
      console.error("Backend error:", error);
      Alert.alert(
        "Error",
        "Failed to process file. Make sure the Python backend is running."
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // Apply filters to events
  const applyFilters = (major: string, level: string) => {
    let filtered = [...allEvents];

    if (major !== "All") {
      filtered = filtered.filter(
        (event) =>
          event.description &&
          event.description.toLowerCase().includes(`major: ${major.toLowerCase()}`)
      );
    }

    if (level !== "All") {
      filtered = filtered.filter(
        (event) =>
          event.description &&
          event.description.toLowerCase().includes(`level: ${level.toLowerCase()}`)
      );
    }

    setExtractedEvents(filtered);
  };

  // Handler for major filter change
  const handleMajorChange = (major: string) => {
    setSelectedMajor(major);
    applyFilters(major, selectedLevel);
  };

  // Handler for level filter change
  const handleLevelChange = (level: string) => {
    setSelectedLevel(level);
    applyFilters(selectedMajor, level);
  };

  // Handler for web drag-and-drop
  const handleWebFileSelected = async (file: File) => {
    console.log("File dropped:", file.name, file.type, file.size);
    setIsUploading(true);
    try {
      await uploadFileToBackend(URL.createObjectURL(file), file.name, file);
    } catch (error) {
      console.error("Upload error:", error);
      Alert.alert("Error", "Failed to upload file. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileUpload = async () => {
    setIsUploading(true);

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*"],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        setIsUploading(false);
        return;
      }

      const file = result.assets[0];
      await uploadFileToBackend(file.uri, file.name);
    } catch (error) {
      console.error("Upload error:", error);
      Alert.alert("Error", "Failed to upload file. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handlePhotoUpload = async () => {
    setIsUploading(true);

    try {
      // Request media library permission
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permissionResult.granted) {
        Alert.alert(
          "Permission Required",
          "Photo library permission is required to select images."
        );
        setIsUploading(false);
        return;
      }

      // Launch image library picker
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 1,
      });

      if (result.canceled) {
        setIsUploading(false);
        return;
      }

      const image = result.assets[0];
      const fileName = `photo_${Date.now()}.jpg`;
      await uploadFileToBackend(image.uri, fileName);
    } catch (error) {
      console.error("Upload error:", error);
      Alert.alert("Error", "Failed to upload photo. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleEditEvent = (event: ExtractedEvent) => {
    setEditingEventId(event.id);
    setEditTitle(event.title);
    setEditDescription(event.description);
    setEditDate(event.date);
  };

  const handleSaveEdit = () => {
    if (!editingEventId) return;

    setExtractedEvents((prev) =>
      prev.map((event) =>
        event.id === editingEventId
          ? {
              ...event,
              title: editTitle,
              description: editDescription,
              date: editDate,
            }
          : event
      )
    );

    setEditingEventId(null);
    setEditTitle("");
    setEditDescription("");
    setEditDate("");
  };

  const handleCancelEdit = () => {
    setEditingEventId(null);
    setEditTitle("");
    setEditDescription("");
    setEditDate("");
  };

  const handleDeleteEvent = (eventId: string) => {
    if (Platform.OS === "web") {
      // Web: Use native confirm dialog
      if (window.confirm("Are you sure you want to delete this event?")) {
        setExtractedEvents((prev) =>
          prev.filter((event) => event.id !== eventId)
        );
      }
    } else {
      // Mobile: Use React Native Alert
      Alert.alert("Delete Event", "Are you sure you want to delete this event?", [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            setExtractedEvents((prev) =>
              prev.filter((event) => event.id !== eventId)
            );
          },
        },
      ]);
    }
  };

  const handleSaveAllEvents = async () => {
    try {
      const eventsToSave = extractedEvents.map(({ id, ...event }) => event);
      await onSaveEvents(eventsToSave);

      if (Platform.OS === "web") {
        // Web: Show alert and close immediately
        alert(`Success! ${extractedEvents.length} event(s) added to your calendar!`);
        handleClose();
      } else {
        // Mobile: Use React Native Alert
        Alert.alert(
          "Success",
          `${extractedEvents.length} event(s) added to your calendar!`,
          [{ text: "OK", onPress: handleClose }]
        );
      }
    } catch (error) {
      console.error("Save error:", error);
      if (Platform.OS === "web") {
        alert("Error: Failed to save events. Please try again.");
      } else {
        Alert.alert("Error", "Failed to save events. Please try again.");
      }
    }
  };

  const handleClose = () => {
    setExtractedEvents([]);
    setAllEvents([]);
    setAvailableMajors([]);
    setAvailableLevels([]);
    setSelectedMajor("All");
    setSelectedLevel("All");
    setShowFilters(false);
    setEditingEventId(null);
    setEditTitle("");
    setEditDescription("");
    setEditDate("");
    setIsProcessing(false);
    setIsUploading(false);
    onClose();
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true}>
      <View style={styles.modalOverlay}>
        <DragDropUpload
          onFileSelected={handleWebFileSelected}
          acceptedTypes={["application/pdf", "image/*"]}
        >
          <View style={styles.modalContainer}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.title}>🤖 Auto Add Events</Text>
              <TouchableOpacity onPress={handleClose} style={styles.closeButton}>
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </View>

            {/* Content */}
            <ScrollView style={styles.content}>
            {/* Upload Section */}
            {extractedEvents.length === 0 && !isProcessing && (
              <View style={styles.uploadSection}>
                <Text style={styles.instructionText}>
                  {Platform.OS === "web"
                    ? "Drag & drop a PDF or image here, or click below to upload"
                    : "Upload a photo or file to automatically extract event dates"}
                </Text>

                <TouchableOpacity
                  style={styles.uploadButton}
                  onPress={handlePhotoUpload}
                  disabled={isUploading}
                >
                  <Text style={styles.uploadButtonIcon}>📷</Text>
                  <Text style={styles.uploadButtonText}>Upload Photo</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.uploadButton, styles.uploadButtonSecondary]}
                  onPress={handleFileUpload}
                  disabled={isUploading}
                >
                  <Text style={styles.uploadButtonIcon}>📄</Text>
                  <Text style={styles.uploadButtonText}>Upload File</Text>
                </TouchableOpacity>

                {isUploading && (
                  <View style={styles.loadingContainer}>
                    <ActivityIndicator size="small" color="#007AFF" />
                    <Text style={styles.loadingText}>Uploading...</Text>
                  </View>
                )}
              </View>
            )}

            {/* Processing Indicator */}
            {isProcessing && (
              <View style={styles.processingContainer}>
                <ActivityIndicator size="large" color="#007AFF" />
                <Text style={styles.processingText}>
                  Extracting events from your file...
                </Text>
                <Text style={styles.processingSubtext}>
                  This may take a few moments
                </Text>
              </View>
            )}

            {/* Extracted Events List */}
            {extractedEvents.length > 0 && !isProcessing && (
              <View style={styles.eventsSection}>
                <Text style={styles.sectionTitle}>
                  Found {extractedEvents.length} event(s)
                </Text>
                <Text style={styles.sectionSubtitle}>
                  Review and edit before adding to calendar
                </Text>

                {extractedEvents.map((event) => (
                  <View key={event.id} style={styles.eventCard}>
                    {editingEventId === event.id ? (
                      // Edit Mode
                      <View style={styles.editContainer}>
                        <Text style={styles.editLabel}>Title</Text>
                        <TextInput
                          style={styles.editInput}
                          value={editTitle}
                          onChangeText={setEditTitle}
                          placeholder="Event title"
                        />

                        <Text style={styles.editLabel}>Description</Text>
                        <TextInput
                          style={[styles.editInput, styles.editInputMultiline]}
                          value={editDescription}
                          onChangeText={setEditDescription}
                          placeholder="Event description"
                          multiline
                          numberOfLines={3}
                        />

                        <Text style={styles.editLabel}>Date (YYYY-MM-DD)</Text>
                        <TextInput
                          style={styles.editInput}
                          value={editDate}
                          onChangeText={setEditDate}
                          placeholder="2025-10-20"
                        />

                        <View style={styles.editActions}>
                          <TouchableOpacity
                            style={styles.cancelButton}
                            onPress={handleCancelEdit}
                          >
                            <Text style={styles.cancelButtonText}>Cancel</Text>
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={styles.saveEditButton}
                            onPress={handleSaveEdit}
                          >
                            <Text style={styles.saveEditButtonText}>Save</Text>
                          </TouchableOpacity>
                        </View>
                      </View>
                    ) : (
                      // View Mode
                      <>
                        <View style={styles.eventHeader}>
                          <View style={styles.eventHeaderLeft}>
                            <Text style={styles.eventTitle}>{event.title}</Text>
                            {event.confidence && (
                              <Text style={styles.confidenceText}>
                                {Math.round(event.confidence * 100)}% confident
                              </Text>
                            )}
                          </View>
                        </View>

                        <Text style={styles.eventDate}>
                          📅 {formatDate(event.date)}
                        </Text>

                        {event.description && (
                          <Text style={styles.eventDescription}>
                            {event.description}
                          </Text>
                        )}

                        <View style={styles.eventActions}>
                          <TouchableOpacity
                            style={styles.editButton}
                            onPress={() => handleEditEvent(event)}
                          >
                            <Text style={styles.editButtonText}>✏️ Edit</Text>
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={styles.deleteButton}
                            onPress={() => handleDeleteEvent(event.id)}
                          >
                            <Text style={styles.deleteButtonText}>
                              🗑️ Delete
                            </Text>
                          </TouchableOpacity>
                        </View>
                      </>
                    )}
                  </View>
                ))}

                {/* Action Buttons */}
                <View style={styles.bottomActions}>
                  <TouchableOpacity
                    style={styles.addMoreButton}
                    onPress={() => setExtractedEvents([])}
                  >
                    <Text style={styles.addMoreButtonText}>
                      + Upload Another File
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.saveAllButton}
                    onPress={handleSaveAllEvents}
                  >
                    <Text style={styles.saveAllButtonText}>
                      Save All Events ({extractedEvents.length})
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}
          </ScrollView>
          </View>
        </DragDropUpload>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "flex-end",
  },
  modalContainer: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: "75%",
    minHeight: "75%",
    top: "25%"
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#333",
  },
  closeButton: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#f0f0f0",
    alignItems: "center",
    justifyContent: "center",
  },
  closeButtonText: {
    fontSize: 18,
    color: "#666",
  },
  content: {
    flex: 1,
    padding: 20,
  },
  uploadSection: {
    alignItems: "center",
    paddingVertical: 40,
  },
  instructionText: {
    fontSize: 16,
    color: "#666",
    textAlign: "center",
    marginBottom: 30,
    paddingHorizontal: 20,
  },
  uploadButton: {
    backgroundColor: "#007AFF",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    borderRadius: 12,
    width: "100%",
    marginBottom: 15,
  },
  uploadButtonSecondary: {
    backgroundColor: "#34C759",
  },
  uploadButtonIcon: {
    fontSize: 24,
    marginRight: 10,
  },
  uploadButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 20,
  },
  loadingText: {
    marginLeft: 10,
    color: "#666",
    fontSize: 14,
  },
  processingContainer: {
    alignItems: "center",
    paddingVertical: 60,
  },
  processingText: {
    marginTop: 20,
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  processingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
  },
  eventsSection: {
    paddingBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#333",
    marginBottom: 5,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: "#666",
    marginBottom: 20,
  },
  eventCard: {
    backgroundColor: "#f8f8f8",
    borderRadius: 12,
    padding: 16,
    marginBottom: 15,
    borderLeftWidth: 4,
    borderLeftColor: "#007AFF",
  },
  eventHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  eventHeaderLeft: {
    flex: 1,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 4,
  },
  confidenceText: {
    fontSize: 11,
    color: "#34C759",
    fontWeight: "600",
  },
  eventDate: {
    fontSize: 14,
    color: "#666",
    marginBottom: 8,
  },
  eventDescription: {
    fontSize: 14,
    color: "#666",
    marginBottom: 12,
  },
  eventActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
  },
  editButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#007AFF",
  },
  editButtonText: {
    color: "#007AFF",
    fontSize: 14,
    fontWeight: "600",
  },
  deleteButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#FF3B30",
  },
  deleteButtonText: {
    color: "#FF3B30",
    fontSize: 14,
    fontWeight: "600",
  },
  editContainer: {
    gap: 10,
  },
  editLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
    marginBottom: 4,
  },
  editInput: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
  },
  editInputMultiline: {
    minHeight: 80,
    textAlignVertical: "top",
  },
  editActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
    marginTop: 10,
  },
  cancelButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#f0f0f0",
  },
  cancelButtonText: {
    color: "#666",
    fontSize: 14,
    fontWeight: "600",
  },
  saveEditButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#007AFF",
  },
  saveEditButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  bottomActions: {
    marginTop: 20,
    gap: 12,
  },
  addMoreButton: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#fff",
    borderWidth: 2,
    borderColor: "#007AFF",
    alignItems: "center",
  },
  addMoreButtonText: {
    color: "#007AFF",
    fontSize: 16,
    fontWeight: "600",
  },
  saveAllButton: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#34C759",
    alignItems: "center",
  },
  saveAllButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
});

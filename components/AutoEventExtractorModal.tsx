import React, { useState, useCallback, useEffect } from "react";
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

// =============================================================================
// TYPES
// =============================================================================

export interface ExtractedEvent {
  id: string;
  date: string;
  time?: string;
  title: string;
  description: string;
  course_code?: string;
  course_name?: string;
  major_level?: string;
  offered_to?: string;
  confidence?: number;
}

interface AutoEventExtractorModalProps {
  visible: boolean;
  onClose: () => void;
  onSaveEvents: (events: Omit<ExtractedEvent, "id">[]) => Promise<void>;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function AutoEventExtractorModal({
  visible,
  onClose,
  onSaveEvents,
}: AutoEventExtractorModalProps) {
  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileUri, setSelectedFileUri] = useState<string>("");
  const [selectedFileName, setSelectedFileName] = useState<string>("");
  const [fileSelected, setFileSelected] = useState(false);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState<string>("");

  // Events state - Two stage approach
  const [allExtractedEvents, setAllExtractedEvents] = useState<ExtractedEvent[]>([]);
  const [filteredEvents, setFilteredEvents] = useState<ExtractedEvent[]>([]);
  const [displayedEvents, setDisplayedEvents] = useState<ExtractedEvent[]>([]);

  // Available filter options (extracted from document)
  const [availableMajors, setAvailableMajors] = useState<string[]>([]);
  const [availableLevels, setAvailableLevels] = useState<string[]>([]);

  // User input filters
  const [userMajorLevel, setUserMajorLevel] = useState<string>("");
  const [userOfferedTo, setUserOfferedTo] = useState<string>("");

  // UI state
  const [showUserInputs, setShowUserInputs] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDate, setEditDate] = useState("");

  // Backend URL configuration
  const BACKEND_URL = Platform.select({
    android: "http://10.0.2.2:5000",
    ios: "http://localhost:5000",
    default: "http://localhost:5000",
  });

  // =============================================================================
  // BACKEND API FUNCTIONS
  // =============================================================================

  /**
   * Stage 1 & 2: Extract and filter events from backend
   * Backend handles both extraction and filtering in one call
   */
  const extractAndFilterEvents = async (
    fileUri: string,
    fileName: string,
    fileBlob?: Blob
  ): Promise<void> => {
    setIsProcessing(true);
    setProcessingStage("Uploading file...");

    try {
      const formData = new FormData();

      // Prepare file for upload
      const fileType = fileName.split(".").pop()?.toLowerCase();
      const mimeType = fileType === "pdf" ? "application/pdf" : `image/${fileType}`;

      if (fileBlob) {
        // Web: Use File object directly
        formData.append("file", fileBlob, fileName);
      } else {
        // Mobile: Use URI
        formData.append("file", {
          uri: fileUri,
          name: fileName,
          type: mimeType,
        } as any);
      }

      // Add filter parameters (even if empty - backend will return all if empty)
      formData.append("major_level", userMajorLevel.trim() || "");
      formData.append("offered_to", userOfferedTo.trim() || "");

      console.log("🚀 Sending to backend:", `${BACKEND_URL}/extract-events`);
      console.log("📋 Filters - Level:", userMajorLevel || "all", "Major:", userOfferedTo || "all");

      setProcessingStage("Extracting events with AI...");

      const response = await fetch(`${BACKEND_URL}/extract-events`, {
        method: "POST",
        body: formData,
        headers: Platform.OS === "web" ? {} : { "Content-Type": "multipart/form-data" },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log("✅ Backend response:", data);

      if (data.success && data.events && data.events.length > 0) {
        setProcessingStage("Processing results...");

        // Convert to our event format with unique IDs
        const events: ExtractedEvent[] = data.events.map(
          (event: any, index: number) => ({
            id: `event-${Date.now()}-${index}`,
            date: event.date || "",
            time: event.time || "",
            title: event.title || event.course_code || "Event",
            description: event.description || "",
            course_code: event.course_code || "",
            course_name: event.course_name || "",
            major_level: event.major_level || "",
            offered_to: event.offered_to || "",
            confidence: event.confidence || 0.9,
          })
        );

        // Update state
        setAllExtractedEvents(events);
        setFilteredEvents(events);
        setDisplayedEvents(events);

        // Extract available filter options from events
        const majors = new Set<string>();
        const levels = new Set<string>();

        events.forEach((event) => {
          if (event.offered_to) {
            const offered = event.offered_to.toUpperCase();
            if (offered.includes(",")) {
              offered.split(",").forEach((m) => majors.add(m.trim()));
            } else if (offered !== "ALL") {
              majors.add(offered);
            }
          }
          if (event.major_level) {
            levels.add(event.major_level);
          }
        });

        setAvailableMajors(Array.from(majors).sort());
        setAvailableLevels(Array.from(levels).sort());
        setShowFilters(majors.size > 0 || levels.size > 0);

        console.log(`✅ Extracted ${data.total_extracted} events, ${events.length} after filter`);
      } else {
        showAlert(
          "No Events Found",
          "Could not extract any events from the file. Please try a different file or check if the document contains exam schedule data."
        );
      }
    } catch (error) {
      console.error("❌ Backend error:", error);
      showAlert(
        "Processing Error",
        `Failed to process file: ${error instanceof Error ? error.message : "Unknown error"}\n\nMake sure the Python backend is running on ${BACKEND_URL}`
      );
    } finally {
      setIsProcessing(false);
      setProcessingStage("");
    }
  };

  /**
   * Client-side filtering of already extracted events
   */
  const applyClientSideFilter = useCallback(
    (level: string, major: string) => {
      if (allExtractedEvents.length === 0) return;

      let filtered = [...allExtractedEvents];

      // Filter by level
      if (level && level !== "All") {
        filtered = filtered.filter((event) => {
          const eventLevel = (event.major_level || "").trim();
          return eventLevel === level || eventLevel === "";
        });
      }

      // Filter by major
      if (major && major !== "All") {
        const majorUpper = major.toUpperCase();
        filtered = filtered.filter((event) => {
          const offered = (event.offered_to || "").toUpperCase();
          if (offered === "" || offered === "ALL") return true;
          if (offered.includes(",")) {
            return offered.split(",").some((m) => m.trim() === majorUpper);
          }
          return offered === majorUpper || offered.includes(majorUpper);
        });
      }

      setFilteredEvents(filtered);
      setDisplayedEvents(filtered);
      console.log(`🔍 Client filter: ${allExtractedEvents.length} -> ${filtered.length} events`);
    },
    [allExtractedEvents]
  );

  // =============================================================================
  // FILE HANDLING
  // =============================================================================

  const handleWebFileSelected = async (file: File) => {
    console.log("📁 File dropped:", file.name, file.type, file.size);
    setSelectedFile(file);
    setSelectedFileUri(URL.createObjectURL(file));
    setSelectedFileName(file.name);
    setFileSelected(true);
  };

  const handleFileUpload = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*"],
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;

      const file = result.assets[0];
      setSelectedFileUri(file.uri);
      setSelectedFileName(file.name);
      setFileSelected(true);
    } catch (error) {
      console.error("File selection error:", error);
      showAlert("Error", "Failed to select file. Please try again.");
    }
  };

  const handlePhotoUpload = async () => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permissionResult.granted) {
        showAlert("Permission Required", "Photo library permission is needed to select images.");
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 1,
      });

      if (result.canceled) return;

      const image = result.assets[0];
      const fileName = `photo_${Date.now()}.jpg`;
      setSelectedFileUri(image.uri);
      setSelectedFileName(fileName);
      setFileSelected(true);
    } catch (error) {
      console.error("Photo selection error:", error);
      showAlert("Error", "Failed to select photo. Please try again.");
    }
  };

  const handleCameraCapture = async () => {
    try {
      const permissionResult = await ImagePicker.requestCameraPermissionsAsync();

      if (!permissionResult.granted) {
        showAlert("Permission Required", "Camera permission is needed to take photos.");
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 1,
      });

      if (result.canceled) return;

      const image = result.assets[0];
      const fileName = `camera_${Date.now()}.jpg`;
      setSelectedFileUri(image.uri);
      setSelectedFileName(fileName);
      setFileSelected(true);
    } catch (error) {
      console.error("Camera error:", error);
      showAlert("Error", "Failed to capture photo. Please try again.");
    }
  };

  const handleSubmit = async () => {
    if (!fileSelected || !selectedFileName) {
      showAlert("Error", "Please select a file first.");
      return;
    }

    await extractAndFilterEvents(
      selectedFileUri,
      selectedFileName,
      selectedFile || undefined
    );
  };

  const clearFileSelection = () => {
    setFileSelected(false);
    setSelectedFile(null);
    setSelectedFileUri("");
    setSelectedFileName("");
  };

  // =============================================================================
  // EVENT EDITING
  // =============================================================================

  const handleEditEvent = (event: ExtractedEvent) => {
    setEditingEventId(event.id);
    setEditTitle(event.title);
    setEditDescription(event.description);
    setEditDate(event.date);
  };

  const handleSaveEdit = () => {
    if (!editingEventId) return;

    const updateEvents = (events: ExtractedEvent[]) =>
      events.map((event) =>
        event.id === editingEventId
          ? { ...event, title: editTitle, description: editDescription, date: editDate }
          : event
      );

    setAllExtractedEvents((prev) => updateEvents(prev));
    setFilteredEvents((prev) => updateEvents(prev));
    setDisplayedEvents((prev) => updateEvents(prev));

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
    const confirmDelete = () => {
      const removeEvent = (events: ExtractedEvent[]) =>
        events.filter((event) => event.id !== eventId);

      setAllExtractedEvents((prev) => removeEvent(prev));
      setFilteredEvents((prev) => removeEvent(prev));
      setDisplayedEvents((prev) => removeEvent(prev));
    };

    if (Platform.OS === "web") {
      if (window.confirm("Are you sure you want to delete this event?")) {
        confirmDelete();
      }
    } else {
      Alert.alert("Delete Event", "Are you sure you want to delete this event?", [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: confirmDelete },
      ]);
    }
  };

  // =============================================================================
  // SAVE & CLOSE
  // =============================================================================

  const handleSaveAllEvents = async () => {
    if (displayedEvents.length === 0) {
      showAlert("No Events", "There are no events to save.");
      return;
    }

    try {
      const eventsToSave = displayedEvents.map(({ id, ...event }) => event);
      await onSaveEvents(eventsToSave);

      showAlert(
        "Success",
        `${displayedEvents.length} event(s) added to your calendar!`,
        handleClose
      );
    } catch (error) {
      console.error("Save error:", error);
      showAlert("Error", "Failed to save events. Please try again.");
    }
  };

  const handleClose = () => {
    // Reset all state
    setAllExtractedEvents([]);
    setFilteredEvents([]);
    setDisplayedEvents([]);
    setAvailableMajors([]);
    setAvailableLevels([]);
    setShowFilters(false);
    setEditingEventId(null);
    setEditTitle("");
    setEditDescription("");
    setEditDate("");
    setIsProcessing(false);
    setProcessingStage("");
    setUserMajorLevel("");
    setUserOfferedTo("");
    setShowUserInputs(true);
    clearFileSelection();
    onClose();
  };

  // =============================================================================
  // UTILITIES
  // =============================================================================

  const showAlert = (title: string, message: string, onOk?: () => void) => {
    if (Platform.OS === "web") {
      alert(`${title}\n\n${message}`);
      onOk?.();
    } else {
      Alert.alert(title, message, [{ text: "OK", onPress: onOk }]);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "No date";
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString("en-US", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // =============================================================================
  // RENDER
  // =============================================================================

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
              <Text style={styles.title}>🤖 Auto Extract Events</Text>
              <TouchableOpacity onPress={handleClose} style={styles.closeButton}>
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </View>

            {/* Content */}
            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              {/* ============ UPLOAD SECTION ============ */}
              {displayedEvents.length === 0 && !isProcessing && (
                <View style={styles.uploadSection}>
                  {/* Step 1: File Selection */}
                  <View style={styles.stepContainer}>
                    <Text style={styles.stepTitle}>Step 1: Select File</Text>
                    <Text style={styles.stepDescription}>
                      {Platform.OS === "web"
                        ? "Drag & drop a PDF/image or click to select"
                        : "Choose a photo or document with exam schedule"}
                    </Text>

                    {!fileSelected ? (
                      <View style={styles.uploadButtons}>
                        {Platform.OS !== "web" && (
                          <TouchableOpacity
                            style={styles.uploadButton}
                            onPress={handleCameraCapture}
                          >
                            <Text style={styles.uploadButtonIcon}>📷</Text>
                            <Text style={styles.uploadButtonText}>Take Photo</Text>
                          </TouchableOpacity>
                        )}

                        <TouchableOpacity
                          style={[styles.uploadButton, styles.uploadButtonSecondary]}
                          onPress={handlePhotoUpload}
                        >
                          <Text style={styles.uploadButtonIcon}>🖼️</Text>
                          <Text style={styles.uploadButtonText}>Select Photo</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                          style={[styles.uploadButton, styles.uploadButtonTertiary]}
                          onPress={handleFileUpload}
                        >
                          <Text style={styles.uploadButtonIcon}>📄</Text>
                          <Text style={styles.uploadButtonText}>Select PDF/File</Text>
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <View style={styles.selectedFileSection}>
                        <Text style={styles.selectedFileIcon}>✅</Text>
                        <Text style={styles.selectedFileTitle}>File Selected</Text>
                        <Text style={styles.selectedFileName}>{selectedFileName}</Text>
                        <TouchableOpacity
                          style={styles.changeFileButton}
                          onPress={clearFileSelection}
                        >
                          <Text style={styles.changeFileButtonText}>Change File</Text>
                        </TouchableOpacity>
                      </View>
                    )}
                  </View>

                  {/* Step 2: Filter Options (Optional) */}
                  {fileSelected && (
                    <View style={styles.stepContainer}>
                      <Text style={styles.stepTitle}>Step 2: Your Info (Optional)</Text>
                      <Text style={styles.stepDescription}>
                        Filter to show only your relevant exams, or leave empty for all
                      </Text>

                      <View style={styles.inputGroup}>
                        <Text style={styles.inputLabel}>Your Level (1-4)</Text>
                        <TextInput
                          style={styles.input}
                          value={userMajorLevel}
                          onChangeText={setUserMajorLevel}
                          placeholder="e.g., 1, 2, 3, or 4"
                          keyboardType="number-pad"
                          maxLength={1}
                        />
                      </View>

                      <View style={styles.inputGroup}>
                        <Text style={styles.inputLabel}>Your Major</Text>
                        <TextInput
                          style={styles.input}
                          value={userOfferedTo}
                          onChangeText={setUserOfferedTo}
                          placeholder="e.g., CS, SE, AI, CIS, CYS"
                          autoCapitalize="characters"
                        />
                      </View>

                      <TouchableOpacity
                        style={styles.submitButton}
                        onPress={handleSubmit}
                        disabled={isProcessing}
                      >
                        <Text style={styles.submitButtonText}>
                          🚀 Extract Events
                        </Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </View>
              )}

              {/* ============ PROCESSING INDICATOR ============ */}
              {isProcessing && (
                <View style={styles.processingContainer}>
                  <ActivityIndicator size="large" color="#007AFF" />
                  <Text style={styles.processingText}>
                    {processingStage || "Processing..."}
                  </Text>
                  <Text style={styles.processingSubtext}>
                    AI is analyzing your document
                  </Text>
                </View>
              )}

              {/* ============ RESULTS SECTION ============ */}
              {displayedEvents.length > 0 && !isProcessing && (
                <View style={styles.eventsSection}>
                  {/* Results Header */}
                  <View style={styles.resultsHeader}>
                    <Text style={styles.sectionTitle}>
                      📋 Found {displayedEvents.length} Event(s)
                    </Text>
                    {allExtractedEvents.length !== displayedEvents.length && (
                      <Text style={styles.filterNote}>
                        (filtered from {allExtractedEvents.length} total)
                      </Text>
                    )}
                  </View>

                  {/* Quick Filters */}
                  {showFilters && (
                    <View style={styles.quickFilters}>
                      <Text style={styles.quickFilterLabel}>Quick Filter:</Text>
                      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                        <TouchableOpacity
                          style={[
                            styles.filterChip,
                            !userMajorLevel && !userOfferedTo && styles.filterChipActive,
                          ]}
                          onPress={() => {
                            setUserMajorLevel("");
                            setUserOfferedTo("");
                            setDisplayedEvents(allExtractedEvents);
                          }}
                        >
                          <Text style={styles.filterChipText}>All</Text>
                        </TouchableOpacity>
                        {availableLevels.map((level) => (
                          <TouchableOpacity
                            key={`level-${level}`}
                            style={[
                              styles.filterChip,
                              userMajorLevel === level && styles.filterChipActive,
                            ]}
                            onPress={() => {
                              setUserMajorLevel(level);
                              applyClientSideFilter(level, userOfferedTo);
                            }}
                          >
                            <Text style={styles.filterChipText}>Level {level}</Text>
                          </TouchableOpacity>
                        ))}
                        {availableMajors.map((major) => (
                          <TouchableOpacity
                            key={`major-${major}`}
                            style={[
                              styles.filterChip,
                              userOfferedTo.toUpperCase() === major && styles.filterChipActive,
                            ]}
                            onPress={() => {
                              setUserOfferedTo(major);
                              applyClientSideFilter(userMajorLevel, major);
                            }}
                          >
                            <Text style={styles.filterChipText}>{major}</Text>
                          </TouchableOpacity>
                        ))}
                      </ScrollView>
                    </View>
                  )}

                  {/* Event Cards */}
                  {displayedEvents.map((event) => (
                    <View key={event.id} style={styles.eventCard}>
                      {editingEventId === event.id ? (
                        /* Edit Mode */
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
                            placeholder="2025-01-15"
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
                        /* View Mode */
                        <>
                          <View style={styles.eventHeader}>
                            <View style={styles.eventHeaderLeft}>
                              <Text style={styles.eventTitle}>{event.title}</Text>
                              {event.confidence && (
                                <View style={styles.confidenceBadge}>
                                  <Text style={styles.confidenceText}>
                                    {Math.round(event.confidence * 100)}% confident
                                  </Text>
                                </View>
                              )}
                            </View>
                          </View>

                          <Text style={styles.eventDate}>
                            📅 {formatDate(event.date)}
                            {event.time && ` • ⏰ ${event.time}`}
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
                              <Text style={styles.deleteButtonText}>🗑️ Delete</Text>
                            </TouchableOpacity>
                          </View>
                        </>
                      )}
                    </View>
                  ))}

                  {/* Bottom Actions */}
                  <View style={styles.bottomActions}>
                    <TouchableOpacity
                      style={styles.addMoreButton}
                      onPress={() => {
                        setAllExtractedEvents([]);
                        setFilteredEvents([]);
                        setDisplayedEvents([]);
                        clearFileSelection();
                        setShowFilters(false);
                      }}
                    >
                      <Text style={styles.addMoreButtonText}>
                        📤 Upload Another File
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.saveAllButton}
                      onPress={handleSaveAllEvents}
                    >
                      <Text style={styles.saveAllButtonText}>
                        ✅ Save All Events ({displayedEvents.length})
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

// =============================================================================
// STYLES
// =============================================================================

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
    maxHeight: "85%",
    minHeight: "85%",
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
    width: 32,
    height: 32,
    borderRadius: 16,
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

  // Upload Section
  uploadSection: {
    paddingVertical: 20,
  },
  stepContainer: {
    backgroundColor: "#f8f9fa",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  stepTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#333",
    marginBottom: 8,
  },
  stepDescription: {
    fontSize: 14,
    color: "#666",
    marginBottom: 20,
  },
  uploadButtons: {
    gap: 12,
  },
  uploadButton: {
    backgroundColor: "#007AFF",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    borderRadius: 12,
  },
  uploadButtonSecondary: {
    backgroundColor: "#34C759",
  },
  uploadButtonTertiary: {
    backgroundColor: "#FF9500",
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

  // Selected File
  selectedFileSection: {
    backgroundColor: "#e8f5e9",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    borderWidth: 2,
    borderColor: "#34C759",
    borderStyle: "dashed",
  },
  selectedFileIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  selectedFileTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#34C759",
    marginBottom: 4,
  },
  selectedFileName: {
    fontSize: 14,
    color: "#333",
    marginBottom: 12,
    textAlign: "center",
  },
  changeFileButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#34C759",
  },
  changeFileButtonText: {
    color: "#34C759",
    fontSize: 14,
    fontWeight: "600",
  },

  // Input Fields
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
    marginBottom: 8,
  },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
  },
  submitButton: {
    backgroundColor: "#007AFF",
    padding: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 8,
  },
  submitButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },

  // Processing
  processingContainer: {
    alignItems: "center",
    paddingVertical: 80,
  },
  processingText: {
    marginTop: 20,
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
  },
  processingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
  },

  // Results Section
  eventsSection: {
    paddingBottom: 40,
  },
  resultsHeader: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#333",
  },
  filterNote: {
    fontSize: 13,
    color: "#666",
    marginTop: 4,
  },

  // Quick Filters
  quickFilters: {
    marginBottom: 20,
  },
  quickFilterLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#666",
    marginBottom: 10,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#f0f0f0",
    marginRight: 8,
  },
  filterChipActive: {
    backgroundColor: "#007AFF",
  },
  filterChipText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
  },

  // Event Cards
  eventCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: "#007AFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
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
    fontWeight: "700",
    color: "#333",
    marginBottom: 4,
  },
  confidenceBadge: {
    backgroundColor: "#e8f5e9",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    alignSelf: "flex-start",
  },
  confidenceText: {
    fontSize: 11,
    color: "#34C759",
    fontWeight: "600",
  },
  eventDate: {
    fontSize: 14,
    color: "#007AFF",
    fontWeight: "600",
    marginBottom: 8,
  },
  eventDescription: {
    fontSize: 13,
    color: "#666",
    marginBottom: 12,
    lineHeight: 18,
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
    backgroundColor: "#f0f0f0",
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
    backgroundColor: "#fef2f2",
  },
  deleteButtonText: {
    color: "#FF3B30",
    fontSize: 14,
    fontWeight: "600",
  },

  // Edit Mode
  editContainer: {
    gap: 12,
  },
  editLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
  },
  editInput: {
    backgroundColor: "#f8f8f8",
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
    marginTop: 8,
  },
  cancelButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#f0f0f0",
  },
  cancelButtonText: {
    color: "#666",
    fontSize: 14,
    fontWeight: "600",
  },
  saveEditButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#007AFF",
  },
  saveEditButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },

  // Bottom Actions
  bottomActions: {
    marginTop: 24,
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
    padding: 18,
    borderRadius: 12,
    backgroundColor: "#34C759",
    alignItems: "center",
  },
  saveAllButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
});
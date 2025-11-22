import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Dimensions,
  ScrollView,
  StyleSheet,
} from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  runOnJS,
} from "react-native-reanimated";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import EventModal from "./EventModal";
import { CalendarEvent } from "../hooks/useEvents";

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const SCREEN_HEIGHT = Dimensions.get("window").height;

export default function CalendarMonthView({
  year,
  month,
  onBack,
  onMonthYearChange,
  events,
  onAddEvent,
  onDeleteEvent,
  getEventsForDate,
}: {
  year: number;
  month: number;
  onBack: () => void;
  onMonthYearChange: (newMonth: number, newYear: number) => void;
  events: CalendarEvent[];
  onAddEvent: (event: Omit<CalendarEvent, "id">) => Promise<void>;
  onDeleteEvent: (eventId: string) => Promise<void>;
  getEventsForDate: (date: string) => CalendarEvent[];
}) {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState("");

  // Get today's date for highlighting
  const today = new Date();
  const isCurrentMonth =
    today.getMonth() === month && today.getFullYear() === year;
  const currentDay = today.getDate();

  const translateY = useSharedValue(0);
  const opacity = useSharedValue(1);

  // Animate when month changes
  useEffect(() => {
    translateY.value = 0;
    opacity.value = 0;
    translateY.value = withTiming(0, { duration: 300 });
    opacity.value = withTiming(1, { duration: 300 });
  }, [month, year]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));

  const handleNextMonth = () => {
    if (month === 11) {
      // December -> January of next year
      onMonthYearChange(0, year + 1);
    } else {
      onMonthYearChange(month + 1, year);
    }
  };

  const handlePreviousMonth = () => {
    if (month === 0) {
      // January -> December of previous year
      onMonthYearChange(11, year - 1);
    } else {
      onMonthYearChange(month - 1, year);
    }
  };

  const pan = Gesture.Pan()
    .onUpdate((event) => {
      translateY.value = event.translationY;
    })
    .onEnd((event) => {
      const direction = event.translationY;

      if (direction < -80) {
        // Swipe up → next month - slide out upward
        translateY.value = withTiming(-SCREEN_HEIGHT, { duration: 250 });
        opacity.value = withTiming(0, { duration: 250 });
        setTimeout(() => runOnJS(handleNextMonth)(), 250);
      } else if (direction > 80) {
        // Swipe down → previous month - slide out downward
        translateY.value = withTiming(SCREEN_HEIGHT, { duration: 250 });
        opacity.value = withTiming(0, { duration: 250 });
        setTimeout(() => runOnJS(handlePreviousMonth)(), 250);
      } else {
        // Not enough swipe - bounce back
        translateY.value = withTiming(0, { duration: 200 });
      }
    });

  const formatDate = (day: number) => {
    const monthStr = String(month + 1).padStart(2, "0");
    const dayStr = String(day).padStart(2, "0");
    return `${year}-${monthStr}-${dayStr}`;
  };

  const handleDayPress = (day: number) => {
    setSelectedDay(day);
    const date = formatDate(day);
    setSelectedDate(date);
  };

  const handleAddEventPress = () => {
    if (selectedDay) {
      setShowEventModal(true);
    }
  };

  const handleSaveEvent = async (
    title: string,
    description: string,
    date: string
  ) => {
    await onAddEvent({ date, title, description });
  };

  const handleDeleteEvent = async (eventId: string) => {
    await onDeleteEvent(eventId);
  };

  const dayEvents = selectedDay
    ? getEventsForDate(formatDate(selectedDay))
    : [];

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.container, animatedStyle]}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.monthTitle}>
          {months[month]} {year}
        </Text>
        <Text style={styles.swipeHint}>Swipe ↑ or ↓ to change month</Text>

        <ScrollView style={styles.scrollView}>
          {/* Calendar Grid */}
          <View style={styles.calendarGrid}>
            {days.map((day) => {
              const dateStr = formatDate(day);
              const hasEvents = getEventsForDate(dateStr).length > 0;
              const isSelected = selectedDay === day;
              const isToday = isCurrentMonth && day === currentDay;

              return (
                <TouchableOpacity
                  key={day}
                  style={[
                    styles.dayCell,
                    isSelected && styles.selectedDayCell,
                    isToday && styles.todayCell,
                  ]}
                  onPress={() => handleDayPress(day)}
                >
                  <Text
                    style={[
                      styles.dayText,
                      isSelected && styles.selectedDayText,
                      isToday && styles.todayText,
                    ]}
                  >
                    {day}
                  </Text>
                  {hasEvents && <View style={styles.eventDot} />}
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Selected Day Events */}
          {selectedDay && (
            <View style={styles.eventsContainer}>
              <Text style={styles.eventsTitle}>
                Events on {months[month]} {selectedDay}, {year}
              </Text>

              {dayEvents.length === 0 ? (
                <Text style={styles.noEventsText}>No events for this day</Text>
              ) : (
                dayEvents.map((event) => (
                  <View key={event.id} style={styles.eventCard}>
                    <View style={styles.eventContent}>
                      <Text style={styles.eventTitle}>{event.title}</Text>
                      {event.description ? (
                        <Text style={styles.eventDescription}>
                          {event.description}
                        </Text>
                      ) : null}
                    </View>
                    <TouchableOpacity
                      style={styles.deleteButton}
                      onPress={() => handleDeleteEvent(event.id)}
                    >
                      <Text style={styles.deleteButtonText}>Delete</Text>
                    </TouchableOpacity>
                  </View>
                ))
              )}
            </View>
          )}

          {/* Upcoming Tasks Section */}
          {!selectedDay &&
            (() => {
              const todayDate = new Date(
                today.getFullYear(),
                today.getMonth(),
                today.getDate()
              );
              const upcomingEvents = events
                .filter((event) => {
                  const eventDate = new Date(event.date);
                  return eventDate >= todayDate;
                })
                .sort(
                  (a, b) =>
                    new Date(a.date).getTime() - new Date(b.date).getTime()
                );

              return upcomingEvents.length > 0 ? (
                <View style={styles.upcomingContainer}>
                  <Text style={styles.upcomingTitle}>📅 Upcoming Tasks</Text>
                  {upcomingEvents.map((event) => {
                    const eventDate = new Date(event.date);
                    const diffTime = eventDate.getTime() - todayDate.getTime();
                    const diffDays = Math.ceil(
                      diffTime / (1000 * 60 * 60 * 24)
                    );

                    let urgencyStyle = styles.lowUrgency;
                    let urgencyLabel = "";

                    if (diffDays === 0) {
                      urgencyStyle = styles.highUrgency;
                      urgencyLabel = "TODAY";
                    } else if (diffDays === 1) {
                      urgencyStyle = styles.highUrgency;
                      urgencyLabel = "TOMORROW";
                    } else if (diffDays <= 3) {
                      urgencyStyle = styles.mediumUrgency;
                      urgencyLabel = `IN ${diffDays} DAYS`;
                    } else if (diffDays <= 7) {
                      urgencyStyle = styles.lowUrgency;
                      urgencyLabel = `IN ${diffDays} DAYS`;
                    } else {
                      urgencyLabel = eventDate.toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year:
                          eventDate.getFullYear() !== today.getFullYear()
                            ? "numeric"
                            : undefined,
                      });
                    }

                    return (
                      <View
                        key={event.id}
                        style={[styles.upcomingCard, urgencyStyle]}
                      >
                        <View style={styles.upcomingContent}>
                          <Text style={styles.upcomingEventTitle}>
                            {event.title}
                          </Text>
                          {event.description ? (
                            <Text style={styles.upcomingEventDescription}>
                              {event.description}
                            </Text>
                          ) : null}
                          <Text style={styles.upcomingDate}>
                            {urgencyLabel}
                          </Text>
                        </View>
                      </View>
                    );
                  })}
                </View>
              ) : null;
            })()}
        </ScrollView>

        {/* Add Event Button - Always visible */}
        <TouchableOpacity
          style={[
            styles.addEventButton,
            !selectedDay && styles.addEventButtonDisabled,
          ]}
          onPress={handleAddEventPress}
          disabled={!selectedDay}
        >
          <Text style={styles.addEventButtonText}>
            {selectedDay
              ? `+ Add Event (Day ${selectedDay})`
              : "Select a day to add event"}
          </Text>
        </TouchableOpacity>

        {/* Event Modal */}
        <EventModal
          visible={showEventModal}
          onClose={() => setShowEventModal(false)}
          onSave={handleSaveEvent}
          selectedDate={selectedDate}
        />
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 10,
  },
  backButton: {
    color: "#007AFF",
    marginBottom: 10,
    fontSize: 16,
  },
  monthTitle: {
    fontSize: 20,
    fontWeight: "bold",
    textAlign: "center",
  },
  swipeHint: {
    fontSize: 12,
    color: "#888",
    textAlign: "center",
    marginTop: 4,
  },
  scrollView: {
    flex: 1,
  },
  calendarGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 20,
  },
  dayCell: {
    width: "14.28%",
    alignItems: "center",
    paddingVertical: 10,
    position: "relative",
  },
  selectedDayCell: {
    backgroundColor: "#007AFF",
    borderRadius: 20,
  },
  dayText: {
    fontSize: 16,
    color: "#333",
  },
  selectedDayText: {
    color: "#fff",
    fontWeight: "bold",
  },
  eventDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: "#FF3B30",
    position: "absolute",
    bottom: 5,
  },
  eventsContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: "#f8f8f8",
    borderRadius: 10,
  },
  eventsTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 10,
  },
  noEventsText: {
    color: "#999",
    fontStyle: "italic",
  },
  eventCard: {
    backgroundColor: "#fff",
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  eventContent: {
    flex: 1,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
  },
  eventDescription: {
    fontSize: 14,
    color: "#666",
  },
  deleteButton: {
    backgroundColor: "#FF3B30",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  deleteButtonText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
  addEventButton: {
    backgroundColor: "#007AFF",
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 10,
  },
  addEventButtonDisabled: {
    backgroundColor: "#ccc",
    opacity: 0.6,
  },
  addEventButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "bold",
  },
  todayCell: {
    borderWidth: 2,
    borderColor: "#FF9500",
    borderRadius: 20,
  },
  todayText: {
    color: "#FF9500",
    fontWeight: "bold",
  },
  upcomingContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: "#f8f8f8",
    borderRadius: 10,
  },
  upcomingTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 15,
    color: "#333",
  },
  upcomingCard: {
    backgroundColor: "#fff",
    padding: 15,
    borderRadius: 10,
    marginBottom: 12,
    borderLeftWidth: 4,
  },
  upcomingContent: {
    flex: 1,
  },
  upcomingEventTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
    color: "#333",
  },
  upcomingEventDescription: {
    fontSize: 14,
    color: "#666",
    marginBottom: 8,
  },
  upcomingDate: {
    fontSize: 12,
    fontWeight: "700",
    color: "#fff",
    backgroundColor: "#333",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    alignSelf: "flex-start",
  },
  highUrgency: {
    borderLeftColor: "#FF3B30",
    backgroundColor: "#FFF5F5",
  },
  mediumUrgency: {
    borderLeftColor: "#FF9500",
    backgroundColor: "#FFF9F0",
  },
  lowUrgency: {
    borderLeftColor: "#34C759",
    backgroundColor: "#F5FFF8",
  },
});

import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
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
import { CalendarEvent } from "../hooks/useEvents";
import AutoEventExtractorModal from "./AutoEventExtractorModal";

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

const SCREEN_WIDTH = Dimensions.get("window").width;

export default function CalendarYearView({
  year,
  onSelectMonth,
  onChangeYear,
  events,
  onAddEvents,
}: {
  year: number;
  onSelectMonth: (monthIndex: number) => void;
  onChangeYear: (newYear: number) => void;
  events: CalendarEvent[];
  onAddEvents: (events: Omit<CalendarEvent, "id">[]) => Promise<void>;
}) {
  // Shared value to track swipe distance
  const translateX = useSharedValue(0);
  const opacity = useSharedValue(1);
  const [showAutoExtractor, setShowAutoExtractor] = useState(false);

  // Calculate events per month
  const getEventsForMonth = (monthIndex: number) => {
    return events.filter((event) => {
      const eventDate = new Date(event.date);
      return (
        eventDate.getMonth() === monthIndex && eventDate.getFullYear() === year
      );
    });
  };

  const monthEventCounts = months.map((_, index) => ({
    month: months[index],
    monthIndex: index,
    count: getEventsForMonth(index).length,
  }));

  // Get busiest months (sorted by event count, showing top 3)
  const busiestMonths = monthEventCounts
    .filter((m) => m.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  // When year changes, animate the slide
  useEffect(() => {
    // Slide in from right or left depending on direction
    translateX.value = 0;
    opacity.value = 0;
    translateX.value = withTiming(0, { duration: 300 });
    opacity.value = withTiming(1, { duration: 300 });
  }, [year]);

  // Animation style
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    opacity: opacity.value,
  }));

  // New gesture API
  const pan = Gesture.Pan()
    .onUpdate((event) => {
      translateX.value = event.translationX;
    })
    .onEnd((event) => {
      const direction = event.translationX;

      if (direction < -80) {
        // Swipe left → next year - slide out to left
        translateX.value = withTiming(-SCREEN_WIDTH, { duration: 250 });
        opacity.value = withTiming(0, { duration: 250 });
        setTimeout(() => runOnJS(onChangeYear)(year + 1), 250);
      } else if (direction > 80) {
        // Swipe right → previous year - slide out to right
        translateX.value = withTiming(SCREEN_WIDTH, { duration: 250 });
        opacity.value = withTiming(0, { duration: 250 });
        setTimeout(() => runOnJS(onChangeYear)(year - 1), 250);
      } else {
        // Not enough swipe - bounce back
        translateX.value = withTiming(0, { duration: 200 });
      }
    });

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.container, animatedStyle]}>
        {/* Year title */}
        <View style={styles.header}>
          <Text style={styles.yearTitle}>{year}</Text>
          <Text style={styles.swipeHint}>Swipe ← or → to change year</Text>
        </View>

        <ScrollView style={styles.scrollView}>
          {/* Month grid */}
          <View style={styles.monthGrid}>
            {months.map((month, index) => {
              // Check if this is the current month
              const today = new Date();
              const isCurrentMonth =
                today.getMonth() === index && today.getFullYear() === year;

              return (
                <TouchableOpacity
                  key={month}
                  onPress={() => onSelectMonth(index)}
                  style={[
                    styles.monthCard,
                    isCurrentMonth && styles.currentMonthCard,
                  ]}
                >
                  <Text
                    style={[
                      styles.monthName,
                      isCurrentMonth && styles.currentMonthText,
                    ]}
                  >
                    {month}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Busiest Months Section */}
          {busiestMonths.length > 0 && (
            <View style={styles.busiestContainer}>
              <Text style={styles.busiestTitle}>📊 Busiest Months</Text>
              {busiestMonths.map((item, index) => (
                <TouchableOpacity
                  key={item.month}
                  style={[
                    styles.busiestCard,
                    index === 0 && styles.busiestFirst,
                    index === 1 && styles.busiestSecond,
                    index === 2 && styles.busiestThird,
                  ]}
                  onPress={() => onSelectMonth(item.monthIndex)}
                >
                  <View style={styles.busiestContent}>
                    <Text style={styles.busiestRank}>#{index + 1}</Text>
                    <Text style={styles.busiestMonth}>{item.month}</Text>
                  </View>
                  <View style={styles.busiestCountBadge}>
                    <Text style={styles.busiestCount}>
                      {item.count} {item.count === 1 ? "event" : "events"}
                    </Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </ScrollView>

        {/* Auto Add Events Button - Fixed at bottom */}
        <TouchableOpacity
          style={styles.autoAddButton}
          onPress={() => setShowAutoExtractor(true)}
        >
          <Text style={styles.autoAddButtonIcon}>🤖</Text>
          <Text style={styles.autoAddButtonText}>Auto Add Events</Text>
          <Text style={styles.autoAddButtonSubtext}>
            Upload photo or file to extract dates
          </Text>
        </TouchableOpacity>

        {/* Auto Event Extractor Modal */}
        <AutoEventExtractorModal
          visible={showAutoExtractor}
          onClose={() => setShowAutoExtractor(false)}
          onSaveEvents={onAddEvents}
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
  header: {
    alignItems: "center",
    marginVertical: 10,
  },
  yearTitle: {
    fontSize: 22,
    fontWeight: "bold",
  },
  swipeHint: {
    color: "#888",
    marginTop: 4,
    fontSize: 12,
  },
  scrollView: {
    flex: 1,
  },
  monthGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },
  monthCard: {
    width: "31%",
    margin: "1%",
    borderRadius: 10,
    backgroundColor: "#f0f0f0",
    padding: 20,
    alignItems: "center",
    position: "relative",
    minHeight: 70,
    justifyContent: "center",
  },
  currentMonthCard: {
    backgroundColor: "#E3F2FD",
    borderWidth: 2,
    borderColor: "#2196F3",
  },
  monthName: {
    fontWeight: "600",
    fontSize: 14,
    color: "#333",
  },
  currentMonthText: {
    color: "#2196F3",
    fontWeight: "700",
  },
  eventBadge: {
    position: "absolute",
    top: 5,
    right: 5,
    backgroundColor: "#FF3B30",
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  eventBadgeText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "bold",
  },
  busiestContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: "#f8f8f8",
    borderRadius: 10,
    marginBottom: 20,
  },
  busiestTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 15,
    color: "#333",
  },
  busiestCard: {
    backgroundColor: "#fff",
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderLeftWidth: 4,
  },
  busiestFirst: {
    borderLeftColor: "#FFD700",
    backgroundColor: "#FFFBF0",
  },
  busiestSecond: {
    borderLeftColor: "#C0C0C0",
    backgroundColor: "#F8F8F8",
  },
  busiestThird: {
    borderLeftColor: "#CD7F32",
    backgroundColor: "#FFF5F0",
  },
  busiestContent: {
    flexDirection: "row",
    alignItems: "center",
  },
  busiestRank: {
    fontSize: 18,
    fontWeight: "700",
    marginRight: 10,
    color: "#666",
  },
  busiestMonth: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  busiestCountBadge: {
    backgroundColor: "#007AFF",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  busiestCount: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
  autoAddButton: {
    backgroundColor: "#F0F0FF",
    borderWidth: 2,
    borderColor: "#7C3AED",
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
    margin: 10,
  },
  autoAddButtonIcon: {
    fontSize: 40,
    marginBottom: 10,
  },
  autoAddButtonText: {
    fontSize: 18,
    fontWeight: "700",
    color: "#7C3AED",
    marginBottom: 5,
  },
  autoAddButtonSubtext: {
    fontSize: 13,
    color: "#666",
    textAlign: "center",
  },
});

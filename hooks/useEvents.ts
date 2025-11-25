import { useState, useEffect } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export interface CalendarEvent {
  id: string;
  date: string; // Format: YYYY-MM-DD
  title: string;
  description?: string;
}

const EVENTS_STORAGE_KEY= "@calendar_events";

export const useEvents= () => {
  const [events, setEvents]= useState<CalendarEvent[]>([]);
  const [loading, setLoading]= useState(true);

  // Load events from storage
  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents= async () => {
    try {
      const storedEvents= await AsyncStorage.getItem(EVENTS_STORAGE_KEY);
      if (storedEvents) {
        setEvents(JSON.parse(storedEvents));
      }
    } catch (error) {
      console.error("Error loading events:", error);
    } finally {
      setLoading(false);
    }
  };

  // Helper to persist data
  const persistEvents= async (newEvents: CalendarEvent[]) => {
    try {
      await AsyncStorage.setItem(EVENTS_STORAGE_KEY, JSON.stringify(newEvents));
    } catch (error) {
      console.error("Error saving events:", error);
    }
  };

  // Add a single event (Refactored to be safe)
  const addEvent= async (event: Omit<CalendarEvent, "id">) => {
    const newEvent: CalendarEvent= {
      ...event,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9), // Protected ID (Safe)
    };

    setEvents((prevEvents) => {
      const updatedEvents= [...prevEvents, newEvent];
      persistEvents(updatedEvents); // Save the calculated state
      return updatedEvents;
    });
  };

  // ✅ NEW: Add multiple events at once (Fixes your issue)
  const addMultipleEvents= async (newEventsList: Omit<CalendarEvent, "id">[]) => {
    // 1. Process all new events first
    const formattedEvents: CalendarEvent[]= newEventsList.map((event, index) => ({
      ...event,
      // Create unique ID using timestamp + random + index to ensure uniqueness in loops
      id: `${Date.now()}-${index}-${Math.random().toString(36).substr(2, 5)}`,
    }));

    // 2. Update state ONCE using the functional update pattern
    setEvents((prevEvents) => {
      const updatedEvents= [...prevEvents, ...formattedEvents];
      
      // 3. Save to storage
      persistEvents(updatedEvents);
      
      return updatedEvents;
    });
  };

  // Delete an event
  const deleteEvent= async (eventId: string) => {
    setEvents((prevEvents) => {
      const updatedEvents= prevEvents.filter((e) => e.id !== eventId);
      persistEvents(updatedEvents);
      return updatedEvents;
    });
  };

  // Get events for a specific date
  const getEventsForDate= (date: string) => {
    return events.filter((e) => e.date === date);
  };

  // Get events for a specific month/year
  const getEventsForMonth= (year: number, month: number) => {
    const datePrefix= `${year}-${String(month + 1).padStart(2, "0")}`;
    return events.filter((e) => e.date.startsWith(datePrefix));
  };

  return {
    events,
    loading,
    addEvent,
    addMultipleEvents, // Export the new function
    deleteEvent,
    getEventsForDate,
    getEventsForMonth,
  };
};
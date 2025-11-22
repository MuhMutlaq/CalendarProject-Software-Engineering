import { useState, useEffect } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export interface CalendarEvent {
  id: string;
  date: string; // Format: YYYY-MM-DD
  title: string;
  description?: string;
}

const EVENTS_STORAGE_KEY = "@calendar_events";

export const useEvents = () => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  // Load events from storage
  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      const storedEvents = await AsyncStorage.getItem(EVENTS_STORAGE_KEY);
      if (storedEvents) {
        setEvents(JSON.parse(storedEvents));
      }
    } catch (error) {
      console.error("Error loading events:", error);
    } finally {
      setLoading(false);
    }
  };

  // Save events to storage
  const saveEvents = async (newEvents: CalendarEvent[]) => {
    try {
      await AsyncStorage.setItem(EVENTS_STORAGE_KEY, JSON.stringify(newEvents));
      setEvents(newEvents);
    } catch (error) {
      console.error("Error saving events:", error);
    }
  };

  // Add a new event
  const addEvent = async (event: Omit<CalendarEvent, "id">) => {
    const newEvent: CalendarEvent = {
      ...event,
      id: Date.now().toString(), // Simple ID generation
    };
    const updatedEvents = [...events, newEvent];
    await saveEvents(updatedEvents);
  };

  // Delete an event
  const deleteEvent = async (eventId: string) => {
    const updatedEvents = events.filter((e) => e.id !== eventId);
    await saveEvents(updatedEvents);
  };

  // Get events for a specific date
  const getEventsForDate = (date: string) => {
    return events.filter((e) => e.date === date);
  };

  // Get events for a specific month/year
  const getEventsForMonth = (year: number, month: number) => {
    const datePrefix = `${year}-${String(month + 1).padStart(2, "0")}`;
    return events.filter((e) => e.date.startsWith(datePrefix));
  };

  return {
    events,
    loading,
    addEvent,
    deleteEvent,
    getEventsForDate,
    getEventsForMonth,
  };
};

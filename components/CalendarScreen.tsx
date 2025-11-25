import React, { useState } from "react";
import { View } from "react-native";
import CalendarYearView from "./CalendarYearView";
import CalendarMonthView from "./CalendarMonthView";
import { useEvents } from "../hooks/useEvents";

export default function CalendarScreen() {
  const today= new Date();
  const [selectedMonth, setSelectedMonth]= useState<number | null>(
    today.getMonth()
  );
  const [selectedYear, setSelectedYear]= useState(today.getFullYear());
  const { events, addEvent, addMultipleEvents, deleteEvent, getEventsForDate }= useEvents();

  const handleMonthYearChange= (newMonth: number, newYear: number) => {
    setSelectedMonth(newMonth);
    setSelectedYear(newYear);
  };

  const handleAddMultipleEvents= async (
    newEvents: Omit<import("../hooks/useEvents").CalendarEvent, "id">[]
  ) => {
    // Call the batch function once. It's much faster and guarantees all events are saved.
    await addMultipleEvents(newEvents);
  };

  return (
    <View style={{ flex: 1, backgroundColor: "#fff" }}>
      {selectedMonth === null ? (
        <CalendarYearView
          year={selectedYear}
          onSelectMonth={(month: number) => setSelectedMonth(month)}
          onChangeYear={(newYear: number) => setSelectedYear(newYear)}
          events={events}
          onAddEvents={handleAddMultipleEvents}
        />
      ): (
        <CalendarMonthView
          month={selectedMonth}
          year={selectedYear}
          onBack={() => setSelectedMonth(null)}
          onMonthYearChange={handleMonthYearChange}
          events={events}
          onAddEvent={addEvent}
          onDeleteEvent={deleteEvent}
          getEventsForDate={getEventsForDate}
        />
      )}
    </View>
  );
}

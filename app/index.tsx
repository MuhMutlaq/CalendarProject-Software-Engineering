import { SafeAreaView } from "react-native-safe-area-context";
import CalendarScreen from "../components/CalendarScreen";
import React from "react";

export default function Index() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#fff" }}>
      <CalendarScreen />
    </SafeAreaView>
  );
}

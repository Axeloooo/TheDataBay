import { Link, Stack } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: "Not Found" }} />
      <View style={styles.container}>
        <Text style={styles.icon}>🔍</Text>
        <Text style={styles.title}>Page Not Found</Text>
        <Text style={styles.message}>
          The screen you are looking for does not exist.
        </Text>
        <Link href="/" style={styles.link}>
          <Text style={styles.linkText}>Go to Marketplace</Text>
        </Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    backgroundColor: "#F8F9FA",
    gap: 12,
  },
  icon: {
    fontSize: 56,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#11181C",
  },
  message: {
    fontSize: 15,
    color: "#687076",
    textAlign: "center",
  },
  link: {
    marginTop: 12,
  },
  linkText: {
    fontSize: 16,
    color: "#0a7ea4",
    fontWeight: "600",
  },
});

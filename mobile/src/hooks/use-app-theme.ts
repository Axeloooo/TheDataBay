import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

export function useAppTheme() {
  const colorScheme = useColorScheme();
  return Colors[colorScheme ?? "light"];
}

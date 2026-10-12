import { Platform } from "react-native";

const tintColorLight = "#1a7af8";
const tintColorDark = "#7fc4ff";

export const Colors = {
  light: {
    text: "#0f1728",
    background: "#f4f7fb",
    tint: tintColorLight,
    icon: "#5f6c85",
    tabIconDefault: "#70809d",
    tabIconSelected: tintColorLight,
    card: "#ffffff",
    cardMuted: "#eef3fb",
    border: "#d9e2f1",
    surface: "#dfe8f7",
    subtleText: "#6b7891",
    success: "#19a16d",
    danger: "#d55353",
    warning: "#c77f16",
    heroStart: "#0f1728",
    heroEnd: "#1640a5",
  },
  dark: {
    text: "#f3f7fd",
    background: "#07111f",
    tint: tintColorDark,
    icon: "#94a8c7",
    tabIconDefault: "#7187a6",
    tabIconSelected: tintColorDark,
    card: "#0d1a2d",
    cardMuted: "#12243b",
    border: "#203451",
    surface: "#0f1f35",
    subtleText: "#90a2bf",
    success: "#35c28a",
    danger: "#ff7b7b",
    warning: "#f1b24d",
    heroStart: "#07111f",
    heroEnd: "#15346f",
  },
};

export const AppTheme = {
  spacing: {
    xxs: 4,
    xs: 8,
    sm: 12,
    md: 16,
    lg: 20,
    xl: 24,
    xxl: 32,
  },
  radius: {
    sm: 12,
    md: 16,
    lg: 20,
    xl: 28,
    pill: 999,
  },
  shadow: {
    card: {
      shadowColor: "#10203a",
      shadowOffset: { width: 0, height: 14 },
      shadowOpacity: 0.08,
      shadowRadius: 28,
      elevation: 8,
    },
    soft: {
      shadowColor: "#10203a",
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.05,
      shadowRadius: 18,
      elevation: 4,
    },
  },
} as const;

export const Fonts = Platform.select({
  ios: {
    sans: "system-ui",
    serif: "ui-serif",
    rounded: "ui-rounded",
    mono: "ui-monospace",
  },
  default: {
    sans: "normal",
    serif: "serif",
    rounded: "normal",
    mono: "monospace",
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded:
      "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});

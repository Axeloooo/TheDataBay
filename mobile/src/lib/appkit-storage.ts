import AsyncStorage from "@react-native-async-storage/async-storage";
import type { Storage } from "@reown/appkit-react-native";

export const appKitStorage: Storage = {
  async getKeys() {
    return [...(await AsyncStorage.getAllKeys())];
  },

  async getEntries<T = unknown>() {
    const keys = await AsyncStorage.getAllKeys();
    if (keys.length === 0) {
      return [];
    }

    const entries = await AsyncStorage.multiGet(keys);
    return entries.flatMap(([key, value]) => {
      if (value === null) {
        return [];
      }

      try {
        return [[key, JSON.parse(value) as T]];
      } catch {
        return [[key, value as T]];
      }
    });
  },

  async getItem<T = unknown>(key: string) {
    const value = await AsyncStorage.getItem(key);

    if (value === null) {
      return undefined;
    }

    try {
      return JSON.parse(value) as T;
    } catch {
      return value as T;
    }
  },

  async setItem<T = unknown>(key: string, value: T) {
    const serialized =
      typeof value === "string" ? value : JSON.stringify(value);
    await AsyncStorage.setItem(key, serialized);
  },

  async removeItem(key: string) {
    await AsyncStorage.removeItem(key);
  },
};

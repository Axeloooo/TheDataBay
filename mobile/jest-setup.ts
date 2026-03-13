import '@react-native-async-storage/async-storage/jest/async-storage-mock';

// Mock expo-secure-store
jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    getItemAsync: jest.fn(async (key: string) => store[key] ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => {
      store[key] = value;
    }),
    deleteItemAsync: jest.fn(async (key: string) => {
      delete store[key];
    }),
  };
});

// Mock expo-file-system
jest.mock('expo-file-system', () => ({
  documentDirectory: '/mock/documents/',
  writeAsStringAsync: jest.fn(async () => undefined),
  readAsStringAsync: jest.fn(async () => ''),
  deleteAsync: jest.fn(async () => undefined),
  EncodingType: { Base64: 'base64', UTF8: 'utf8' },
}));

// Mock expo-sharing
jest.mock('expo-sharing', () => ({
  isAvailableAsync: jest.fn(async () => false),
  shareAsync: jest.fn(async () => undefined),
}));

// Mock expo-crypto
jest.mock('expo-crypto', () => ({
  digestStringAsync: jest.fn(async () => 'mock-hash'),
  CryptoDigestAlgorithm: { SHA256: 'SHA-256' },
}));

// Mock expo-constants
jest.mock('expo-constants', () => ({
  default: {
    expoConfig: {
      extra: {
        apiUrl: 'http://localhost:8080',
        pinataGatewayUrl: 'https://gateway.pinata.cloud',
      },
    },
  },
}));

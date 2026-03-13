import { useEffect } from "react";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";

export function HelloWave() {
  const rotation = useSharedValue(0);

  useEffect(() => {
    rotation.value = withRepeat(
      withSequence(
        withTiming(24, { duration: 120, easing: Easing.out(Easing.quad) }),
        withTiming(-10, { duration: 120, easing: Easing.inOut(Easing.quad) }),
        withTiming(24, { duration: 120, easing: Easing.inOut(Easing.quad) }),
        withTiming(0, { duration: 120, easing: Easing.in(Easing.quad) }),
      ),
      4,
      false,
    );
  }, [rotation]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  return (
    <Animated.Text
      style={[
        {
          fontSize: 28,
          lineHeight: 32,
          marginTop: -6,
        },
        animatedStyle,
      ]}
    >
      👋
    </Animated.Text>
  );
}

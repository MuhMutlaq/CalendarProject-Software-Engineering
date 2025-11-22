import { ExpoConfig } from "expo/config";

// You can remove this if you don't use Expo Router
export default ({ config }: { config: ExpoConfig }) => ({
  ...config,
});
